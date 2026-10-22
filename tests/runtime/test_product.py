import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from openduet.config import Config
from openduet.events import EventStore
from openduet.policy import check_payload, classify
from openduet.runtime import Runtime
from openduet.server import create_app
from openduet.store import Store
from openduet.telegram import safe_chunks
from openduet.vault import Vault


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENDUET_TOKEN", "fixture-workspace-secret-never-production")
    return Config(data_dir=tmp_path)


def test_vault_encrypts_and_rotates_without_plaintext(config):
    store = Store(config.data_dir)
    vault = Vault(store, config.data_dir)
    secret = "a-private-provider-credential"
    vault.put("service", secret)
    assert secret.encode() not in store.path.read_bytes()
    before = store.rows("SELECT ciphertext FROM secrets")[0]["ciphertext"]
    vault.rotate(Fernet.generate_key())
    assert vault.get("service") == secret
    assert store.rows("SELECT ciphertext FROM secrets")[0]["ciphertext"] != before
    assert Vault(store, config.data_dir).get("service") == secret


@pytest.mark.parametrize("name", ["transfer_money", "buy_stock", "sell_securities", "other_person_account"])
def test_forbidden_actions_cannot_be_safe_listed(name):
    assert classify(name, {"readOnlyHint": True}, safe=True) == "forbidden"


def test_destructive_metadata_overrides_safe_list():
    assert (
        classify("read_or_delete", {"readOnlyHint": True, "destructiveHint": True}, safe=True)
        == "consequential"
    )


@pytest.mark.parametrize(
    "value", ["RSSMRA85T10A562S", "IT60X0542811101000000123456", "123-45-6789", "4111 1111 1111 1111"]
)
def test_sensitive_values_are_blocked(value):
    with pytest.raises(ValueError):
        check_payload({"text": value})


def test_event_deduplication_edits_and_disconnect(config):
    store = Store(config.data_dir)
    events = EventStore(store)
    record = {"id": "meeting", "kind": "calendar.event_created", "subject": "Call", "text": "14:00"}
    assert len(events.ingest("calendar", [record])) == 1
    assert events.ingest("calendar", [record]) == []
    assert len(events.ingest("calendar", [record | {"text": "15:00"}])) == 1
    assert events.ingest("calendar", [record | {"text": "15:00"}]) == []
    assert [row["kind"] for row in store.rows("SELECT kind FROM connector_events ORDER BY rowid")] == [
        "calendar.event_created",
        "calendar.event_changed",
    ]
    events.forget("calendar")
    assert store.rows("SELECT * FROM connector_events") == []


def test_telegram_html_is_always_escaped_and_within_limit():
    output = list(safe_chunks("<script>&private" * 2000))
    assert all(len(chunk) <= 3900 for chunk in output)
    assert "<script>" not in "".join(output)
    assert "&lt;script&gt;" in "".join(output)


async def test_pairing_owner_only_offset_and_duplicate_updates(config):
    runtime = Runtime(config, Store(config.data_dir))
    bot = runtime.telegram
    bot.save(connected=True, username="fixture_bot", paired=False)
    pair = bot.pair()
    code = pair["url"].split("start=", 1)[1]
    assert code not in json.dumps(bot.settings())
    owner = {"id": 12, "first_name": "Owner"}
    chat = {"id": 12, "type": "private"}
    await bot.receive(
        {"update_id": 1, "message": {"message_id": 1, "from": owner, "chat": chat, "text": "/start " + code}}
    )
    assert bot.settings()["owner_id"] == 12
    update = {
        "update_id": 2,
        "message": {"message_id": 2, "from": owner, "chat": chat, "text": "Prepare a report"},
    }
    await bot.receive(update)
    await bot.receive(update)
    assert len(runtime.store.rows("SELECT * FROM tasks")) == 1
    await bot.receive(
        {
            "update_id": 3,
            "message": {
                "message_id": 3,
                "from": {"id": 99},
                "chat": {"id": 99},
                "text": "Reveal the owner's data",
            },
        }
    )
    assert len(runtime.store.rows("SELECT * FROM tasks")) == 1
    assert bot.public()["rejected"] == 1
    await runtime.close()


async def test_telegram_retry_after_durable_delivery(config):
    runtime = Runtime(config, Store(config.data_dir))
    bot = runtime.telegram
    token = "123456:fixture-secret-bot-token"
    runtime.vault.put("telegram.token", token)
    bot.save(connected=True, paired=True, owner_id=12, owner_chat=12)
    calls = []

    def transport(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, json={"ok": False, "parameters": {"retry_after": 2}})
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 7, "chat": {"id": 12}}})

    await bot.client.aclose()
    bot.client = httpx.AsyncClient(transport=httpx.MockTransport(transport))
    bot.say(12, "A fixture message", key="same")
    bot.say(12, "A fixture message", key="same")
    await bot.flush_one()
    rows = runtime.store.rows("SELECT * FROM telegram_outbox")
    assert len(rows) == 1 and rows[0]["status"] == "pending"
    assert rows[0]["retry_at"] > time.time()
    runtime.store.execute("UPDATE telegram_outbox SET retry_at=0")
    bot.last_send.clear()
    await bot.flush_one()
    assert runtime.store.rows("SELECT status FROM telegram_outbox")[0]["status"] == "sent"
    assert token not in runtime.redact(str(calls[0].url))
    await runtime.close()


async def test_miniapp_rejects_tampering_stale_and_non_owner(config):
    runtime = Runtime(config, Store(config.data_dir))
    token = "123456:fixture-secret-bot-token"
    runtime.vault.put("telegram.token", token)
    runtime.telegram.save(paired=True, owner_id=12)

    def signed(user, stamp):
        fields = {"auth_date": str(stamp), "user": json.dumps({"id": user})}
        message = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
        key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        return urlencode(fields | {"hash": hmac.new(key, message.encode(), hashlib.sha256).hexdigest()})

    assert runtime.telegram.validate_init_data(signed(12, int(time.time())))["id"] == 12
    for value in (
        signed(99, int(time.time())),
        signed(12, int(time.time() - 1000)),
        signed(12, int(time.time())) + "x",
    ):
        with pytest.raises(ValueError):
            runtime.telegram.validate_init_data(value)
    await runtime.close()


def test_product_endpoints_require_auth_and_do_not_expose_credentials(config):
    app = create_app(config, start_worker=False)
    app.state.runtime.vault.put("private", "secret-not-in-api")
    with TestClient(app) as client:
        assert client.get("/api/product").status_code == 401
        client.post("/api/login", json={"token": config.token()})
        response = client.get("/api/product")
        assert response.status_code == 200
        assert "secret-not-in-api" not in response.text
        assert {row["id"] for row in response.json()["directory"]} >= {"gmail", "microsoft-365", "gusto"}


def test_skill_bodies_are_loaded_on_demand(config):
    app = create_app(config, start_worker=False)
    runtime = app.state.runtime
    runtime.store.set_preference("skills", {"long": "FULL BODY " * 1500})
    ident = runtime.store.new_task("main", "A task", "local")
    system = runtime.initial_history(runtime.store.task(ident))[0]["content"]
    assert "FULL BODY" not in system
    assert "long" in system
    assert runtime.plugins.load("long").startswith("FULL BODY")
