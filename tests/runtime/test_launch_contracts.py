"""All launch-service record shapes cross the real SDK and host approval boundary."""

import json
import sys
from pathlib import Path

import pytest

from openduet.catalog import SETUP, directory
from openduet.config import Config, ConnectorConfig
from openduet.events import unpack
from openduet.runtime import Runtime
from openduet.store import Store
from tests.fixtures.contract_protocol import SERVICES
from tests.fixtures.mcp_process import loopback_server


def dispatch(name, arguments, ident):
    return [
        {
            "role": "assistant",
            "tool_calls": [{"id": ident, "function": {"name": name, "arguments": json.dumps(arguments)}}],
        }
    ]


@pytest.mark.parametrize("service", list(SERVICES))
async def test_provider_record_contract_through_transport_and_exact_review(tmp_path, service):
    profile = SERVICES[service]
    runtime = Runtime(Config(data_dir=tmp_path), Store(tmp_path))
    effects = tmp_path / "effects.jsonl"
    try:
        with loopback_server(effects) as origin:
            if profile["transport"] == "stdio":
                runtime.config.connectors[service] = ConnectorConfig(
                    command=sys.executable,
                    args=[
                        str(Path(__file__).parents[1] / "fixtures" / "mcp_http_server.py"),
                        "--stdio-profile",
                        service,
                        str(effects),
                    ],
                )
                await runtime.tools.refresh()
            else:
                await runtime.registry.add(
                    service,
                    {
                        "url": origin + "/profiles/" + service,
                        "require_approval": profile["require_approval"],
                        "exclusive": profile["exclusive"],
                    },
                )
            reader = next(
                tool
                for tool in runtime.tools.catalog.values()
                if tool.connector == service and tool.remote_name == "read_contract"
            )
            writer = next(
                tool
                for tool in runtime.tools.catalog.values()
                if tool.connector == service and tool.remote_name == "update_contract"
            )
            task = runtime.store.new_task(
                "main",
                "Read the requested fixture account, then update record-1 to Reviewed fixture value.",
                "local",
            )
            history = dispatch(reader.name, {}, "read")
            if profile["require_approval"]:
                assert not await runtime.process_calls(runtime.store.task(task), history)
                assert not effects.exists()
                pending = runtime.store.rows("SELECT id FROM calls WHERE status='pending'")[0]
                runtime.approvals.decide(pending["id"], "approve")
            assert await runtime.process_calls(runtime.store.task(task), history)
            output = json.loads(history[-1]["content"])
            assert output["source_id"] and output["sources"]
            records, _ = unpack(output["data"])
            ids = runtime.attention.events.ingest(service, records, profile["kind"])
            assert len(ids) == 1
            assert not runtime.attention.events.ingest(service, records, profile["kind"])
            event = json.loads(runtime.store.rows("SELECT data FROM connector_events")[0]["data"])
            assert event["source"] != service + ":"
            if profile["expected_subject"]:
                assert event["subject"] == profile["expected_subject"]
            payload = {"record_id": "record-1", "value": "Reviewed fixture value"}
            history = dispatch(writer.name, payload, "write")
            assert not await runtime.process_calls(runtime.store.task(task), history)
            assert not any(
                json.loads(line)["tool"] == "update_contract" for line in effects.read_text().splitlines()
            )
            pending = runtime.store.rows("SELECT id,arguments FROM calls WHERE status='pending'")[0]
            assert json.loads(pending["arguments"]) == payload
            runtime.approvals.decide(pending["id"], "approve")
            assert await runtime.process_calls(runtime.store.task(task), history)
            await runtime.process_calls(runtime.store.task(task), dispatch(writer.name, payload, "write"))
            assert (
                sum(
                    json.loads(line)["tool"] == "update_contract" for line in effects.read_text().splitlines()
                )
                == 1
            )
    finally:
        await runtime.close()


def test_directory_and_fixture_coverage_are_the_same_services():
    assert set(SETUP) == set(SERVICES) == {item["id"] for item in directory()}
    assert all(
        item["setup_url"].startswith("https://")
        and item["guide_url"].endswith("#" + item["id"])
        and item["limits"]
        for item in directory()
    )


async def test_exclusive_provider_blocks_other_tools_context_and_rebinding(tmp_path):
    runtime = Runtime(Config(data_dir=tmp_path), Store(tmp_path))
    try:
        with loopback_server() as origin:
            await runtime.registry.add("private-provider", {"url": origin + "/mcp", "exclusive": True})
            assert all(tool.approval for tool in runtime.tools.catalog.values() if tool.connector)
            runtime.store.memory("A prior memory from another account")
            old = runtime.store.new_task("main", "Old private conversation", "local")
            runtime.store.status(old, "ready")
            task = runtime.store.new_task("main", "Read only this provider", "local")
            assert "Old private conversation" not in json.dumps(
                runtime.initial_history(runtime.store.task(task))
            )
            assert "A prior memory" not in json.dumps(runtime.initial_history(runtime.store.task(task)))
            with pytest.raises(ValueError, match="reserved"):
                await runtime.registry.add("other", {"url": origin + "/mcp"})
            with pytest.raises(ValueError, match="rebound"):
                await runtime.registry.add("private-provider", {"url": origin + "/other", "exclusive": True})
            with pytest.raises(ValueError, match="unavailable"):
                runtime.tools.get("search_context", {"query": "prior"})
            assert {
                tool["function"]["name"]
                for tool in runtime.provider_tools()
                if not tool["function"]["name"].startswith("mcp_")
            } <= {"create_artifact", "read_source", "read_attachment", "load_skill"}
            await runtime.registry.disconnect("private-provider")
            with pytest.raises(ValueError, match="reserved"):
                await runtime.registry.add("other", {"url": origin + "/mcp"})
    finally:
        await runtime.close()


def test_gusto_provider_policy_cannot_be_downgraded_by_read_metadata():
    config = ConnectorConfig(url="https://mcp.api.gusto.com", require_approval=False, exclusive=False)
    assert config.require_approval and config.exclusive
    with pytest.raises(ValueError, match="background polling"):
        ConnectorConfig(url="https://mcp.api.gusto.com", poll_tool="read_payroll")


def test_isolated_provider_toml_cannot_mix_accounts_or_reuse_existing_history(tmp_path):
    store = Store(tmp_path)
    store.new_task("main", "Prior work from another account", "local")
    isolated = ConnectorConfig(url="https://mcp.api.gusto.com")
    from openduet.registry import Registry

    class Workspace:
        config = Config(data_dir=tmp_path, connectors={"gusto": isolated})

    workspace = Workspace()
    workspace.store = store
    with pytest.raises(ValueError, match="fresh, dedicated"):
        Registry(workspace)
    assert not store.preference("exclusive_provider", "")
    workspace.config.connectors["other"] = ConnectorConfig(url="https://example.com/mcp")
    with pytest.raises(ValueError, match="fresh, dedicated"):
        Registry(workspace)
