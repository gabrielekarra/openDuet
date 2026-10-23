import asyncio
import json

import pytest
from mcp.types import Tool as MCPTool

from openduet import connectors
from openduet.config import Config
from openduet.runtime import Runtime
from openduet.store import Store
from openduet.tools import StaleToolBinding, Tool, schema


def prepare(runtime, name, arguments=None):
    task = runtime.store.new_task("main", "Send the reviewed reply", "local")
    history = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "one",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(arguments or {})},
                }
            ],
        }
    ]
    runtime.checkpoint(task, history, 0)
    return task, history


@pytest.mark.parametrize("read_only", [True, False])
async def test_restart_replays_only_recorded_reads_and_blocks_uncertain_effects(tmp_path, read_only):
    config = Config(data_dir=tmp_path)
    runtime = Runtime(config, Store(tmp_path))
    effects = []

    async def execute(arguments, task):
        effects.append(task)
        return {"receipt": "observed"}

    tool = Tool(
        "operation", "Fixture operation", schema({}), execute, risk="read" if read_only else "prepare"
    )
    runtime.tools.catalog[tool.name] = tool
    task, history = prepare(runtime, tool.name)
    assert await runtime.process_calls(runtime.store.task(task), history.copy())
    # Persist exactly the state a process death leaves between request and receipt.
    runtime.store.execute("UPDATE calls SET status='executing',result=NULL")
    runtime.store.status(task, "running")
    await runtime.close()
    recovered = Runtime(config, Store(tmp_path))
    recovered.tools.catalog[tool.name] = tool
    recovered.store.recover()
    assert recovered.store.task(task)["status"] == ("queued" if read_only else "blocked")
    await recovered.process_calls(recovered.store.task(task), history.copy())
    assert len(effects) == (2 if read_only else 1)
    assert recovered.store.rows("SELECT status FROM calls")[0]["status"] == (
        "succeeded" if read_only else "uncertain"
    )
    await recovered.close()


@pytest.fixture
async def connected(tmp_path, monkeypatch):
    runtime = Runtime(Config(data_dir=tmp_path), Store(tmp_path))
    effects = []

    async def discover(*args, **kwargs):
        return [
            MCPTool(name="send_reply", description="Send exactly the reviewed reply", inputSchema=schema({}))
        ]

    async def call(*args, before_call=None, **kwargs):
        if before_call:
            before_call()
        effects.append(args)
        return {"receipt": "sent"}

    monkeypatch.setattr(connectors, "discover", discover)
    monkeypatch.setattr(connectors, "call", call)
    await runtime.registry.add("mail", {"url": "https://mail.example/mcp"})
    name = next(name for name, tool in runtime.tools.catalog.items() if tool.connector == "mail")
    yield runtime, name, effects
    await runtime.close()


@pytest.mark.parametrize("when", ["before_review", "after_review"])
@pytest.mark.parametrize("change", ["endpoint", "account"])
async def test_prepared_action_is_invalid_after_endpoint_or_account_change(connected, when, change):
    runtime, name, effects = connected
    task, history = prepare(runtime, name)
    assert not await runtime.process_calls(runtime.store.task(task), history)
    call = runtime.store.rows("SELECT * FROM calls")[0]
    if when == "after_review":
        runtime.approvals.decide(call["id"], "approve")
    if change == "endpoint":
        await runtime.registry.add("mail", {"url": "https://different.example/mcp"})
    else:
        runtime.registry.new_revision("mail")
        await runtime.tools.refresh()
    if when == "before_review":
        with pytest.raises(StaleToolBinding, match="changed"):
            runtime.approvals.decide(call["id"], "approve")
    else:
        assert await runtime.process_calls(runtime.store.task(task), history)
        assert runtime.store.rows("SELECT status FROM calls")[0]["status"] == "denied"
    assert effects == []


async def test_connection_change_during_token_refresh_denies_before_external_call(connected):
    runtime, name, effects = connected
    task, history = prepare(runtime, name)
    assert not await runtime.process_calls(runtime.store.task(task), history)
    call = runtime.store.rows("SELECT * FROM calls")[0]
    runtime.approvals.decide(call["id"], "approve")
    started, finish = asyncio.Event(), asyncio.Event()

    async def auth(config):
        started.set()
        await finish.wait()
        return {"Authorization": "Bearer fixture-token"}

    runtime.registry.auth_headers = auth
    execution = asyncio.create_task(runtime.process_calls(runtime.store.task(task), history))
    await asyncio.wait_for(started.wait(), 5)
    runtime.registry.new_revision("mail")
    finish.set()
    assert await execution
    assert effects == []
    assert runtime.store.rows("SELECT status FROM calls")[0]["status"] == "denied"


async def test_old_unbound_approvals_require_a_fresh_request(connected):
    runtime, name, effects = connected
    task, history = prepare(runtime, name)
    assert not await runtime.process_calls(runtime.store.task(task), history)
    call = runtime.store.rows("SELECT * FROM calls")[0]
    runtime.store.execute("DELETE FROM call_bindings")
    with pytest.raises(StaleToolBinding):
        runtime.approvals.decide(call["id"], "approve")
    assert not effects
