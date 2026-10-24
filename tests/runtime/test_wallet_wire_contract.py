"""Stripe's documented HTTP contract, with synthetic records and no issuer account."""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs

import httpx
import pytest

from openduet.config import Config
from openduet.server import create_app

TOKEN = "wallet-contract-only-workspace-token"
SIGNING_SECRET = "whsec_fixture_not_a_real_credential"


@pytest.fixture
async def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENDUET_TOKEN", TOKEN)
    app = create_app(Config(data_dir=tmp_path, public_url="https://workspace"), start_worker=False)
    runtime = app.state.runtime
    requests = []

    def issuer(request):
        assert request.headers["stripe-version"] == "2025-03-31.basil"
        assert request.headers["authorization"] == "Bearer sk_test_fixture_not_a_real_key"
        values = parse_qs(request.content.decode())
        requests.append((request.method, request.url.path, values))
        if request.url.path == "/v1/issuing/cards":
            assert values["type"] == ["virtual"]
            assert values["currency"] == ["eur"]
            assert values["spending_controls[spending_limits][0][amount]"] == ["100"]
            assert values["spending_controls[spending_limits][0][interval]"] == ["all_time"]
            return httpx.Response(200, json={"id": "ic_fixture", "last4": "4242", "livemode": False})
        assert request.url.path == "/v1/issuing/cards/ic_fixture"
        assert values == {"status": ["canceled"]}
        return httpx.Response(200, json={"id": "ic_fixture", "status": "canceled"})

    await runtime.wallet.provider.client.aclose()
    runtime.wallet.provider.client = httpx.AsyncClient(
        base_url="https://api.stripe.com", transport=httpx.MockTransport(issuer)
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://workspace"
    ) as client:
        response = await client.post(
            "/api/wallet",
            headers={"Authorization": "Bearer " + TOKEN},
            json={
                "enabled": True,
                "key": "sk_test_fixture_not_a_real_key",
                "cardholder": "ich_fixture",
                "webhook": SIGNING_SECRET,
                "daily_cap": 100,
                "monthly_cap": 100,
                "currency": "EUR",
                "merchants": ["merchant-demo"],
                "checkout_hosts": {"merchant-demo": "shop.example"},
            },
        )
        assert response.status_code == 200
        try:
            yield client, runtime, requests
        finally:
            await runtime.close()


async def signed_authorization(client, *, amount=100, merchant="merchant-demo", currency="eur"):
    content = json.dumps(
        {
            "type": "issuing_authorization.request",
            "data": {
                "object": {
                    "id": "iauth_fixture",
                    "card": "ic_fixture",
                    "currency": currency,
                    "pending_request": {"amount": amount, "currency": currency},
                    "merchant_data": {"network_id": merchant},
                }
            },
        }
    ).encode()
    stamp = str(int(time.time()))
    signature = hmac.new(SIGNING_SECRET.encode(), stamp.encode() + b"." + content, hashlib.sha256).hexdigest()
    response = await client.post(
        "/api/wallet/webhook",
        content=content,
        headers={"Stripe-Signature": f"t={stamp},v1={signature}", "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.headers["stripe-version"] == "2025-03-31.basil"
    assert response.headers["content-type"].startswith("application/json")
    return response.json()["approved"]


async def approve_card(runtime, requests):
    task = runtime.store.new_task("main", "Create a card limited to 1 EUR for merchant-demo.", "local")
    history = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "create-card",
                    "function": {
                        "name": "purchase_card",
                        "arguments": json.dumps(
                            {"merchant": "merchant-demo", "amount": 100, "currency": "EUR"}
                        ),
                    },
                }
            ],
        }
    ]
    assert not await runtime.process_calls(runtime.store.task(task), history)
    assert not requests
    pending = runtime.store.rows("SELECT id FROM calls WHERE status='pending'")[0]
    runtime.approvals.decide(pending["id"], "approve")
    assert await runtime.process_calls(runtime.store.task(task), history)
    assert len(requests) == 1


async def test_signed_webhook_versions_exact_scope_and_cancel_after_authorization(workspace):
    client, runtime, requests = workspace
    assert not await signed_authorization(client)
    await approve_card(runtime, requests)
    assert not await signed_authorization(client, amount=101)
    assert not await signed_authorization(client, merchant="other-merchant")
    assert not await signed_authorization(client, currency="usd")
    assert await signed_authorization(client)
    assert await signed_authorization(client)
    await runtime.wallet.tick()
    assert [request[:2] for request in requests] == [
        ("POST", "/v1/issuing/cards"),
        ("POST", "/v1/issuing/cards/ic_fixture"),
    ]
    assert runtime.store.rows("SELECT status FROM purchases")[0]["status"] == "spent"


async def test_disabling_wallet_declines_a_previously_issued_card(workspace):
    client, runtime, requests = workspace
    await approve_card(runtime, requests)
    runtime.store.set_preference("wallet", runtime.wallet.settings() | {"enabled": False})
    assert not await signed_authorization(client)
    assert runtime.store.rows("SELECT status FROM purchases")[0]["status"] == "active"


@pytest.mark.parametrize("prefix", ["sk_live_", "rk_live_"])
async def test_live_keys_need_operator_opt_in_before_replacing_test_credentials(workspace, prefix):
    client, runtime, requests = workspace
    response = await client.post(
        "/api/wallet",
        headers={"Authorization": "Bearer " + TOKEN},
        json={"key": prefix + "fixture_not_a_real_key"},
    )
    assert response.status_code == 400
    assert runtime.vault.get("wallet.stripe.key") == "sk_test_fixture_not_a_real_key"
    assert runtime.wallet.settings()["enabled"]
    assert not requests


@pytest.mark.parametrize("prefix", ["sk_live_", "rk_live_"])
async def test_stored_live_keys_are_blocked_after_upgrade_without_preventing_cancellation(workspace, prefix):
    client, runtime, requests = workspace
    await approve_card(runtime, requests)
    runtime.vault.put("wallet.stripe.key", prefix + "fixture_not_a_real_key")
    assert not await signed_authorization(client)
    with pytest.raises(ValueError, match="test-mode issuer"):
        await runtime.wallet.purchase({"merchant": "merchant-demo", "amount": 100, "currency": "EUR"}, "task")
    purchase = runtime.store.rows("SELECT id FROM purchases")[0]["id"]
    with pytest.raises(ValueError, match="test-mode issuer"):
        await runtime.wallet.checkout(purchase, "https://shop.example", {}, "task")
    assert len(requests) == 1
    # Revocation of an existing live card remains possible in test-only deployments.
    requests.clear()

    def revoke(request):
        assert request.url.path == "/v1/issuing/cards/ic_fixture"
        assert parse_qs(request.content.decode()) == {"status": ["canceled"]}
        requests.append(request.url.path)
        return httpx.Response(200, json={"id": "ic_fixture", "status": "canceled"})

    await runtime.wallet.provider.client.aclose()
    runtime.wallet.provider.client = httpx.AsyncClient(
        base_url="https://api.stripe.com", transport=httpx.MockTransport(revoke)
    )
    await runtime.wallet.cancel(purchase)
    assert requests == ["/v1/issuing/cards/ic_fixture"]
