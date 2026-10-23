"""User-invoked readiness checks. Results never contain provider responses or credentials."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, replace

import httpx

from .providers import trust_environment


async def running_readiness(config, *, check_model=False, transport=None):
    """Ask the actual service: launchd and the diagnostic terminal can have different TCC grants."""
    from urllib.parse import quote

    async with httpx.AsyncClient(
        base_url=f"http://127.0.0.1:{config.port}",
        headers={"Authorization": "Bearer " + config.token()},
        trust_env=False,
        timeout=50,
        transport=transport,
    ) as client:
        try:
            response = await client.get("/api/product")
        except httpx.HTTPError:
            return None
        if response.status_code != 200:
            return {
                "ready": False,
                "service_running": True,
                "error": "Could not authenticate to the local service. Check the configuration and port.",
            }
        try:
            if check_model:
                probe = await client.post(
                    "/api/models/" + quote(config.default_provider, safe="") + "/test", json={}
                )
                probe.raise_for_status()
                response = await client.get("/api/product")
            response.raise_for_status()
            return response.json()["readiness"] | {"service_running": True}
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return {
                "ready": False,
                "service_running": True,
                "error": "The local service did not complete its readiness check. Check its private logs and model connection.",
            }


def fingerprint(config):
    return hashlib.sha256(json.dumps(asdict(config), sort_keys=True).encode()).hexdigest()


def readiness(runtime):
    name = runtime.config.default_provider
    config = runtime.config.providers[name]
    checked = runtime.store.preference("provider_checks", {}).get(name, {})
    model_ready = bool(
        checked.get("ok") and checked.get("tools") and checked.get("fingerprint") == fingerprint(config)
    )
    bot = runtime.telegram.settings()
    return {
        "ready": bool(model_ready and bot.get("paired")),
        "model": {
            "name": name,
            "configured": bool(config.model),
            "tested": model_ready,
            "checked": checked.get("checked"),
            "error": checked.get("error", ""),
        },
        "telegram": {"paired": bool(bot.get("paired")), "connected": bool(bot.get("connected"))},
        "mac": runtime.mac.health(),
        "computer": {"configured": bool(runtime.config.computer_url)},
        "kev": dict(runtime.attention.health),
    }


async def model_probe(runtime, name):
    config = runtime.config.providers[name]
    result = {"checked": time.time(), "ok": False, "tools": False, "fingerprint": fingerprint(config)}
    probe = {
        "type": "function",
        "function": {
            "name": "openduet_connection_probe",
            "description": "Read-only connection check. Returns connected and has no external effects.",
            "parameters": {
                "type": "object",
                "properties": {"value": {"type": "string", "enum": ["connected"]}},
                "required": ["value"],
                "additionalProperties": False,
            },
        },
    }
    try:
        async with asyncio.timeout(45):
            reply = await runtime.provider_factory(replace(config, max_tokens=128)).complete(
                [
                    {
                        "role": "system",
                        "content": "You are testing a connection. Do not explain. Call the provided read-only openduet_connection_probe tool with value connected.",
                    },
                    {"role": "user", "content": "Call openduet_connection_probe now, with value connected."},
                ],
                [probe],
            )
        result["ok"] = True
        calls = reply.message.get("tool_calls") or []
        result["tools"] = (
            len(calls) == 1
            and calls[0]["function"]["name"] == "openduet_connection_probe"
            and json.loads(calls[0]["function"]["arguments"]) == {"value": "connected"}
        )
        if not result["tools"]:
            result["error"] = (
                "The model answered but did not produce a valid tool call. Try a tool-capable model or turn off native tool calling."
            )
    except TimeoutError:
        result["error"] = (
            "The model did not answer within 45 seconds. Check the server and whether the model is loaded."
        )
    except Exception:
        result["error"] = (
            "Model connection failed. Check the URL, model id, credentials and selected protocol."
        )
    checks = runtime.store.preference("provider_checks", {})
    checks[name] = result
    runtime.store.set_preference("provider_checks", checks)
    return result


async def available_models(config, *, transport=None):
    # Operators choose the endpoint. Local model traffic must stay local even
    # when an environment has a corporate/public outbound proxy configured.
    endpoint = "/api/tags" if config.kind == "ollama" else "/models"
    headers = {}
    if config.api_key_env:
        import os

        key = os.environ.get(config.api_key_env, "")
        headers = {"Authorization": "Bearer " + key} if key else {}
        if config.kind == "anthropic":
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
    async with httpx.AsyncClient(
        timeout=10, transport=transport, trust_env=trust_environment(config.base_url)
    ) as client:
        response = await client.get(config.base_url.rstrip("/") + endpoint, headers=headers)
        if response.is_error:
            raise ValueError("Model listing is unavailable. Enter the model id supplied by your server.")
        if len(response.content) > 2_000_000:
            raise ValueError("Model list is too large")
        data = response.json()
    items = data.get("models", []) if config.kind == "ollama" else data.get("data", [])
    return sorted(
        {
            str(item.get("name") or item.get("id"))[:200]
            for item in items[:300]
            if isinstance(item, dict) and (item.get("id") or item.get("name"))
        }
    )
