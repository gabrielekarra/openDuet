"""Provider adapters use a single, persisted OpenAI-style conversation format.

No automatic retries: a failed request is visible and consumes no duplicate tool execution.
Endpoints and credential bindings come only from operator configuration.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass

import httpx

from .config import ProviderConfig


@dataclass
class Reply:
    message: dict
    input_tokens: int = 0
    output_tokens: int = 0


class Provider:
    def __init__(self, config: ProviderConfig, transport=None):
        self.config = config
        self.transport = transport

    async def complete(self, messages: list[dict], tools: list[dict]) -> Reply:
        c = self.config
        key = os.environ.get(c.api_key_env, "") if c.api_key_env else ""
        if c.api_key_env and not key:
            raise ValueError(f"Missing credential binding: {c.api_key_env}")
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        messages = [dict(m) for m in messages]
        if not c.tools:
            messages = self._text_messages(messages)
            messages[0]["content"] += (
                '\nTool calling protocol: return ONLY {"tool_calls":[{"name":"tool_name",'
                '"arguments":{}}]} to request tools, or plain text for your final answer. Tools: '
                + json.dumps(tools)
            )
        payload = {"model": c.model, "messages": messages, "max_tokens": c.max_tokens}
        if tools and c.tools:
            payload["tools"] = tools
        endpoint = "/chat/completions"
        if c.kind == "anthropic":
            endpoint = "/messages"
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
            payload = self._anthropic(messages, tools if c.tools else [])
        elif c.kind == "ollama":
            endpoint = "/api/chat"
            payload.pop("max_tokens")
            payload.update(stream=False, think=c.thinking, options={"num_predict": c.max_tokens})
            history = []
            for original in messages:
                message = dict(original)
                if isinstance(message.get("content"), list):
                    blocks = message["content"]
                    message["content"] = "\n".join(
                        block.get("text", "") for block in blocks if block["type"] == "text"
                    )
                    message["images"] = [
                        block["image_url"]["url"].split(",", 1)[1]
                        for block in blocks
                        if block["type"] == "image_url"
                    ]
                if message["role"] == "tool":
                    message["tool_name"] = message.pop("name", "")
                    message.pop("tool_call_id", None)
                if message.get("tool_calls"):
                    message["tool_calls"] = [
                        {
                            "function": {
                                "name": call["function"]["name"],
                                "arguments": json.loads(call["function"]["arguments"]),
                            }
                        }
                        for call in message["tool_calls"]
                    ]
                history.append(message)
            payload["messages"] = history
        async with httpx.AsyncClient(
            timeout=180,
            transport=self.transport,
            follow_redirects=False,
            trust_env=c.base_url.startswith("https://"),
        ) as client:
            async with client.stream(
                "POST", c.base_url.rstrip("/") + endpoint, json=payload, headers=headers
            ) as response:
                if response.is_error:
                    # Provider responses can echo credentials or private prompts. Do not persist bodies.
                    raise RuntimeError(f"Model provider returned HTTP {response.status_code}")
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > 4_000_000:
                        raise ValueError("Model response exceeds 4 MB")
                body = json.loads(data)
        if c.kind == "anthropic":
            content, calls = [], []
            for block in body["content"]:
                if block["type"] == "text":
                    content.append(block["text"])
                elif block["type"] == "tool_use":
                    calls.append(
                        {
                            "id": block["id"],
                            "type": "function",
                            "function": {"name": block["name"], "arguments": json.dumps(block["input"])},
                        }
                    )
            message = {"role": "assistant", "content": "\n".join(content)}
            if calls:
                message["tool_calls"] = calls
            usage = body.get("usage", {})
            incoming, outgoing = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        elif c.kind == "ollama":
            message = body["message"]
            for call in message.get("tool_calls", []):
                call.setdefault("id", uuid.uuid4().hex)
                call.setdefault("type", "function")
                if isinstance(call["function"]["arguments"], dict):
                    call["function"]["arguments"] = json.dumps(call["function"]["arguments"])
            incoming, outgoing = body.get("prompt_eval_count", 0), body.get("eval_count", 0)
        else:
            message = body["choices"][0]["message"]
            usage = body.get("usage", {})
            incoming, outgoing = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
        message = {k: v for k, v in message.items() if k in {"role", "content", "tool_calls"}}
        message["role"] = "assistant"
        if not c.tools:
            self._parse_text_tools(message)
        # Use a conservative character estimate when servers omit usage accounting.
        return Reply(
            message,
            incoming or max(1, len(json.dumps(messages)) // 3),
            outgoing or max(1, len(json.dumps(message)) // 3),
        )

    @staticmethod
    def _text_messages(messages):
        result = []
        for msg in messages:
            role = msg["role"]
            content = msg.get("content") or ""
            if msg.get("tool_calls"):
                content += "\nTool requests: " + json.dumps(msg["tool_calls"])
            if role == "tool":
                role, content = "user", "UNTRUSTED TOOL RESULT: " + content
            result.append({"role": role, "content": content})
        return result

    @staticmethod
    def _parse_text_tools(message):
        text = (message.get("content") or "").strip()
        if text.startswith("```json") and text.endswith("```"):
            text = text[7:-3].strip()
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            return
        if not isinstance(parsed, dict) or not isinstance(parsed.get("tool_calls"), list):
            return
        message["tool_calls"] = [
            {
                "id": uuid.uuid4().hex,
                "type": "function",
                "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])},
            }
            for c in parsed["tool_calls"]
        ]
        message["content"] = ""

    def _anthropic(self, messages, tools):
        history = []
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        for m in messages:
            if m["role"] == "system":
                continue
            if m["role"] == "tool":
                role = "user"
                blocks = [{"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}]
            else:
                role = m["role"]
                if isinstance(m.get("content"), list):
                    blocks = []
                    for block in m["content"]:
                        if block["type"] == "text":
                            blocks.append(block)
                        elif block["type"] == "image_url":
                            prefix, data = block["image_url"]["url"].split(",", 1)
                            blocks.append(
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": prefix[5:].split(";")[0],
                                        "data": data,
                                    },
                                }
                            )
                else:
                    blocks = [{"type": "text", "text": m["content"]}] if m.get("content") else []
                for call in m.get("tool_calls", []):
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": call["id"],
                            "name": call["function"]["name"],
                            "input": json.loads(call["function"]["arguments"]),
                        }
                    )
            if history and history[-1]["role"] == role:
                history[-1]["content"].extend(blocks)
            else:
                history.append({"role": role, "content": blocks})
        result = {
            "model": self.config.model,
            "system": system,
            "messages": history,
            "max_tokens": self.config.max_tokens,
        }
        if tools:
            result["tools"] = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"]["description"],
                    "input_schema": t["function"]["parameters"],
                }
                for t in tools
            ]
        return result
