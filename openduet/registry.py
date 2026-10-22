"""Hot-reloaded MCP registry and browser-driven OAuth 2.1/PKCE."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from dataclasses import asdict
from urllib.parse import urlencode, urlsplit

import httpx

from .config import ConnectorConfig
from .store import uid


def endpoint(value):
    parsed = urlsplit(value)
    if (
        parsed.username
        or parsed.password
        or not parsed.hostname
        or (
            parsed.scheme != "https"
            and not (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"})
        )
    ):
        raise ValueError("Use HTTPS without credentials (loopback HTTP is allowed for local MCP servers)")
    return value


class Registry:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS connector_registry(id TEXT PRIMARY KEY, config TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS oauth_pending(state TEXT PRIMARY KEY, connector TEXT, expires REAL, data TEXT);
            """)
        for row in self.store.rows("SELECT * FROM connector_registry"):
            runtime.config.connectors.setdefault(row["id"], ConnectorConfig(**json.loads(row["config"])))

    async def add(self, name, values):
        if (
            not name
            or len(name) > 80
            or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in name)
        ):
            raise ValueError("Use letters, numbers, hyphens or underscores for the connector id")
        if values.get("command"):
            raise ValueError("Local executable connectors can only be configured by the operator in TOML")
        endpoint(values.get("url", ""))
        allowed = {
            key: value
            for key, value in values.items()
            if key
            in {
                "url",
                "safe_tools",
                "excluded_tools",
                "poll_tool",
                "poll_arguments",
                "event_kind",
                "poll_seconds",
                "cursor_argument",
            }
        }
        config = ConnectorConfig(**allowed)
        config.credential_ref = "connector:" + name
        self.store.execute(
            "INSERT OR REPLACE INTO connector_registry VALUES(?,?)", (name, json.dumps(asdict(config)))
        )
        self.runtime.config.connectors[name] = config
        disabled = self.store.preference("disabled_connectors", [])
        self.store.set_preference("disabled_connectors", [item for item in disabled if item != name])
        await self.runtime.tools.refresh()
        return {"id": name}

    async def disconnect(self, name):
        config = self.runtime.config.connectors.get(name)
        disabled = set(self.store.preference("disabled_connectors", []))
        disabled.add(name)
        self.store.set_preference("disabled_connectors", sorted(disabled))
        # Revoke locally before awaiting the remote provider. Already executing effects remain uncertain.
        self.runtime.attention.forget_connector(name)
        if config and config.credential_ref:
            try:
                token = json.loads(self.runtime.vault.get(config.credential_ref))
                if token.get("revocation_endpoint"):
                    async with httpx.AsyncClient(timeout=10) as client:
                        await client.post(
                            endpoint(token["revocation_endpoint"]),
                            data={
                                "token": token.get("refresh_token", token["access_token"]),
                                "client_id": token.get("client_id", ""),
                            },
                        )
            except (ValueError, httpx.HTTPError, KeyError):
                pass
            self.runtime.vault.remove(config.credential_ref)
        self.store.execute("DELETE FROM connector_registry WHERE id=?", (name,))
        self.runtime.config.connectors.pop(name, None)
        await self.runtime.tools.refresh()

    async def auth_headers(self, config):
        if not config.credential_ref:
            return {}
        if not self.store.rows("SELECT name FROM secrets WHERE name=?", (config.credential_ref,)):
            return {}
        token = json.loads(self.runtime.vault.get(config.credential_ref, purpose="connector"))
        if token.get("expires_at", 1e20) <= time.time() + 30 and token.get("refresh_token"):
            async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
                response = await client.post(
                    endpoint(token["token_endpoint"]),
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": token["refresh_token"],
                        "client_id": token["client_id"],
                    },
                )
                if response.is_error:
                    raise ValueError("Reconnect this account: OAuth refresh failed")
                renewed = response.json()
            token.update(renewed)
            token["expires_at"] = time.time() + renewed.get("expires_in", 3600)
            self.runtime.vault.put(config.credential_ref, json.dumps(token))
        return {"Authorization": "Bearer " + token["access_token"]}

    async def begin_oauth(self, name, redirect_uri, client_id="", scopes=""):
        config = self.runtime.config.connectors[name]
        parsed = urlsplit(config.url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            resource_response = await client.get(root + "/.well-known/oauth-protected-resource" + parsed.path)
            if resource_response.is_error:
                resource_response = await client.get(root + "/.well-known/oauth-protected-resource")
            resource = resource_response.json() if resource_response.is_success else {}
            auth = endpoint((resource.get("authorization_servers") or [root])[0])
            metadata_response = await client.get(auth.rstrip("/") + "/.well-known/oauth-authorization-server")
            metadata_response.raise_for_status()
            metadata = metadata_response.json()
            if "S256" not in metadata.get("code_challenge_methods_supported", ["S256"]):
                raise ValueError("OAuth server must support PKCE S256")
            if not client_id:
                registration = endpoint(metadata.get("registration_endpoint", ""))
                result = await client.post(
                    registration,
                    json={
                        "client_name": "OpenDuet",
                        "redirect_uris": [redirect_uri],
                        "grant_types": ["authorization_code", "refresh_token"],
                        "response_types": ["code"],
                        "token_endpoint_auth_method": "none",
                    },
                )
                result.raise_for_status()
                client_id = result.json()["client_id"]
        verifier, state = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        details = {
            "verifier": verifier,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "token_endpoint": endpoint(metadata["token_endpoint"]),
            "revocation_endpoint": metadata.get("revocation_endpoint", ""),
            "resource": config.url,
        }
        # PKCE verifier is a credential too; the pending table contains only a reference.
        reference = "oauth:" + uid()
        self.runtime.vault.put(reference, json.dumps(details))
        self.store.execute(
            "INSERT INTO oauth_pending VALUES(?,?,?,?)",
            (hashlib.sha256(state.encode()).hexdigest(), name, time.time() + 600, reference),
        )
        return {
            "url": endpoint(metadata["authorization_endpoint"])
            + "?"
            + urlencode(
                {
                    "response_type": "code",
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                    "state": state,
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                    "resource": config.url,
                    "scope": scopes,
                }
            )
        }

    async def finish_oauth(self, state, code):
        digest = hashlib.sha256(state.encode()).hexdigest()
        rows = self.store.rows(
            "SELECT * FROM oauth_pending WHERE state=? AND expires>?", (digest, time.time())
        )
        if not rows:
            raise ValueError("OAuth request expired or was already used")
        row = rows[0]
        changed = self.store.execute("DELETE FROM oauth_pending WHERE state=?", (digest,))
        if not changed:
            raise ValueError("OAuth request already used")
        data = json.loads(self.runtime.vault.get(row["data"], purpose="oauth"))
        self.runtime.vault.remove(row["data"])
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.post(
                data["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": data["client_id"],
                    "redirect_uri": data["redirect_uri"],
                    "code_verifier": data["verifier"],
                    "resource": data["resource"],
                },
            )
            if response.is_error:
                raise ValueError("OAuth authorization failed; reconnect the account")
            token = response.json()
        token.update({key: data[key] for key in ("client_id", "token_endpoint", "revocation_endpoint")})
        token["expires_at"] = time.time() + token.get("expires_in", 3600)
        self.runtime.vault.put(
            self.runtime.config.connectors[row["connector"]].credential_ref, json.dumps(token)
        )
        await self.runtime.tools.refresh()
        return {"connected": row["connector"]}
