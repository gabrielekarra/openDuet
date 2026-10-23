"""HTTP SDK discovery, OAuth, provider-shaped ingestion and disconnect boundaries."""

import asyncio
import json
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from openduet import connectors
from openduet.config import Config
from openduet.events import unpack
from openduet.runtime import Runtime
from openduet.store import Store
from tests.fixtures.mcp_process import loopback_server


@pytest.fixture
def runtime(tmp_path):
    return Runtime(Config(data_dir=tmp_path), Store(tmp_path))


async def test_http_oauth_pkce_hot_discovery_and_read(runtime):
    with loopback_server() as origin:
        await runtime.registry.add("fixture", {"url": origin + "/oauth/mcp"})
        assert "fixture" in runtime.tools.errors
        result = await runtime.registry.begin_oauth("fixture", "http://127.0.0.1/callback")
        async with httpx.AsyncClient(trust_env=False) as client:
            response = await client.get(result["url"])
        callback = parse_qs(urlsplit(response.headers["location"]).query)
        await runtime.registry.finish_oauth(callback["state"][0], callback["code"][0])
        assert "fixture" not in runtime.tools.errors
        tool = next(t for t in runtime.tools.catalog.values() if t.remote_name == "echo")
        task = runtime.store.new_task("main", "Read the fixture", "local")
        result = json.loads(await runtime.tools.invoke(tool.name, {"text": "verified HTTP"}, task))
        assert "verified HTTP" in json.dumps(result)
        assert result["source_id"]
        await runtime.registry.disconnect("fixture")
        assert not any(t.connector == "fixture" for t in runtime.tools.catalog.values())
    await runtime.close()


@pytest.mark.parametrize(
    "service,kind",
    [
        ("gmail", "mail.received"),
        ("google-calendar", "calendar.event"),
        ("slack", "chat.message"),
        ("stripe", "invoice.updated"),
    ],
)
async def test_http_service_pages_dedup_edits_and_terminal_cursor(runtime, service, kind):
    with loopback_server() as origin:
        await runtime.registry.add(
            service,
            {
                "url": origin + "/mcp",
                "poll_tool": "read_events",
                "poll_arguments": {"service": service},
                "cursor_argument": "cursor",
                "event_kind": kind,
            },
        )
        for index in range(3):
            runtime.store.execute("UPDATE connector_cursors SET next_poll=0")
            await runtime.attention.poll_connectors()
            cursor = runtime.store.rows("SELECT * FROM connector_cursors")[0]
            assert not cursor["error"]
            if index == 1:
                assert json.loads(cursor["cursor"]) is None
        events = [json.loads(row["data"]) for row in runtime.store.rows("SELECT data FROM connector_events")]
        assert len(events) == 2
        if service == "gmail":
            assert any(event["kind"] == "mail.read" for event in events)
            assert events[0]["text"] == "Please review the proposal"
        if service == "google-calendar":
            assert any(event["kind"] == "calendar.event_changed" for event in events)
        if service == "stripe":
            assert events[0]["payload"]["amount_due"] == 12345
            assert "minor currency" in events[0]["payload"]["amount_unit"]
        assert all(event["source"].startswith(service + ":") for event in events)
    await runtime.close()


async def test_poll_error_keeps_cursor_and_disconnect_during_io_forgets(runtime, monkeypatch):
    with loopback_server() as origin:
        await runtime.registry.add(
            "gmail",
            {
                "url": origin + "/mcp",
                "poll_tool": "read_events",
                "poll_arguments": {"service": "gmail"},
                "cursor_argument": "cursor",
            },
        )
        await runtime.attention.poll_connectors()
        saved = runtime.store.rows("SELECT cursor FROM connector_cursors")[0]["cursor"]
        runtime.config.connectors["gmail"].poll_arguments["force_error"] = True
        # Config metadata changed, so rediscover before the next poll.
        await runtime.tools.refresh()
        runtime.store.execute("UPDATE connector_cursors SET next_poll=0")
        await runtime.attention.poll_connectors()
        row = runtime.store.rows("SELECT * FROM connector_cursors")[0]
        assert row["cursor"] == saved and row["error"]
        started, release = asyncio.Event(), asyncio.Event()

        async def delayed(*args, **kwargs):
            started.set()
            await release.wait()
            raise RuntimeError("Old request failed after disconnect")

        monkeypatch.setattr(connectors, "call", delayed)
        runtime.store.execute("UPDATE connector_cursors SET next_poll=0")
        pending = asyncio.create_task(runtime.attention.poll_connectors())
        await started.wait()
        await runtime.registry.disconnect("gmail")
        release.set()
        await pending
        assert not runtime.store.rows("SELECT * FROM connector_cursors")
        assert not runtime.store.rows("SELECT * FROM connector_events")
    await runtime.close()


def test_graph_nextlink_and_oversize_page_are_explicit():
    assert unpack({"value": [{"id": "m1"}], "@odata.nextLink": "https://graph.microsoft.com/next"})[
        1
    ].endswith("/next")
    with pytest.raises(ValueError, match="200"):
        unpack({"items": [{"id": str(n)} for n in range(201)]})
