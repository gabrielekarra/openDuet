"""Opt-in read-only contract acceptance; reports never contain provider records."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import ssl
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from .providers import trust_environment
from .registry import endpoint


async def check(runtime, connector, spec):
    if not isinstance(spec, dict):
        raise ValueError("A service check must be a JSON object")
    tool = next(
        (
            tool
            for tool in runtime.tools.catalog.values()
            if tool.connector == connector and tool.remote_name == spec.get("tool")
        ),
        None,
    )
    if tool is None or tool.risk != "read" or tool.approval:
        raise ValueError("Live checks require an available, explicitly read-only discovered tool")
    arguments = spec.get("arguments", {})
    runtime.tools.get(tool.name, arguments)
    fingerprint = runtime.tools.fingerprint(tool)
    path = spec.get("record_path", [])
    fields = spec.get("required_fields", [])
    minimum = spec.get("minimum_records", 1)
    if (
        not isinstance(path, list)
        or len(path) > 8
        or any(not isinstance(key, str) or len(key) > 100 for key in path)
        or not isinstance(fields, list)
        or len(fields) > 50
        or any(not isinstance(key, str) for key in fields)
        or not isinstance(minimum, int)
        or not 0 <= minimum <= 200
    ):
        raise ValueError("Use bounded record_path, required_fields and minimum_records")
    result = await tool.run(arguments, "")
    if runtime.tools.fingerprint(runtime.tools.get(tool.name, arguments)) != fingerprint:
        raise ValueError("Connection or tool changed during the contract read")
    if not isinstance(result, dict) or result.get("isError"):
        raise ValueError("The provider reported a read error")
    data = result.get("structuredContent", result)
    if "structuredContent" not in result:
        for block in result.get("content", []):
            if block.get("type") == "text":
                try:
                    data = json.loads(block["text"])
                    break
                except ValueError:
                    pass
    for key in path:
        if not isinstance(data, dict) or key not in data:
            raise ValueError("The configured record path was not returned by the provider")
        data = data[key]
    if not isinstance(data, list):
        data = [data]
    if not minimum <= len(data) <= 200 or any(
        not isinstance(record, dict) or not set(fields) <= record.keys() for record in data
    ):
        raise ValueError("Returned records did not satisfy the configured contract")
    return runtime.redact_data(
        {
            "passed": True,
            "connector": connector,
            "tool": tool.remote_name,
            "observed_at": time.time(),
            "record_count": len(data),
            "required_fields": fields,
            "tool_schema_sha256": hashlib.sha256(
                json.dumps(tool.parameters, sort_keys=True).encode()
            ).hexdigest(),
        }
    )


async def run_plan(url, token, plan):
    endpoint(url)
    entries = plan.get("services", [])
    if not isinstance(entries, list) or not 1 <= len(entries) <= 30:
        raise ValueError("Plan requires 1–30 explicit service checks")
    reports = []
    async with httpx.AsyncClient(
        timeout=90,
        follow_redirects=False,
        trust_env=trust_environment(url),
        verify=ssl.create_default_context(),
        headers={"Authorization": "Bearer " + token},
    ) as client:
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Service checks must be objects")
            connector = entry.get("connector", "")
            if (
                not isinstance(connector, str)
                or not 1 <= len(connector) <= 80
                or any(
                    c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
                    for c in connector
                )
            ):
                raise ValueError("A plan must name valid connector IDs")
            try:
                response = await client.post(
                    url.rstrip("/") + "/api/connectors/" + quote(connector, safe="") + "/check",
                    json={key: value for key, value in entry.items() if key != "connector"},
                )
                if not response.is_success:
                    reports.append(
                        {"connector": connector, "passed": False, "http_status": response.status_code}
                    )
                else:
                    try:
                        data = response.json()
                        if not isinstance(data, dict) or not isinstance(data.get("passed"), bool):
                            raise ValueError("Invalid contract report")
                        reports.append(
                            {
                                key: value
                                for key, value in data.items()
                                if key
                                in {
                                    "passed",
                                    "connector",
                                    "tool",
                                    "observed_at",
                                    "record_count",
                                    "required_fields",
                                    "tool_schema_sha256",
                                }
                            }
                        )
                    except ValueError:
                        reports.append(
                            {
                                "connector": connector,
                                "passed": False,
                                "error": "Workspace returned an invalid contract report",
                            }
                        )
            except httpx.HTTPError:
                reports.append(
                    {
                        "connector": connector,
                        "passed": False,
                        "error": "Workspace unavailable; request was not retried",
                    }
                )
    return {"passed": all(report.get("passed") is True for report in reports), "checks": reports}


def main():
    parser = argparse.ArgumentParser(
        description="Explicitly test selected read-only tools against your connected accounts"
    )
    parser.add_argument("--live", action="store_true", help="Allow the reads explicitly named in the plan")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--token-env", default="OPENDUET_TOKEN")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(".runtime/connector-live-acceptance.json"))
    args = parser.parse_args()
    if not args.live:
        parser.error("No accounts contacted. Add --live to authorize only the plan's read-only checks.")
    token = os.environ.get(args.token_env, "")
    if not token:
        parser.error("Set the selected token environment variable for the running workspace")
    if args.plan.stat().st_size > 100000:
        parser.error("Plan exceeds 100 KB")
    report = asyncio.run(run_plan(args.url, token, json.loads(args.plan.read_text())))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    args.output.chmod(0o600)
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
