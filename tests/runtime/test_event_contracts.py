import base64
import json
import time

from openduet.catalog import RECIPES, directory
from openduet.config import Config
from openduet.mappers import normalize, timestamp
from openduet.plugins import local_archive
from openduet.runtime import Runtime
from openduet.store import Store


def test_gmail_received_sent_and_reply_headers_are_normalized():
    body = base64.urlsafe_b64encode(b"Please review the contract.").decode()
    raw = {
        "id": "gmail-id",
        "threadId": "thread-one",
        "labelIds": ["SENT"],
        "internalDate": "1800000000000",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": "Contract"},
                {"name": "From", "value": "owner@example.com"},
                {"name": "To", "value": "client@example.com"},
                {"name": "In-Reply-To", "value": "<previous@x>"},
            ],
            "body": {"data": body},
        },
    }
    event = normalize(raw, "mail.received", "gmail")
    assert event["kind"] == "mail.sent"
    assert event["payload"]["in_reply_to"] == "<previous@x>"
    assert event["payload"]["thread_id"] == "thread-one"
    assert event["payload"]["to"] == "client@example.com"
    assert event["body"] == "Please review the contract."
    assert event["occurred_at"] == 1800000000


def test_microsoft_calendar_and_slack_contracts():
    event = normalize(
        {
            "id": "m",
            "from": {"emailAddress": {"address": "client@example.com"}},
            "body": {"content": "Please review"},
            "receivedDateTime": "2026-10-22T09:00:00Z",
        },
        "mail.received",
        "microsoft-365",
    )
    assert event["sender"] == "client@example.com" and event["body"] == "Please review"
    calendar = normalize(
        {
            "id": "c",
            "summary": "Meeting",
            "start": {"dateTime": "2026-10-22T09:00:00-04:00"},
            "end": {"dateTime": "2026-10-22T10:00:00-04:00"},
            "htmlLink": "https://calendar.example/event",
        },
        "calendar.event_created",
        "google-calendar",
    )
    assert calendar["payload"]["end"] - calendar["payload"]["start"] == 3600
    assert timestamp("2026-10-22T09:00:00-04:00") == timestamp("2026-10-22T13:00:00Z")
    slack = normalize(
        {"ts": "1800000000.1", "thread_ts": "1799999999.1", "user": "U123", "text": "Hello"},
        "chat.message",
        "slack",
    )
    assert slack["id"] == "1800000000.1" and slack["payload"]["thread_id"] == "1799999999.1"


def test_all_curated_directory_contracts_have_permissions_and_explicit_review():
    assert len(directory()) == 17
    for entry in directory():
        assert entry["setup_url"].startswith("https://")
        assert entry["scopes"] and entry["capability"] and entry["limits"]
        assert {"send", "pay", "sign", "delete", "publish"} <= set(entry["approval_actions"])
    assert set(RECIPES) == {
        "missed-messages",
        "unpaid-invoices",
        "meeting-scheduling",
        "contract-preparation",
        "payroll-preparation",
    }
    assert all("Ask before" in recipe["prompt"] for recipe in RECIPES.values())


async def test_plugin_local_path_adds_skills_and_directory_without_connecting(tmp_path):
    runtime = Runtime(Config(data_dir=tmp_path / "data"), Store(tmp_path / "data"))
    plugin = tmp_path / "plugin"
    (plugin / "skills" / "demo").mkdir(parents=True)
    (plugin / "plugin.json").write_text(
        json.dumps(
            {
                "name": "fixture-plugin",
                "description": "Preparation",
                "connectors": [{"name": "fixture-account", "url": "https://fixture.example/mcp"}],
            }
        )
    )
    (plugin / "skills" / "demo" / "SKILL.md").write_text(
        "---\nname: fixture-skill\ndescription: Prepare a fixture\n---\nFULL BODY SHOULD ONLY LOAD ON DEMAND"
    )
    runtime.plugins.install(local_archive(plugin))
    assert any(entry["name"] == "fixture-account" for entry in runtime.plugins.connections())
    assert runtime.config.connectors == {}
    task = runtime.store.new_task("main", "Prepare work", "local")
    history = runtime.initial_history(runtime.store.task(task))
    assert "FULL BODY SHOULD" not in json.dumps(history)
    assert "FULL BODY SHOULD" in runtime.plugins.load("fixture-skill")
    runtime.plugins.uninstall("fixture-plugin")
    assert not runtime.plugins.connections()
    await runtime.close()


async def test_calendar_conflicts_include_travel_buffer_and_ignore_self(tmp_path):
    runtime = Runtime(Config(data_dir=tmp_path), Store(tmp_path))
    runtime.attention.configure({"travel_minutes": 30})
    records = [
        {
            "id": "first",
            "subject": "A",
            "payload": {"start": 10000, "end": 11000},
            "start": 10000,
            "end": 11000,
        },
        {
            "id": "second",
            "subject": "Flight B",
            "payload": {"start": 11500, "end": 12500},
            "start": 11500,
            "end": 12500,
        },
    ]
    runtime.attention.events.ingest("calendar", records, "calendar.event_created")
    event = json.loads(
        runtime.store.rows("SELECT data FROM connector_events ORDER BY created LIMIT 1")[0]["data"]
    )
    conflicts = runtime.attention.calendar_conflicts(event)
    assert len(conflicts) == 1 and conflicts[0]["subject"] == "Flight B"
    await runtime.close()


async def test_exact_reply_labels_do_not_match_unrelated_subject(tmp_path):
    runtime = Runtime(Config(data_dir=tmp_path), Store(tmp_path))
    runtime.store.execute(
        "INSERT INTO decisions(decision_id,kind,event_payload,ts) VALUES('d','mail.received',?,?)",
        (json.dumps({"message_id": "<exact@x>", "subject": "Same title"}), time.time()),
    )
    event = {"payload": {"in_reply_to": "<other@x>", "subject": "Same title"}}
    runtime.attention.record_thread_reply(event)
    assert not runtime.store.rows("SELECT * FROM labels")
    event["payload"]["in_reply_to"] = "<exact@x>"
    runtime.attention.record_thread_reply(event)
    assert runtime.store.rows("SELECT source FROM labels")[0]["source"] == "reply-header"
    await runtime.close()
