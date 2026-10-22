"""Dedicated browser service. No workspace DB, provider keys or connector tokens are mounted here."""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import os
import socket
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


def public_url(value, *, resolve_names=True):
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 80, 443}
    ):
        raise ValueError("Only public HTTP(S) websites on standard ports are supported")
    blocked = {
        host.strip().lower()
        for host in os.environ.get("OPENDUET_COMPUTER_DENY_HOSTS", "").split(",")
        if host.strip()
    }
    if any(parsed.hostname == host or parsed.hostname.endswith("." + host) for host in blocked):
        raise ValueError("This site is denied by the operator")
    # In the internal Docker network only the proxy has external DNS/egress.
    # It validates every answer and pins the connection IP, preventing rebinding.
    if not resolve_names:
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            address = None
        if parsed.hostname == "localhost" or (address and not address.is_global):
            raise ValueError("Private destination denied")
        return value
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
        raise ValueError("Private, local and metadata destinations are not accessible from the computer")
    return value


class Operation(BaseModel):
    action: str
    url: str = Field(default="", max_length=3000)
    selector: str = Field(default="", max_length=2000)
    text: str = Field(default="", max_length=32000)
    filename: str = Field(default="", max_length=200)
    content: str = Field(default="", max_length=28_000_000)


class PrivateLogin(BaseModel):
    expected_url: str = Field(max_length=3000)
    fields: dict[str, str]


class Computer:
    def __init__(self, directory=None):
        self.directory = Path(directory or os.environ.get("OPENDUET_COMPUTER_DATA", "/computer"))
        self.context = self.page = self.playwright = None
        self.lock = asyncio.Lock()
        self.private_selectors = set()
        self.effects_allowed = False

    async def start(self):
        if self.context:
            return
        from playwright.async_api import async_playwright

        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.playwright = await async_playwright().start()
        proxy = os.environ.get("OPENDUET_EGRESS_PROXY", "")
        if not proxy and not os.environ.get("OPENDUET_COMPUTER_FIXTURE"):
            raise ValueError("The isolated computer requires its enforcing egress proxy")
        self.context = await self.playwright.chromium.launch_persistent_context(
            str(self.directory / "profile"),
            headless=True,
            accept_downloads=True,
            service_workers="block",
            proxy={"server": proxy} if proxy else None,
            executable_path=os.environ.get("CHROMIUM_PATH"),
            args=["--disable-dev-shm-usage"],
        )

        async def route(request):
            try:
                await asyncio.to_thread(public_url, request.request.url, resolve_names=not bool(proxy))
                if request.request.method not in {"GET", "HEAD", "OPTIONS"} and not self.effects_allowed:
                    raise ValueError("Unapproved state-changing browser request")
            except (ValueError, OSError):
                await request.abort()
            else:
                await request.continue_()

        await self.context.route("**/*", route)
        await self.context.route_web_socket("**/*", lambda websocket: websocket.close())
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.page.set_default_timeout(15000)

    async def state(self):
        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "text": (await self.page.locator("body").inner_text())[:24000],
        }

    async def run(self, operation):
        async with self.lock:
            try:
                self.effects_allowed = operation.action in {"click", "fill", "upload", "download"}
                return await self.perform(operation)
            finally:
                self.effects_allowed = False

    async def perform(self, operation):
        await self.start()
        action = operation.action
        if action == "open":
            await asyncio.to_thread(
                public_url, operation.url, resolve_names=not bool(os.environ.get("OPENDUET_EGRESS_PROXY"))
            )
            await self.page.goto(operation.url, wait_until="domcontentloaded", timeout=30000)
            self.private_selectors.clear()
        elif action == "click":
            await self.page.locator(operation.selector).click()
        elif action == "fill":
            element = self.page.locator(operation.selector)
            if (
                await element.get_attribute("type") == "password"
                or operation.selector in self.private_selectors
            ):
                raise ValueError("Use private sign-in for credentials")
            await element.fill(operation.text)
        elif action == "screenshot":
            # Secret inputs are visually hidden as well as excluded from text observations.
            await self.page.locator("input,textarea").evaluate_all(
                "nodes => nodes.forEach(n => n.style.visibility = 'hidden')"
            )
            try:
                data = await self.page.screenshot(type="png", full_page=False)
            finally:
                await self.page.locator("input,textarea").evaluate_all(
                    "nodes => nodes.forEach(n => n.style.visibility = '')"
                )
            return {"mime": "image/png", "name": "browser.png", "content": base64.b64encode(data).decode()}
        elif action == "download":
            async with self.page.expect_download() as download:
                await self.page.locator(operation.selector).click()
            received = await download.value
            path = await received.path()
            if not path or Path(path).stat().st_size > 20_000_000:
                raise ValueError("Download exceeds the 20 MB bridge limit")
            return {
                "name": Path(received.suggested_filename).name,
                "content": base64.b64encode(Path(path).read_bytes()).decode(),
            }
        elif action == "upload":
            content = base64.b64decode(operation.content, validate=True)
            if len(content) > 20_000_000:
                raise ValueError("Upload exceeds limit")
            await self.page.locator(operation.selector).set_input_files(
                {
                    "name": Path(operation.filename).name,
                    "mimeType": "application/octet-stream",
                    "buffer": content,
                }
            )
        elif action != "read":
            raise ValueError("Unknown computer operation")
        return await self.state()

    async def login(self, body):
        async with self.lock:
            await self.start()
            if self.page.url != body.expected_url:
                raise ValueError("The page changed; refresh before private sign-in")
            for selector, value in body.fields.items():
                await self.page.locator(selector).fill(value)
                self.private_selectors.add(selector)
            return {"filled": True}


def create_service(computer=None):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    browser = computer or Computer()
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app):
        yield
        if browser.context:
            await browser.context.close()
        if browser.playwright:
            await browser.playwright.stop()

    app.router.lifespan_context = lifespan

    def auth(value):
        import hmac

        expected = os.environ.get("OPENDUET_COMPUTER_TOKEN", "")
        if len(expected) < 24 or not hmac.compare_digest(value.removeprefix("Bearer "), expected):
            raise HTTPException(401, "Computer authentication required")

    @app.get("/health")
    async def health():
        return {"ok": True, "isolated": True}

    @app.post("/tools")
    async def tools(body: Operation, authorization: str = Header(default="")):
        auth(authorization)
        try:
            return await browser.run(body)
        except Exception:
            raise HTTPException(
                409, "Browser operation unavailable; refresh the page and inspect the task"
            ) from None

    @app.post("/private/login")
    async def login(body: PrivateLogin, authorization: str = Header(default="")):
        auth(authorization)
        try:
            return await browser.login(body)
        except Exception:
            raise HTTPException(409, "Private login failed or the page changed") from None

    return app


class ComputerClient:
    def __init__(self, runtime):
        self.runtime = runtime
        self.page = None

    async def request(self, path, payload):
        token = os.environ.get("OPENDUET_COMPUTER_TOKEN", "")
        self.runtime.private_values.add(token)
        async with httpx.AsyncClient(
            timeout=45,
            follow_redirects=False,
            trust_env=self.runtime.config.computer_url.startswith("https://"),
        ) as client:
            response = await client.post(
                self.runtime.config.computer_url.rstrip("/") + path,
                json=payload,
                headers={"Authorization": "Bearer " + token},
            )
            if response.is_error:
                raise ValueError("The isolated computer rejected this operation")
            return response.json()

    async def run(self, **arguments):
        if arguments.get("action") == "upload":
            import re

            ident = arguments.pop("file_id", "")
            if not re.fullmatch(r"[0-9a-f]{32}", ident):
                raise ValueError("Choose an existing artifact or attachment id")
            rows = self.runtime.store.rows("SELECT filename FROM artifacts WHERE id=?", (ident,))
            folder = "artifacts"
            if not rows:
                rows = self.runtime.store.rows("SELECT filename FROM attachments WHERE id=?", (ident,))
                folder = "attachments"
            if not rows:
                raise ValueError("Bridge file not found")
            path = self.runtime.config.data_dir / folder / rows[0]["filename"]
            if path.stat().st_size > 20_000_000:
                raise ValueError("Upload exceeds the 20 MB bridge limit")
            arguments.update(filename=path.name, content=base64.b64encode(path.read_bytes()).decode())
        result = await self.request("/tools", arguments)
        if result.get("content"):
            from .attachments import ingest

            return await ingest(
                self.runtime,
                base64.b64decode(result["content"], validate=True),
                result["name"],
                inbound=False,
            )
        if result.get("url"):
            from types import SimpleNamespace

            self.page = SimpleNamespace(url=result["url"])
        return result

    async def login(self, selector, value, expected_url):
        return await self.request(
            "/private/login", {"fields": {selector: value}, "expected_url": expected_url}
        )

    async def close(self):
        pass


def main():
    import uvicorn

    uvicorn.run(
        create_service(),
        host=os.environ.get("OPENDUET_COMPUTER_HOST", "127.0.0.1"),
        port=8769,
        access_log=False,
    )
