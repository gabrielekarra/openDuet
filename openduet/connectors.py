from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from .config import ConnectorConfig


@asynccontextmanager
async def session(config: ConnectorConfig, private_headers=None):
    if config.command:
        params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env={n: os.environ[n] for n in config.env_names if n in os.environ},
        )
        context = stdio_client(params)
    else:
        headers = {h: os.environ[n] for h, n in config.header_env.items() if n in os.environ}
        if len(headers) != len(config.header_env):
            raise ValueError("A connector credential binding is missing")
        headers.update(private_headers or {})

        def client_factory(headers=None, timeout=None, auth=None):
            return httpx.AsyncClient(headers=headers, timeout=timeout, auth=auth, follow_redirects=False)

        context = streamablehttp_client(
            config.url, headers=headers, timeout=timedelta(seconds=45), httpx_client_factory=client_factory
        )
    async with context as streams:
        async with ClientSession(
            streams[0], streams[1], read_timeout_seconds=timedelta(seconds=45)
        ) as client:
            await client.initialize()
            yield client


async def discover(config, private_headers=None):
    result, cursor = [], None
    async with session(config, private_headers) as client:
        for _ in range(10):
            page = await client.list_tools(cursor=cursor)
            result.extend(t for t in page.tools if t.name not in config.excluded_tools)
            cursor = page.nextCursor
            if not cursor:
                return result[:200]
    raise ValueError("Connector discovery exceeded ten pages")


async def call(config, name, arguments, private_headers=None):
    if name in config.excluded_tools:
        raise ValueError("Tool was excluded")
    # Opening a fresh session is safe; tools/call is made once and never retried on transport errors.
    async with session(config, private_headers) as client:
        result = await client.call_tool(name, arguments)
        return result.model_dump(mode="json", exclude_none=True)
