"""Hot-reloaded MCP registry and browser-driven OAuth 2.1/PKCE."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import secrets
import ssl
import time
from dataclasses import asdict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from .config import ConnectorConfig
from .providers import trust_environment
from .store import uid


def endpoint(value):
    parsed = urlsplit(value)
    if (
        parsed.username
        or parsed.password
        or parsed.fragment
        or not parsed.hostname
        or (
            parsed.scheme != "https"
            and not (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"})
        )
    ):
        raise ValueError("Use HTTPS without credentials (loopback HTTP is allowed for local MCP servers)")
    if any(
        key.lower()
        in {
            "token",
            "access_token",
            "api_key",
            "apikey",
            "key",
            "authorization",
            "password",
            "secret",
            "client_secret",
            "code_verifier",
        }
        for key, _ in parse_qsl(parsed.query)
    ):
        raise ValueError("Put credentials in the private bearer-token field, not in the server URL")
    return value


async def oauth_request(method, url, **kwargs):
    url = endpoint(url)
    async with httpx.AsyncClient(
        timeout=15,
        follow_redirects=False,
        trust_env=trust_environment(url),
        verify=ssl.create_default_context(),
    ) as client:
        response = await client.request(method, url, **kwargs)
    if len(response.content) > 1_000_000:
        raise ValueError("OAuth response exceeded its size limit")
    return response


async def token_request(settings, fields, *, revoke=False):
    fields = {"client_id": settings.get("client_id", ""), **fields}
    auth = None
    if secret := settings.get("client_secret"):
        if settings.get("token_auth_method") == "client_secret_basic":
            auth = httpx.BasicAuth(settings["client_id"], secret)
        else:
            fields["client_secret"] = secret
    return await oauth_request(
        "POST", settings["revocation_endpoint" if revoke else "token_endpoint"], data=fields, auth=auth
    )


def token_fields(response):
    if response.is_error:
        raise ValueError("OAuth authorization failed; reconnect the account")
    data = response.json()
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("access_token"), str)
        or not data["access_token"]
        or any(c in data["access_token"] for c in "\r\n")
    ):
        raise ValueError("OAuth server did not return a valid access token")
    if str(data.get("token_type", "Bearer")).lower() != "bearer":
        raise ValueError("This OAuth token type is not supported")
    if any(
        key in data and (not isinstance(data[key], str) or any(c in data[key] for c in "\r\n"))
        for key in ("refresh_token", "scope")
    ):
        raise ValueError("OAuth server returned invalid token fields")
    # Token responses cannot replace the trusted issuer/endpoint/client settings.
    result = {
        key: data[key] for key in ("access_token", "refresh_token", "scope", "token_type") if key in data
    }
    result["expires_at"] = time.time() + max(1, min(int(data.get("expires_in", 3600)), 365 * 86400))
    return result


class Registry:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self._token_locks = {}
        with self.store.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS connector_registry(id TEXT PRIMARY KEY, config TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS oauth_pending(state TEXT PRIMARY KEY, connector TEXT, expires REAL, data TEXT);
            """)
        for row in self.store.rows("SELECT * FROM connector_registry"):
            runtime.config.connectors.setdefault(row["id"], ConnectorConfig(**json.loads(row["config"])))
        isolated = [name for name, config in runtime.config.connectors.items() if config.exclusive]
        if isolated and len(runtime.config.connectors) != 1:
            raise ValueError("Use a fresh, dedicated OpenDuet profile for this isolated provider")
        for name, config in runtime.config.connectors.items():
            if config.exclusive and not self.store.preference("exclusive_provider", ""):
                self.require_fresh_profile()
                self.store.set_preference("exclusive_provider", name)
                self.store.set_preference("exclusive_origin", config.url)

    def require_fresh_profile(self):
        if (
            self.store.rows("SELECT id FROM messages LIMIT 1")
            or self.store.rows("SELECT id FROM memories LIMIT 1")
            or self.store.rows("SELECT id FROM tasks LIMIT 1")
            or self.store.preference("mail_accounts", {})
        ):
            raise ValueError("Use a fresh, dedicated OpenDuet profile for this isolated provider")

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
                "require_approval",
                "exclusive",
            }
        }
        config = ConnectorConfig(**allowed)
        reserved = self.store.preference("exclusive_provider", "")
        if reserved and reserved != name:
            raise ValueError(
                "This profile is reserved for an isolated provider; create a separate OpenDuet installation directory"
            )
        if reserved and (
            not config.exclusive or config.url != self.store.preference("exclusive_origin", config.url)
        ):
            raise ValueError(
                "An isolated profile cannot be rebound to another provider; create a fresh profile"
            )
        if config.exclusive and not reserved:
            if self.runtime.config.connectors:
                raise ValueError("Use a fresh, dedicated OpenDuet profile for this isolated provider")
            self.require_fresh_profile()
        config.credential_ref = "connector:" + name
        bearer = values.get("bearer_token", "")
        if bearer:
            if not isinstance(bearer, str) or len(bearer) > 8192 or any(c in bearer for c in "\r\n"):
                raise ValueError("Invalid bearer token")
            self.runtime.vault.put(config.credential_ref, json.dumps({"access_token": bearer}))
        else:
            self.runtime.vault.remove(config.credential_ref)
        self.clear_pending(name)
        self.store.execute(
            "INSERT OR REPLACE INTO connector_registry VALUES(?,?)", (name, json.dumps(asdict(config)))
        )
        self.runtime.config.connectors[name] = config
        if config.exclusive:
            self.store.set_preference("exclusive_provider", name)
            self.store.set_preference("exclusive_origin", config.url)
        self.new_revision(name)
        disabled = self.store.preference("disabled_connectors", [])
        self.store.set_preference("disabled_connectors", [item for item in disabled if item != name])
        await self.runtime.tools.refresh()
        return {"id": name}

    def new_revision(self, name):
        values = self.store.preference("connector_revisions", {})
        values[name] = uid()
        self.store.set_preference("connector_revisions", values)

    def clear_pending(self, name=None):
        where, args = ("connector=?", (name,)) if name else ("expires<=?", (time.time(),))
        rows = self.store.rows("SELECT data FROM oauth_pending WHERE " + where, args)
        self.store.execute("DELETE FROM oauth_pending WHERE " + where, args)
        for row in rows:
            self.runtime.vault.remove(row["data"])

    def require_context(self, name, context):
        if (
            name not in self.runtime.config.connectors
            or not self.runtime.tools.enabled(name)
            or self.runtime.tools.connection_context(name) != context
        ):
            raise ValueError("This connection changed or was disconnected; start a fresh authorization")

    async def disconnect(self, name):
        config = self.runtime.config.connectors.get(name)
        disabled = set(self.store.preference("disabled_connectors", []))
        disabled.add(name)
        self.store.set_preference("disabled_connectors", sorted(disabled))
        self.new_revision(name)
        self.clear_pending(name)
        self.runtime.attention.forget_connector(name)
        token = {}
        if config and config.credential_ref:
            try:
                token = json.loads(self.runtime.vault.get(config.credential_ref))
            except ValueError:
                pass
            self.runtime.vault.remove(config.credential_ref)
        # Remove the old connection before awaiting I/O: a subsequent add of
        # the same id must survive the old provider's revocation response.
        self.store.execute("DELETE FROM connector_registry WHERE id=?", (name,))
        self.runtime.config.connectors.pop(name, None)
        if token.get("revocation_endpoint"):
            try:
                await token_request(
                    token, {"token": token.get("refresh_token", token["access_token"])}, revoke=True
                )
            except (ValueError, httpx.HTTPError, KeyError):
                pass
        await self.runtime.tools.refresh()

    async def auth_headers(self, config):
        if not config.credential_ref:
            return {}
        lock = self._token_locks.setdefault(config.credential_ref, asyncio.Lock())
        async with lock:
            name = next(
                (name for name, value in self.runtime.config.connectors.items() if value is config), None
            )
            if name is None:
                raise ValueError("This connector was replaced or disconnected")
            context = self.runtime.tools.connection_context(name)
            self.require_context(name, context)
            if not self.store.rows("SELECT name FROM secrets WHERE name=?", (config.credential_ref,)):
                return {}
            # Re-read after the lock: rotating refresh tokens are single-use.
            token = json.loads(self.runtime.vault.get(config.credential_ref, purpose="connector"))
            if token.get("expires_at", 1e20) <= time.time() + 30 and token.get("refresh_token"):
                response = await token_request(
                    token,
                    {
                        "grant_type": "refresh_token",
                        "refresh_token": token["refresh_token"],
                        **({"resource": token["resource"]} if token.get("resource") else {}),
                    },
                )
                renewed = token_fields(response)
                self.require_context(name, context)
                token.update(renewed)
                self.runtime.vault.put(config.credential_ref, json.dumps(token))
            return {"Authorization": "Bearer " + token["access_token"]}

    async def begin_oauth(
        self, name, redirect_uri, client_id="", scopes="", client_secret="", authorization_params=None
    ):
        for value in (client_id, scopes, client_secret):
            if not isinstance(value, str) or len(value) > 8192 or any(c in value for c in "\r\n"):
                raise ValueError("Invalid private OAuth client settings")
        extra = authorization_params or {}
        if (
            not isinstance(extra, dict)
            or set(extra) - {"access_type", "prompt"}
            or any(not isinstance(value, str) or len(value) > 100 for value in extra.values())
        ):
            raise ValueError("Only access_type and prompt authorization parameters are supported")
        config = self.runtime.config.connectors[name]
        context = self.runtime.tools.connection_context(name)
        self.require_context(name, context)
        self.clear_pending()
        self.clear_pending(name)
        attempts = self.store.preference("oauth_attempts", {})
        attempts[name] = attempt = uid()
        self.store.set_preference("oauth_attempts", attempts)
        parsed = urlsplit(config.url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        resource_response = await oauth_request(
            "GET", root + "/.well-known/oauth-protected-resource" + parsed.path
        )
        if resource_response.is_error:
            resource_response = await oauth_request("GET", root + "/.well-known/oauth-protected-resource")
        resource = resource_response.json() if resource_response.is_success else {}
        issuer = endpoint((resource.get("authorization_servers") or [root])[0])
        parsed_issuer = urlsplit(issuer)
        discovery = (
            f"{parsed_issuer.scheme}://{parsed_issuer.netloc}/.well-known/oauth-authorization-server"
            + parsed_issuer.path.rstrip("/")
        )
        metadata_response = await oauth_request("GET", discovery)
        if metadata_response.is_error:
            metadata_response = await oauth_request(
                "GET", issuer.rstrip("/") + "/.well-known/openid-configuration"
            )
        if metadata_response.is_error:
            raise ValueError("Could not discover this server's OAuth configuration")
        metadata = metadata_response.json()
        if metadata.get("issuer", issuer).rstrip("/") != issuer.rstrip("/"):
            raise ValueError("OAuth discovery returned a different issuer")
        if "S256" not in metadata.get("code_challenge_methods_supported", ["S256"]):
            raise ValueError("OAuth server must support PKCE S256")
        if not client_id:
            if not metadata.get("registration_endpoint"):
                raise ValueError(
                    "This provider requires its own OAuth client ID and, when issued, client secret"
                )
            response = await oauth_request(
                "POST",
                metadata["registration_endpoint"],
                json={
                    "client_name": "OpenDuet",
                    "redirect_uris": [redirect_uri],
                    "grant_types": ["authorization_code", "refresh_token"],
                    "response_types": ["code"],
                    "token_endpoint_auth_method": "none",
                },
            )
            if response.is_error:
                raise ValueError("OAuth client registration failed; enter a provider-issued client ID")
            registration = response.json()
            client_id = registration["client_id"]
            client_secret = registration.get("client_secret", "")
        methods = metadata.get("token_endpoint_auth_methods_supported", [])
        method = (
            "client_secret_basic"
            if client_secret
            and methods
            and "client_secret_post" not in methods
            and "client_secret_basic" in methods
            else "client_secret_post"
            if client_secret
            else "none"
        )
        if client_secret and methods and method not in methods:
            raise ValueError("The provider's OAuth client authentication method is not supported")
        self.require_context(name, context)
        if self.store.preference("oauth_attempts", {}).get(name) != attempt:
            raise ValueError("A newer OAuth request replaced this one")
        verifier, state = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        details = {
            "verifier": verifier,
            "client_id": client_id,
            "client_secret": client_secret,
            "token_auth_method": method,
            "redirect_uri": redirect_uri,
            "token_endpoint": endpoint(metadata["token_endpoint"]),
            "revocation_endpoint": endpoint(metadata["revocation_endpoint"])
            if metadata.get("revocation_endpoint")
            else "",
            "resource": config.url,
            "context": context,
            "attempt": attempt,
        }
        reference = "oauth:" + uid()
        self.runtime.vault.put(reference, json.dumps(details))
        self.store.execute(
            "INSERT INTO oauth_pending VALUES(?,?,?,?)",
            (hashlib.sha256(state.encode()).hexdigest(), name, time.time() + 600, reference),
        )
        auth = urlsplit(endpoint(metadata["authorization_endpoint"]))
        query = (
            dict(parse_qsl(auth.query))
            | extra
            | {
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
        return {"url": urlunsplit((auth.scheme, auth.netloc, auth.path, urlencode(query), ""))}

    async def finish_oauth(self, state, code):
        self.clear_pending()
        digest = hashlib.sha256(state.encode()).hexdigest()
        rows = self.store.rows(
            "SELECT * FROM oauth_pending WHERE state=? AND expires>?", (digest, time.time())
        )
        if not rows:
            raise ValueError("OAuth request expired or was already used")
        row = rows[0]
        if not self.store.execute("DELETE FROM oauth_pending WHERE state=?", (digest,)):
            raise ValueError("OAuth request already used")
        data = json.loads(self.runtime.vault.get(row["data"], purpose="oauth"))
        self.runtime.vault.remove(row["data"])
        name = row["connector"]

        def current():
            self.require_context(name, data["context"])
            if self.store.preference("oauth_attempts", {}).get(name) != data["attempt"]:
                raise ValueError("A newer OAuth request replaced this one")

        current()
        response = await token_request(
            data,
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": data["redirect_uri"],
                "code_verifier": data["verifier"],
                "resource": data["resource"],
            },
        )
        token = token_fields(response)
        current()
        token.update(
            {
                key: data[key]
                for key in (
                    "client_id",
                    "client_secret",
                    "token_auth_method",
                    "resource",
                    "token_endpoint",
                    "revocation_endpoint",
                )
            }
        )
        self.runtime.vault.put(self.runtime.config.connectors[name].credential_ref, json.dumps(token))
        self.new_revision(name)
        await self.runtime.tools.refresh()
        return {"connected": name}
