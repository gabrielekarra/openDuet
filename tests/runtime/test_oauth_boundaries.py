"""Confidential clients, rotating refresh tokens and account replacement races."""

import asyncio
import json
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from mcp.types import Tool as RemoteTool

from openduet import connectors, registry
from openduet.config import Config
from openduet.runtime import Runtime
from openduet.store import Store


@pytest.fixture
async def runtime(tmp_path, monkeypatch):
    result = Runtime(Config(data_dir=tmp_path), Store(tmp_path))

    async def refresh():
        pass

    monkeypatch.setattr(result.tools, "refresh", refresh)
    await result.registry.add("account", {"url": "https://mcp.example/mcp"})
    yield result
    await result.close()


def discovery(method, url, *, token_auth_method="client_secret_post", **kwargs):
    if "oauth-protected-resource" in url:
        return httpx.Response(200, json={"authorization_servers": ["https://auth.example/tenant"]})
    assert url == "https://auth.example/.well-known/oauth-authorization-server/tenant"
    return httpx.Response(
        200,
        json={
            "issuer": "https://auth.example/tenant",
            "authorization_endpoint": "https://auth.example/authorize?audience=work",
            "token_endpoint": "https://auth.example/token",
            "revocation_endpoint": "https://auth.example/revoke",
            "token_endpoint_auth_methods_supported": [token_auth_method],
            "code_challenge_methods_supported": ["S256"],
        },
    )


@pytest.mark.parametrize("method", ["client_secret_post", "client_secret_basic"])
async def test_confidential_pkce_refresh_is_serial_and_tokens_cannot_replace_endpoints(
    runtime, monkeypatch, method
):
    requests = []
    refreshing = 0

    async def request(verb, url, **kwargs):
        nonlocal refreshing
        if verb == "GET":
            return discovery(verb, url, token_auth_method=method)
        requests.append((url, kwargs))
        form = kwargs["data"]
        if method == "client_secret_post":
            assert form["client_secret"] == "private-client-secret"
            assert kwargs.get("auth") is None
        else:
            assert isinstance(kwargs["auth"], httpx.BasicAuth)
            assert "client_secret" not in form
        if url.endswith("revoke"):
            return httpx.Response(200)
        if form["grant_type"] == "refresh_token":
            refreshing += 1
            assert refreshing == 1
            assert form["refresh_token"] == "rotate-once"
            await asyncio.sleep(0.02)
            return httpx.Response(
                200, json={"access_token": "renewed-private", "refresh_token": "rotated", "expires_in": 3600}
            )
        assert len(form["code_verifier"]) >= 43
        return httpx.Response(
            200,
            json={
                "access_token": "first-private",
                "refresh_token": "rotate-once",
                "expires_in": 1,
                "token_endpoint": "https://wrong.example/steal",
                "client_secret": "untrusted",
            },
        )

    monkeypatch.setattr(registry, "oauth_request", request)
    result = await runtime.registry.begin_oauth(
        "account",
        "https://workspace.example/callback",
        "client-id",
        "tools",
        "private-client-secret",
        {"access_type": "offline", "prompt": "consent"},
    )
    query = parse_qs(urlsplit(result["url"]).query)
    assert query["audience"] == ["work"] and query["access_type"] == ["offline"]
    assert "private-client-secret" not in result["url"]
    pending = runtime.store.rows("SELECT data FROM oauth_pending")[0]["data"]
    assert pending.startswith("oauth:")
    assert "private-client-secret" not in json.dumps(runtime.store.rows("SELECT * FROM connector_registry"))
    await runtime.registry.finish_oauth(query["state"][0], "code")
    cfg = runtime.config.connectors["account"]
    values = await asyncio.gather(*(runtime.registry.auth_headers(cfg) for _ in range(4)))
    assert values == [{"Authorization": "Bearer renewed-private"}] * 4
    assert refreshing == 1
    assert all(url.startswith("https://auth.example/") for url, _ in requests)
    assert "private-client-secret" not in runtime.redact("Echo private-client-secret")
    await runtime.registry.disconnect("account")
    assert requests[-1][0].endswith("revoke")


async def test_stale_callback_cannot_store_token_in_replacement_account(runtime, monkeypatch):
    started, release = asyncio.Event(), asyncio.Event()

    async def request(verb, url, **kwargs):
        if verb == "GET":
            return discovery(verb, url)
        started.set()
        await release.wait()
        return httpx.Response(200, json={"access_token": "old-account-token"})

    monkeypatch.setattr(registry, "oauth_request", request)
    result = await runtime.registry.begin_oauth("account", "https://workspace.example/callback", "client")
    state = parse_qs(urlsplit(result["url"]).query)["state"][0]
    pending = asyncio.create_task(runtime.registry.finish_oauth(state, "code"))
    await started.wait()
    await runtime.registry.add(
        "account", {"url": "https://new.example/mcp", "bearer_token": "new-account-token"}
    )
    release.set()
    with pytest.raises(ValueError, match="changed"):
        await pending
    assert (await runtime.registry.auth_headers(runtime.config.connectors["account"])) == {
        "Authorization": "Bearer new-account-token"
    }
    assert not runtime.store.rows("SELECT * FROM oauth_pending")
    assert not runtime.store.rows("SELECT name FROM secrets WHERE name LIKE 'oauth:%'")


async def test_replacement_drops_old_secret_and_pending_state(runtime, monkeypatch):
    async def request(verb, url, **kwargs):
        return discovery(verb, url)

    monkeypatch.setattr(registry, "oauth_request", request)
    await runtime.registry.add("account", {"url": "https://mcp.example/mcp", "bearer_token": "old-private"})
    await runtime.registry.begin_oauth("account", "https://workspace.example/callback", "client")
    await runtime.registry.add("account", {"url": "https://new.example/mcp"})
    assert not runtime.store.rows("SELECT * FROM secrets")
    assert not runtime.store.rows("SELECT * FROM oauth_pending")
    assert await runtime.registry.auth_headers(runtime.config.connectors["account"]) == {}


async def test_slow_revocation_cannot_remove_a_new_connection(runtime, monkeypatch):
    started, release = asyncio.Event(), asyncio.Event()
    runtime.vault.put(
        "connector:account",
        json.dumps({"access_token": "old", "revocation_endpoint": "https://auth.example/revoke"}),
    )

    async def request(*args, **kwargs):
        started.set()
        await release.wait()
        return httpx.Response(200)

    monkeypatch.setattr(registry, "oauth_request", request)
    pending = asyncio.create_task(runtime.registry.disconnect("account"))
    await started.wait()
    await runtime.registry.add("account", {"url": "https://new.example/mcp", "bearer_token": "new"})
    release.set()
    await pending
    assert runtime.config.connectors["account"].url == "https://new.example/mcp"
    assert await runtime.registry.auth_headers(runtime.config.connectors["account"]) == {
        "Authorization": "Bearer new"
    }


async def test_slow_discovery_cannot_restore_old_account_tools(tmp_path, monkeypatch):
    runtime = Runtime(Config(data_dir=tmp_path), Store(tmp_path))
    started, release = asyncio.Event(), asyncio.Event()

    async def discover(config, *args):
        if "old.example" in config.url:
            started.set()
            await release.wait()
            return [RemoteTool(name="old_read", inputSchema={"type": "object"})]
        return [RemoteTool(name="new_read", inputSchema={"type": "object"})]

    monkeypatch.setattr(connectors, "discover", discover)
    pending = asyncio.create_task(runtime.registry.add("account", {"url": "https://old.example/mcp"}))
    await started.wait()
    await runtime.registry.add("account", {"url": "https://new.example/mcp"})
    release.set()
    await pending
    assert [t.remote_name for t in runtime.tools.catalog.values() if t.connector == "account"] == ["new_read"]
    await runtime.close()
