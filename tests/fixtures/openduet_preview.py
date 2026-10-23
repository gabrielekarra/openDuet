"""Disposable UI fixture. No real model, user data or external accounts are used."""

import asyncio
import json
import os
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

import httpx
from fastapi import Request

from openduet.config import Config
from openduet.providers import Reply
from openduet.server import create_app


class PreviewProvider:
    def __init__(self, config):
        pass

    async def complete(self, messages, tools):
        if messages[-1]["role"] == "tool":
            return Reply(
                {"role": "assistant", "content": "The preview draft is ready. Review it in Make."}, 30, 20
            )
        request = messages[-1].get("content", "")
        if os.environ.get("OPENDUET_PREVIEW_PAUSE_ONCE") and "restart acceptance" in request:
            barrier = config.data_dir / ".restart-barrier"
            if not barrier.exists():
                barrier.write_text(
                    "Model request waiting; the process-restart check will terminate this child"
                )
                await asyncio.Event().wait()
        if "remember" in request.lower():
            name, args = "remember", {"content": "I prefer morning meetings. UI test fixture."}
        else:
            name, args = (
                "create_artifact",
                {
                    "title": "A little space for the week",
                    "format": "md",
                    "content": "# Weekly brief\n\nA synthetic draft from the UI fixture.\n\n- Prepare the meeting brief.\n- Review next steps.\n\nSource: fixture, no connected accounts.",
                },
            )
        return Reply(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "preview-call",
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(args)},
                    }
                ],
            },
            40,
            30,
        )


config = Config(data_dir=Path(os.environ.get("OPENDUET_PREVIEW_DATA", "/tmp/openduet-ui-preview")))
app = create_app(config, provider_factory=PreviewProvider)
runtime = app.state.runtime
static_files = app.router.routes.pop()
deliveries = []


def telegram_transport(request):
    method = request.url.path.rsplit("/", 1)[-1]
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        payload = json.loads(request.content)
    else:
        message = BytesParser(policy=default).parsebytes(
            ("Content-Type: " + content_type + "\r\nMIME-Version: 1.0\r\n\r\n").encode() + request.content
        )
        payload = {}
        for part in message.iter_parts():
            if part.get_filename():
                payload["file"] = True
            else:
                key = part.get_param("name", header="content-disposition")
                value = part.get_payload(decode=True).decode()
                payload[key] = int(value) if key in {"chat_id", "message_thread_id"} else value
    if method != "getUpdates":
        deliveries.append({"method": method, "payload": payload})
    if method == "getMe":
        result = {"id": 123456, "is_bot": True, "username": "openduet_fixture_bot", "first_name": "OpenDuet"}
    elif method == "getUpdates":
        result = []
    else:
        result = {"message_id": len(deliveries), "chat": {"id": payload.get("chat_id", 12)}}
    return httpx.Response(200, json={"ok": True, "result": result})


runtime.telegram.client = httpx.AsyncClient(transport=httpx.MockTransport(telegram_transport))


@app.post("/api/fixture/update")
async def fixture_update(request: Request):
    await runtime.telegram.receive(await request.json())
    return {"ok": True}


@app.get("/api/fixture/deliveries")
async def fixture_deliveries():
    return deliveries


app.router.routes.append(static_files)
