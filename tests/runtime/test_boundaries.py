import hashlib
import hmac
import json
import sys
import time
from types import SimpleNamespace
from urllib.parse import urlencode

import httpx
import pytest

from openduet.artifacts import create
from openduet.config import Config
from openduet.runtime import Runtime
from openduet.server import create_app
from openduet.store import Store
from openduet.tools import Tool, schema


@pytest.fixture
def runtime(tmp_path):
    result = Runtime(Config(data_dir=tmp_path), Store(tmp_path))
    result.vault.put("telegram.token", "123456:fixture-private-token")
    result.telegram.save(
        connected=True, paired=True, owner_id=12, owner_chat=12, session_nonce="fixture-nonce"
    )
    return result


def fake_api(runtime, handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_silent_notifications_batch_persist_dedup_and_hide_internal_metadata(runtime):
    first = runtime.telegram.owner_message("First item", silent=True, key="decision:first")
    second = runtime.telegram.owner_message("Second item", silent=True, key="decision:second")
    assert first == second
    assert runtime.telegram.owner_message("Second item", silent=True, key="decision:second") == second
    rows = runtime.store.rows("SELECT * FROM telegram_outbox")
    assert len(rows) == 1
    payload = json.loads(rows[0]["payload"])
    assert payload["disable_notification"] and payload["_decisions"] == ["first", "second"]
    assert "1. First item" in payload["text"] and "2. Second item" in payload["text"]
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 50, "chat": {"id": 12}}})

    await runtime.telegram.client.aclose()
    runtime.telegram.client = fake_api(runtime, handler)
    runtime.store.execute("UPDATE telegram_outbox SET retry_at=0")
    await runtime.telegram.flush_one()
    assert "_decisions" not in captured[0]
    runtime.telegram.say(99, "Must not go to a previous owner")
    runtime.telegram.last_send.clear()
    await runtime.telegram.flush_one()
    assert len(captured) == 1
    await runtime.close()


async def test_pending_progress_edit_is_not_cancelled_by_its_own_duplicate(runtime):
    payload = {"chat_id": 12, "message_id": 5, "text": "First"}
    runtime.telegram.enqueue("editMessageText", payload, "edit-one")
    runtime.telegram.enqueue("editMessageText", payload, "edit-one")
    assert (
        runtime.store.rows("SELECT status FROM telegram_outbox WHERE id='edit-one'")[0]["status"] == "pending"
    )
    runtime.telegram.enqueue("editMessageText", payload | {"text": "Latest"}, "edit-two")
    assert len(runtime.store.rows("SELECT id FROM telegram_outbox WHERE status='pending'")) == 1
    assert (
        runtime.store.rows("SELECT status FROM telegram_outbox WHERE id='edit-one'")[0]["status"]
        == "cancelled"
    )
    await runtime.close()


async def test_preparation_stays_silent_until_finished(runtime):
    event = {
        "id": "event",
        "kind": "mail.received",
        "source": "gmail:one",
        "subject": "Review",
        "text": "Prepare a draft",
        "payload": {},
        "links": [],
        "actors": [],
    }
    await runtime.attention.prepare(event)
    await runtime.telegram.sync_tasks()
    assert runtime.store.rows("SELECT * FROM telegram_outbox") == []
    task = runtime.store.rows("SELECT id FROM tasks")[0]["id"]
    runtime.store.message("main", "assistant", "Finished draft", task)
    runtime.store.status(task, "ready")
    await runtime.telegram.sync_tasks()
    rows = runtime.store.rows("SELECT payload FROM telegram_outbox")
    assert len(rows) == 1
    assert json.loads(rows[0]["payload"])["disable_notification"] is True
    await runtime.close()


async def test_each_resumed_ready_response_is_delivered_once(runtime):
    task = runtime.store.new_task("main", "Prepare work", "local")
    runtime.store.execute("INSERT INTO task_surfaces VALUES(?,'telegram',12,NULL,NULL,NULL)", (task,))
    runtime.store.status(task, "ready")
    runtime.store.message("main", "assistant", "Independent work ready", task)
    await runtime.telegram.sync_tasks()
    await runtime.telegram.sync_tasks()
    runtime.store.message("main", "assistant", "Reviewed deferred action now has a receipt", task)
    await runtime.telegram.sync_tasks()
    assert len(runtime.store.rows("SELECT id FROM telegram_outbox WHERE id LIKE 'ready:%'")) == 2
    await runtime.close()


async def test_voice_fixture_transcript_is_visible_and_attached_to_same_task(runtime, monkeypatch):
    runtime.config.voice_model = "/fixture/local-whisper"

    class Whisper:
        def __init__(self, path, **kwargs):
            assert path == "/fixture/local-whisper" and kwargs["local_files_only"]

        def transcribe(self, path, **kwargs):
            return [SimpleNamespace(text="Prepare a slide deck")], SimpleNamespace(duration=3)

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Whisper))

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, content=b"fixture-ogg-inert-bytes")
        return httpx.Response(200, json={"ok": True, "result": {"file_path": "voice/one.ogg"}})

    await runtime.telegram.client.aclose()
    runtime.telegram.client = fake_api(runtime, handler)
    await runtime.telegram.receive(
        {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "chat": {"id": 12, "type": "private"},
                "from": {"id": 12},
                "voice": {"file_id": "voice", "file_size": 22},
            },
        }
    )
    task = runtime.store.rows("SELECT * FROM tasks")[0]
    assert "Prepare a slide deck" in task["request"] and "UNTRUSTED attachment" in task["request"]
    assert runtime.store.rows("SELECT task FROM attachments")[0]["task"] == task["id"]
    assert (
        "I heard"
        in json.loads(runtime.store.rows("SELECT payload FROM telegram_outbox")[0]["payload"])["text"]
    )
    runtime.store.status(task["id"], "ready")
    runtime.store.message("main", "assistant", "Prepared", task["id"])
    await runtime.telegram.sync_tasks()
    assert not runtime.store.rows("SELECT * FROM telegram_outbox WHERE method='sendDocument'")
    await runtime.close()


async def test_deck_delivery_has_caption_revision_button_and_real_pptx(runtime):
    task = runtime.store.new_task("main", "Prepare deck", "local")
    item = create(
        runtime.store,
        runtime.config.data_dir / "artifacts",
        task,
        "Fixture deck",
        "pptx",
        json.dumps(
            {"slides": [{"title": "A real slide", "body": "Review this draft", "notes": "Source: fixture"}]}
        ),
    )
    runtime.telegram.send_artifact(12, item)
    row = runtime.store.rows("SELECT payload FROM telegram_outbox")[0]
    payload = json.loads(row["payload"])
    assert payload["caption"] == "Fixture deck"
    assert payload["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "revise:" + item["id"]
    captured = []

    def handler(request):
        captured.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1, "chat": {"id": 12}}})

    await runtime.telegram.client.aclose()
    runtime.telegram.client = fake_api(runtime, handler)
    await runtime.telegram.flush_one()
    assert b".pptx" in captured[0].content and b"PK" in captured[0].content
    await runtime.close()


async def test_secret_echo_and_identifiers_do_not_enter_sources_or_provider_history(runtime):
    runtime.vault.put("fixture.key", "private-fixture-credential")

    async def read(arguments, task):
        return {
            "text": "Echo private-fixture-credential and 123-45-6789",
            "url": "https://fixture.example/record",
        }

    runtime.tools.catalog["read_fixture"] = Tool(
        "read_fixture", "Read", schema({}), read, False, "fixture", "read_fixture", "read"
    )
    task = runtime.store.new_task("main", "Research", "local")
    result = await runtime.tools.invoke("read_fixture", {}, task)
    source = runtime.sources.listing(task)[0]
    assert "private-fixture-credential" not in result + source["excerpt"]
    assert "123-45-6789" not in result + source["excerpt"]
    history = runtime.provider_history(
        runtime.store.task(task), [{"role": "user", "content": "Identifier 123-45-6789"}]
    )
    assert "123-45-6789" not in json.dumps(history)
    await runtime.close()


async def test_deleted_channel_removes_sources_files_versions_and_pending_delivery(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENDUET_TOKEN", "fixture-root-token-for-deletion-test")
    app = create_app(Config(data_dir=tmp_path), start_worker=False)
    runtime = app.state.runtime
    task = runtime.store.new_task("main", "Private fixture", "local")
    item = create(runtime.store, tmp_path / "artifacts", task, "Draft", "md", "Private text")
    runtime.sources.register(task, "fixture", {"text": "Private text"})
    runtime.store.status(task, "ready")
    runtime.telegram.say(12, "Private text", key="ready:" + task)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://workspace",
        headers={"Authorization": "Bearer fixture-root-token-for-deletion-test"},
    ) as client:
        assert (await client.delete("/api/channels/main")).status_code == 200
        assert (await client.get("/api/artifacts/" + item["id"])).status_code == 404
    assert not runtime.store.rows("SELECT * FROM sources")
    assert not runtime.store.rows("SELECT * FROM artifact_versions")
    assert not runtime.store.rows("SELECT * FROM telegram_outbox")
    assert not (tmp_path / "artifacts" / (item["id"] + ".md")).exists()
    await runtime.close()


async def test_miniapp_session_is_scoped_and_revoked_by_pair_change(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENDUET_TOKEN", "fixture-root-token-for-miniapp-test")
    app = create_app(Config(data_dir=tmp_path, public_url="https://workspace"), start_worker=False)
    runtime = app.state.runtime
    token = "123456:fixture-only-bot-token"
    runtime.vault.put("telegram.token", token)
    runtime.telegram.save(connected=True, paired=True, owner_id=12, owner_chat=12, session_nonce="nonce-one")
    fields = {"user": json.dumps({"id": 12}), "auth_date": str(int(time.time()))}
    check = "\n".join(key + "=" + fields[key] for key in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://workspace"
    ) as client:
        assert (
            await client.post("/api/telegram/session", json={"init_data": urlencode(fields)})
        ).status_code == 200
        assert (await client.get("/api/state")).status_code == 200
        assert (await client.post("/api/models", json={})).status_code == 403
        runtime.telegram.save(session_nonce="nonce-two")
        assert (await client.get("/api/state")).status_code == 401
    await runtime.close()


async def test_numeric_card_identifiers_are_withheld_without_corrupting_json(runtime):
    async def read(arguments, task):
        return {"number": 4111111111111111, "safe_total": 200}

    runtime.tools.catalog["read_record"] = Tool(
        "read_record", "Read", schema({}), read, False, "fixture", "read_record", "read"
    )
    task = runtime.store.new_task("main", "Read record", "local")
    value = json.loads(await runtime.tools.invoke("read_record", {}, task))
    assert value["data"]["number"] == "[sensitive identifier withheld]"
    assert value["data"]["safe_total"] == 200
    await runtime.close()


async def test_card_cancellation_race_keeps_authorized_spend_reserved(runtime):
    class Issuer:
        async def create_purchase_card(self, scope):
            return {"id": "race-card", "last4": "4242"}

        async def cancel_card(self, handle):
            assert runtime.wallet.authorize(
                {
                    "data": {
                        "object": {
                            "id": "auth-race",
                            "card": handle,
                            "currency": "eur",
                            "pending_request": {"amount": 100},
                            "merchant_data": {"network_id": "merchant"},
                        }
                    }
                }
            )

    await runtime.wallet.provider.client.aclose()
    runtime.wallet.provider = Issuer()
    runtime.store.set_preference(
        "wallet",
        {"enabled": True, "daily_cap": 100, "monthly_cap": 100, "currency": "EUR", "merchants": ["merchant"]},
    )
    item = await runtime.wallet.purchase({"merchant": "merchant", "amount": 100, "currency": "EUR"}, "task")
    await runtime.wallet.cancel(item["purchase"])
    assert runtime.store.rows("SELECT status FROM purchases")[0]["status"] == "spent"
    with pytest.raises(ValueError, match="cap"):
        await runtime.wallet.purchase({"merchant": "merchant", "amount": 1, "currency": "EUR"}, "task")
    await runtime.close()


async def test_monthly_cap_includes_first_day_even_in_31_day_month(runtime, monkeypatch):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    class BudgetOnlyIssuer:
        async def create_purchase_card(self, scope):
            raise AssertionError("An exhausted monthly cap must not contact the issuer")

    await runtime.wallet.provider.client.aclose()
    runtime.wallet.provider = BudgetOnlyIssuer()
    runtime.attention.configure({"timezone": "UTC"})
    start = datetime(2026, 1, 1, tzinfo=ZoneInfo("UTC")).timestamp()
    now = datetime(2026, 1, 31, 18, tzinfo=ZoneInfo("UTC")).timestamp()
    runtime.store.execute(
        "INSERT INTO purchases VALUES('old','task','merchant',100,'EUR',?,'old-card','spent',?,NULL)",
        (start + 900, start),
    )
    runtime.store.set_preference(
        "wallet",
        {"enabled": True, "daily_cap": 500, "monthly_cap": 500, "currency": "EUR", "merchants": ["merchant"]},
    )
    monkeypatch.setattr("openduet.wallet.time.time", lambda: now)
    with pytest.raises(ValueError, match="cap"):
        await runtime.wallet.purchase({"merchant": "merchant", "amount": 450, "currency": "EUR"}, "task")
    await runtime.close()
