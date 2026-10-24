"""Actual HTTP MCP read acceptance and refusal of consequential live probes."""

import json
import subprocess
import sys

import httpx
import pytest

from openduet.config import Config
from openduet.connector_checks import check, run_plan
from openduet.runtime import Runtime
from openduet.store import Store
from tests.fixtures.mcp_process import loopback_server


async def test_actual_http_provider_contract_reports_shape_without_records(tmp_path):
    runtime = Runtime(Config(data_dir=tmp_path), Store(tmp_path))
    try:
        with loopback_server() as origin:
            await runtime.registry.add("gmail", {"url": origin + "/mcp"})
            spec = {
                "tool": "read_events",
                "arguments": {"service": "gmail"},
                "record_path": ["messages"],
                "required_fields": ["id", "threadId", "payload"],
            }
            result = await check(runtime, "gmail", spec)
            assert result["passed"] and result["record_count"] == 1
            assert len(result["tool_schema_sha256"]) == 64
            assert "client@example.test" not in json.dumps(result)
            assert "Please review" not in json.dumps(result)
            assert not runtime.store.rows("SELECT * FROM tasks")
            with pytest.raises(ValueError, match="contract"):
                await check(runtime, "gmail", spec | {"required_fields": ["missing-required-field"]})
            with pytest.raises(ValueError, match="read-only"):
                await check(runtime, "gmail", {"tool": "delayed", "arguments": {}})
            await runtime.registry.disconnect("gmail")
            with pytest.raises(ValueError, match="read-only"):
                await check(runtime, "gmail", spec)
    finally:
        await runtime.close()


async def test_live_plan_posts_only_named_checks_and_suppresses_error_bodies(monkeypatch):
    original = httpx.AsyncClient
    seen = []

    def transport(request):
        seen.append(request)
        assert request.headers["Authorization"] == "Bearer private-test-token"
        if request.url.path.endswith("gmail/check"):
            return httpx.Response(
                200,
                json={
                    "passed": True,
                    "record_count": 2,
                    "provider_records": [{"private_email": "Private provider content must never be saved"}],
                },
            )
        return httpx.Response(400, json={"detail": "Private provider content must never be saved"})

    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(transport), **kwargs)
    )
    report = await run_plan(
        "https://workspace.example",
        "private-test-token",
        {
            "services": [
                {"connector": "gmail", "tool": "read_events"},
                {"connector": "stripe", "tool": "read_invoices"},
            ]
        },
    )
    assert not report["passed"] and len(report["checks"]) == 2
    assert [request.url.path for request in seen] == [
        "/api/connectors/gmail/check",
        "/api/connectors/stripe/check",
    ]
    assert "Private provider" not in json.dumps(report) and "private-test-token" not in json.dumps(report)


def test_live_probe_requires_explicit_flag_before_reading_plan_or_credentials(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "openduet.connector_checks",
            "--plan",
            str(tmp_path / "nonexistent-plan.json"),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "No accounts contacted" in result.stderr
