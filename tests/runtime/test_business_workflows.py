"""Five fixture workflows must retrieve evidence and stop before external effects."""

import json

import pytest

from openduet.catalog import RECIPES
from openduet.config import Config
from openduet.providers import Reply
from openduet.runtime import Runtime
from openduet.store import Store
from openduet.tools import Tool, schema

CASES = [
    (
        "missed-messages",
        "list_messages",
        "send_reply",
        {"message_id": "mail-1", "sender": "client@example.test", "text": "Please confirm the draft."},
        {"to": "client@example.test", "subject": "Draft", "body": "Prepared confirmation"},
    ),
    (
        "unpaid-invoices",
        "list_invoices",
        "send_reminder",
        {"invoice": "inv-1", "due": "2026-10-20", "amount": 500, "currency": "EUR"},
        {
            "to": "client@example.test",
            "subject": "Invoice inv-1",
            "body": "Reminder for EUR 500 invoice inv-1",
        },
    ),
    (
        "meeting-scheduling",
        "list_calendar",
        "create_meeting",
        {"event": "event-1", "free_slot": "2026-10-23T10:00:00Z"},
        {"attendee": "client@example.test", "new_time": "2026-10-23T10:00:00Z"},
    ),
    (
        "contract-preparation",
        "get_contract",
        "send_for_signature",
        {"document": "agreement-1", "reviewed": False},
        {"document": "agreement-1", "signer": "client@example.test"},
    ),
    (
        "payroll-preparation",
        "get_payroll",
        "submit_payroll",
        {"batch": "payroll-1", "payees": [{"name": "Fixture employee", "gross_minor": 150000}]},
        {"batch": "payroll-1", "total_minor": 150000},
    ),
]


@pytest.mark.parametrize("recipe,reader,writer,record,payload", CASES)
async def test_business_workflow_requires_exact_review_and_real_fixture_source(
    tmp_path, recipe, reader, writer, record, payload
):
    effects = []
    state = {"step": 0}

    def call(name, args):
        return Reply(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": name,
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(args)},
                    }
                ],
            },
            2,
            2,
        )

    class Model:
        def __init__(self, config):
            pass

        async def complete(self, messages, tools):
            state["step"] += 1
            if state["step"] == 1:
                return call(reader, {})
            if state["step"] == 2:
                return call(writer, payload)
            source = next(
                json.loads(message["content"])["source_id"]
                for message in messages
                if message["role"] == "tool" and message.get("name") == reader
            )
            return Reply(
                {"role": "assistant", "content": "The reviewed work has a receipt. [^" + source + "]"}, 2, 2
            )

    runtime = Runtime(Config(data_dir=tmp_path), Store(tmp_path), provider_factory=Model)

    async def read(arguments, task):
        return record

    async def write(arguments, task):
        effects.append(arguments)
        return {"receipt": "fixture-effect-once"}

    runtime.tools.catalog[reader] = Tool(
        reader, "Read fixture account", schema({}), read, False, "fixture", reader, "read"
    )
    runtime.tools.catalog[writer] = Tool(
        writer,
        "External effect",
        schema(
            {
                key: {"type": "integer" if isinstance(value, int) else "string"}
                for key, value in payload.items()
            }
        ),
        write,
        True,
        "fixture",
        writer,
        "consequential",
    )
    task = runtime.store.new_task("main", RECIPES[recipe]["prompt"], "local")
    await runtime.run_task(task)
    assert runtime.store.task(task)["status"] == "awaiting_approval"
    assert effects == []
    pending = runtime.store.rows("SELECT * FROM calls WHERE status='pending'")[0]
    assert json.loads(pending["arguments"]) == payload
    assert runtime.sources.listing(task)
    runtime.approvals.decide(pending["id"], "approve")
    await runtime.run_task(task)
    assert effects == [payload]
    assert runtime.store.task(task)["status"] == "ready"
    assert (
        "[Unverified source"
        not in runtime.store.rows("SELECT content FROM messages WHERE role='assistant'")[0]["content"]
    )
    await runtime.close()
