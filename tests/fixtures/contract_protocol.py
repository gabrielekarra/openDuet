"""Shared recorded-shape MCP fixture, deliberately independent of vendor tool names."""

import json
from pathlib import Path

SERVICES = json.loads(Path(__file__).with_name("service_contracts.json").read_text())["services"]


def dispatch(service, method, arguments, effect_file=""):
    profile = SERVICES[service]
    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "read_contract",
                    "description": "Read synthetic " + service + " provider-schema records",
                    "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
                    "annotations": {"readOnlyHint": True},
                },
                {
                    "name": "update_contract",
                    "description": "Apply an exact reviewed fixture update",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"record_id": {"type": "string"}, "value": {"type": "string"}},
                        "required": ["record_id", "value"],
                        "additionalProperties": False,
                    },
                    "annotations": {"readOnlyHint": False, "destructiveHint": True},
                },
            ]
        }
    if method == "tools/call":
        name = arguments["name"]
        if name not in {"read_contract", "update_contract"}:
            raise ValueError("Fixture tool is unavailable")
        if effect_file:
            with Path(effect_file).open("a") as output:
                output.write(
                    json.dumps(
                        {"service": service, "tool": name, "arguments": arguments.get("arguments", {})}
                    )
                    + "\n"
                )
        if name == "read_contract":
            data = profile["payload"]
            return (
                {"content": [{"type": "text", "text": json.dumps(data)}]}
                if isinstance(data, list)
                else {"content": [], "structuredContent": data}
            )
        return {"content": [], "structuredContent": {"receipt": "fixture-update-once"}}
    raise ValueError("Unsupported fixture method")
