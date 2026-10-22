"""Boundary tests use disposable transports; no real account, issuer or model is contacted."""

import hashlib
import hmac
import io
import json
import logging
import time
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from PIL import Image

from openduet.attachments import ingest
from openduet.computer import public_url
from openduet.config import Config, ConnectorConfig
from openduet.egress import resolve
from openduet.kev.eval import evaluate
from openduet.prototypes import create_app
from openduet.providers import Reply
from openduet.runtime import Runtime
from openduet.store import Store
from openduet.telegram import RedactBotURL
from openduet.tools import Tool, schema
from openduet.vault import Vault


@pytest.fixture
def runtime(tmp_path):
    return Runtime(Config(data_dir=tmp_path), Store(tmp_path))


async def test_deferred_approval_after_independent_work_is_dispatched_once(runtime):
    effects = []

    async def send(arguments, task):
        effects.append(arguments)
        return {"receipt": "sent-once"}

    class Model:
        def __init__(self, config):
            pass

        async def complete(self, messages, tools):
            return Reply({"role": "assistant", "content": "Independent work ready."}, 1, 1)

    runtime.provider_factory = Model
    runtime.tools.catalog["send_email"] = Tool(
        "send_email", "Send", schema({"body": {"type": "string"}}), send, True
    )
    task = runtime.store.new_task("main", "Prepare a message and a report", "local")
    history = [
        {
            "role": "assistant",
            "tool_calls": [
                {"id": "original", "function": {"name": "send_email", "arguments": '{"body":"reviewed"}'}}
            ],
        }
    ]
    runtime.checkpoint(task, history, 0)
    assert not await runtime.process_calls(runtime.store.task(task), history)
    call = runtime.store.rows("SELECT * FROM calls")[0]
    runtime.approvals.decide(call["id"], "defer")
    assert await runtime.process_calls(runtime.store.task(task), history)
    history.append({"role": "assistant", "content": "Independent work ready."})
    runtime.checkpoint(task, history, 1)
    runtime.store.status(task, "ready")
    runtime.approvals.decide(call["id"], "approve")
    await runtime.run_task(task)
    await runtime.run_task(task)
    assert effects == [{"body": "reviewed"}]
    assert runtime.store.rows("SELECT status FROM calls")[0]["status"] == "succeeded"
    await runtime.close()


async def test_oauth_pkce_dcr_refresh_revoke_and_one_use_state(runtime, monkeypatch):
    runtime.config.connectors["fixture"] = ConnectorConfig(
        url="https://mcp.example/mcp", credential_ref="connector:fixture"
    )

    async def refresh():
        pass

    runtime.tools.refresh = refresh
    requests = []

    def handler(request):
        requests.append(request)
        path = request.url.path
        if "oauth-protected-resource" in path:
            return httpx.Response(200, json={"authorization_servers": ["https://auth.example"]})
        if "oauth-authorization-server" in path:
            return httpx.Response(
                200,
                json={
                    "authorization_endpoint": "https://auth.example/authorize",
                    "token_endpoint": "https://auth.example/token",
                    "registration_endpoint": "https://auth.example/register",
                    "revocation_endpoint": "https://auth.example/revoke",
                    "code_challenge_methods_supported": ["S256"],
                },
            )
        if path == "/register":
            assert json.loads(request.content)["token_endpoint_auth_method"] == "none"
            return httpx.Response(201, json={"client_id": "fixture-client"})
        if path == "/token":
            body = parse_qs(request.content.decode())
            if body["grant_type"] == ["authorization_code"]:
                verifier = body["code_verifier"][0]
                assert len(verifier) >= 43
                return httpx.Response(
                    200,
                    json={
                        "access_token": "private-access-fixture",
                        "refresh_token": "private-refresh-fixture",
                        "expires_in": 1,
                    },
                )
            assert body["refresh_token"] == ["private-refresh-fixture"]
            return httpx.Response(200, json={"access_token": "renewed-access-fixture", "expires_in": 3600})
        return httpx.Response(200, json={})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **options: original(transport=httpx.MockTransport(handler))
    )
    result = await runtime.registry.begin_oauth(
        "fixture", "https://workspace.example/api/connectors/oauth/callback"
    )
    query = parse_qs(urlsplit(result["url"]).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"][0] not in json.dumps(runtime.store.rows("SELECT * FROM oauth_pending"))
    await runtime.registry.finish_oauth(query["state"][0], "fake-code")
    with pytest.raises(ValueError):
        await runtime.registry.finish_oauth(query["state"][0], "fake-code")
    headers = await runtime.registry.auth_headers(runtime.config.connectors["fixture"])
    assert headers == {"Authorization": "Bearer renewed-access-fixture"}
    assert "private-access-fixture" not in runtime.redact(
        "Echo private-access-fixture and private-refresh-fixture"
    )
    await runtime.registry.disconnect("fixture")
    assert any(request.url.path == "/revoke" for request in requests)
    assert "fixture" not in runtime.config.connectors
    await runtime.close()


@pytest.mark.parametrize("provider", ["1password", "bitwarden"])
async def test_dedicated_password_manager_values_are_injected_privately(runtime, monkeypatch, provider):
    runtime.store.set_preference(
        "password_manager",
        {
            "provider": provider,
            "url": "https://vault.example",
            "vault": "dedicated",
            "sites": {
                "shop.example": {
                    "item": "item-id",
                    "username_selector": "#user",
                    "password_selector": "#pass",
                }
            },
        },
    )
    runtime.vault.put("password_manager.token", "private-service-token")
    filled = []

    async def login(selector, value, expected_url):
        filled.append((selector, value, expected_url))

    runtime.browser = SimpleNamespace(
        page=SimpleNamespace(url="https://shop.example/login"), login=login, close=lambda: None
    )

    def handler(request):
        assert request.headers["authorization"] == "Bearer private-service-token"
        data = (
            {
                "fields": [
                    {"id": "username", "value": "private-user"},
                    {"id": "password", "value": "private-password"},
                ]
            }
            if provider == "1password"
            else {
                "data": {
                    "collectionIds": ["dedicated"],
                    "login": {"username": "private-user", "password": "private-password"},
                }
            }
        )
        return httpx.Response(200, json=data)

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **options: original(transport=httpx.MockTransport(handler))
    )
    result = await runtime.credentials.sign_in("shop.example", "task")
    assert len(filled) == 2 and filled[1][1] == "private-password"
    assert "private-password" not in json.dumps(result)
    assert runtime.redact("private-password") == "[REDACTED]"
    runtime.browser.page.url = "https://evil.example"
    with pytest.raises(ValueError):
        await runtime.credentials.sign_in("shop.example", "task")

    async def close():
        pass

    runtime.browser.close = close
    await runtime.close()


async def test_card_caps_exact_merchant_one_authorization_and_private_checkout(runtime):
    cancelled = []

    class Issuer:
        async def create_purchase_card(self, scope):
            return {"id": "card-fixture", "last4": "4242"}

        async def cancel_card(self, handle):
            cancelled.append(handle)

        async def private_card(self, handle):
            return dict(number="4242424242424242", cvc="123", exp_month=12, exp_year=2030)

    await runtime.wallet.provider.client.aclose()
    runtime.wallet.provider = Issuer()
    runtime.store.set_preference(
        "wallet",
        {
            "enabled": True,
            "daily_cap": 500,
            "monthly_cap": 1000,
            "merchants": ["merchant-one"],
            "currency": "EUR",
            "checkout_hosts": {"merchant-one": "shop.example"},
        },
    )
    item = await runtime.wallet.purchase(
        {"merchant": "merchant-one", "amount": 400, "currency": "EUR"}, "task"
    )
    with pytest.raises(ValueError):
        await runtime.wallet.purchase({"merchant": "merchant-one", "amount": 200, "currency": "EUR"}, "task")
    filled = []

    async def login(*args):
        filled.append(args)

    runtime.browser.login = login
    selectors = {key: "#" + key for key in ["number", "cvc", "exp_month", "exp_year"]}
    with pytest.raises(ValueError):
        await runtime.wallet.checkout(item["purchase"], "https://evil.example", selectors, "task")
    receipt = await runtime.wallet.checkout(
        item["purchase"], "https://shop.example/checkout", selectors, "task"
    )
    assert len(filled) == 4 and "4242424242424242" not in json.dumps(receipt)
    event = {
        "data": {
            "object": {
                "id": "auth-1",
                "card": "card-fixture",
                "currency": "eur",
                "pending_request": {"amount": 400},
                "merchant_data": {"network_id": "other"},
            }
        }
    }
    assert not runtime.wallet.authorize(event)
    event["data"]["object"]["merchant_data"]["network_id"] = "merchant-one"
    assert runtime.wallet.authorize(event)
    assert runtime.wallet.authorize(event)
    event["data"]["object"]["id"] = "auth-2"
    assert not runtime.wallet.authorize(event)
    await runtime.wallet.tick()
    assert cancelled == ["card-fixture"]
    assert runtime.store.rows("SELECT status FROM purchases")[0]["status"] == "spent"
    with pytest.raises(ValueError):
        await runtime.wallet.purchase({"merchant": "merchant-one", "amount": 200, "currency": "EUR"}, "task")
    await runtime.close()


async def test_issuer_timeout_reserves_budget_and_signature_expires(runtime):
    class Issuer:
        async def create_purchase_card(self, scope):
            raise TimeoutError()

    await runtime.wallet.provider.client.aclose()
    runtime.wallet.provider = Issuer()
    runtime.store.set_preference(
        "wallet",
        {"enabled": True, "daily_cap": 100, "monthly_cap": 100, "merchants": ["m"], "currency": "EUR"},
    )
    args = {"merchant": "m", "amount": 100, "currency": "EUR"}
    with pytest.raises(ValueError, match="uncertain"):
        await runtime.wallet.purchase(args, "task")
    with pytest.raises(ValueError, match="cap"):
        await runtime.wallet.purchase(args, "task")
    runtime.vault.put("wallet.stripe.webhook", "fixture-only-webhook")
    data = b'{"type":"fixture"}'
    stamp = str(int(time.time()))
    digest = hmac.new(b"fixture-only-webhook", stamp.encode() + b"." + data, hashlib.sha256).hexdigest()
    assert runtime.wallet.verify_webhook(data, f"t={stamp},v1={digest}")["type"] == "fixture"
    with pytest.raises(ValueError):
        runtime.wallet.verify_webhook(data, "t=1,v1=invalid")
    await runtime.close()


async def test_images_only_reach_explicit_vision_provider_and_not_history(runtime):
    image = io.BytesIO()
    Image.new("RGB", (20, 20), "red").save(image, format="PNG")
    item = await ingest(runtime, image.getvalue(), "photo.png")
    task = runtime.store.new_task("main", "Read receipt", "local")
    history = [{"role": "user", "content": "UNTRUSTED attachment: " + json.dumps(item)}]
    assert isinstance(runtime.provider_history(runtime.store.task(task), history)[0]["content"], str)
    runtime.config.providers["local"].vision = True
    blocks = runtime.provider_history(runtime.store.task(task), history)[0]["content"]
    assert blocks[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    runtime.checkpoint(task, history, 0)
    assert "base64" not in runtime.store.task(task)["history"]
    await runtime.close()


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "http://169.254.169.254",
        "http://10.0.0.1",
        "file:///etc/passwd",
        "https://user:pass@example.com",
        "http://[::1]",
        "https://example.com:8080",
    ],
)
def test_computer_and_proxy_refuse_local_metadata_and_credential_urls(url):
    with pytest.raises((ValueError, OSError)):
        public_url(url)
    host = urlsplit(url).hostname
    if host in {"127.0.0.1", "169.254.169.254", "10.0.0.1", "::1"}:
        with pytest.raises((ValueError, OSError)):
            resolve(host, 443)


async def test_prototype_origin_has_no_workspace_apis_or_unsandboxed_content(tmp_path):
    ident = "a" * 32
    (tmp_path / ident).mkdir()
    (tmp_path / ident / "index.html").write_text('<script>fetch("/api/state")</script>')
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(tmp_path)), base_url="http://prototype"
    ) as client:
        response = await client.get(f"/p/{ident}/index.html")
        assert "sandbox allow-scripts" in response.headers["content-security-policy"]
        assert "connect-src 'none'" in response.headers["content-security-policy"]
        assert "set-cookie" not in response.headers
        assert (await client.get("/api/state")).status_code == 404
        assert (await client.get(f"/p/{ident}/%2e%2e/secret")).status_code == 404


def test_http_transport_logging_removes_telegram_bot_credential():
    record = logging.LogRecord(
        "httpx",
        logging.INFO,
        "",
        1,
        "HTTP %s",
        ("https://api.telegram.org/bot12345:private-fixture/getUpdates",),
        None,
    )
    RedactBotURL().filter(record)
    assert "private-fixture" not in record.getMessage()


def test_fixture_benchmark_does_not_claim_model_accuracy():
    report = evaluate()
    assert report["synthetic_adapter_fixture"]
    assert report["hostile_interrupts"] == 0
    assert all(case["expected_action"] == case["actual_action"] for case in report["cases"])
    assert report["per_question"]["urgency"]["count"] >= 10


def test_nested_oauth_secrets_redacted_after_vault_resolution(tmp_path):
    store = Store(tmp_path)
    vault = Vault(store, tmp_path)
    vault.put("oauth", json.dumps({"access_token": "private-access", "refresh_token": "private-refresh"}))
    vault.get("oauth")
    assert {"private-access", "private-refresh"} <= vault.resolved
