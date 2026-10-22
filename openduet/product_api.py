"""Console endpoints; the application's auth middleware protects every route except signed callbacks."""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import asdict

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from . import catalog
from .approvals import preview
from .attachments import ingest
from .config import ProviderConfig


class BotToken(BaseModel):
    token: str = Field(min_length=15, max_length=256)


class MacSetting(BaseModel):
    enabled: bool


class Review(BaseModel):
    action: str
    edited: dict | None = None


def install(app, runtime, signature):
    store = runtime.store

    @app.get("/api/product")
    async def product():
        return {
            "telegram": runtime.telegram.public(),
            "proactivity": runtime.attention.snapshot(),
            "directory": catalog.directory(),
            "recipes": catalog.RECIPES,
            "plugins": runtime.plugins.listing(),
            "skills": runtime.plugins.descriptions(),
            "mac": {"enabled": runtime.mac.enabled, "platform": os.sys.platform},
            "approvals": [
                preview(call)
                for call in store.rows(
                    "SELECT * FROM calls WHERE status IN ('pending','deferred','uncertain')"
                )
            ],
            "sources": store.rows(
                "SELECT id,task,tool,url,excerpt FROM sources ORDER BY rowid DESC LIMIT 100"
            ),
            "custom_checkins": store.rows("SELECT * FROM schedules"),
            "connector_polling": store.rows("SELECT * FROM connector_cursors"),
        }

    @app.post("/api/telegram/token")
    async def token(body: BotToken):
        return await runtime.telegram.connect(body.token)

    @app.post("/api/telegram/pair")
    async def pair():
        return runtime.telegram.pair()

    @app.post("/api/telegram/test")
    async def test():
        return {"queued": runtime.telegram.owner_message("OpenDuet connected. / OpenDuet connesso.")}

    @app.delete("/api/telegram")
    async def disconnect():
        await runtime.telegram.disconnect()
        return {"ok": True}

    @app.post("/api/telegram/session")
    async def miniapp_session(request: Request):
        body = await request.json()
        runtime.telegram.validate_init_data(str(body.get("init_data", ""))[:10000])
        expiry = str(int(time.time() + 1800))
        response = JSONResponse({"ok": True})
        response.set_cookie(
            "openduet",
            expiry + "." + signature(expiry),
            httponly=True,
            samesite="none",
            secure=True,
            max_age=1800,
        )
        return response

    @app.post("/api/reviews/{ident}")
    async def review(ident: str, body: Review):
        try:
            return runtime.approvals.decide(ident, body.action, body.edited)
        except ValueError as error:
            raise HTTPException(409, str(error)) from None

    @app.post("/api/mac")
    async def mac(body: MacSetting):
        if body.enabled and os.sys.platform != "darwin":
            raise HTTPException(409, "Run OpenDuet on the Mac you want the agent to control")
        store.set_preference("mac_enabled", body.enabled)
        runtime.mac.elements.clear()
        return {"enabled": runtime.mac.enabled}

    @app.post("/api/proactivity")
    async def attention(request: Request):
        return runtime.attention.configure(await request.json())

    @app.post("/api/proactivity/brief")
    async def brief():
        return {"task": await runtime.attention.brief(force=True)}

    @app.post("/api/proactivity/feedback/{ident}")
    async def feedback(ident: str, request: Request):
        body = await request.json()
        runtime.attention.feedback(ident, body.get("action"))
        return {"ok": True}

    @app.post("/api/proactivity/forget")
    async def forget(request: Request):
        body = await request.json()
        runtime.attention.forget(body.get("kind"), body.get("rule"))
        return {"ok": True}

    @app.get("/api/kev")
    async def kev_health():
        if not runtime.config.kev_url:
            return {"ready": False, "message": "Configure the separate Kev service to enable local inference"}
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(runtime.config.kev_url.rstrip("/") + "/health")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError:
            return {"ready": False, "message": "Kev unavailable: brief-only mode"}

    @app.post("/api/kev/download", status_code=202)
    async def kev_download():
        if not runtime.config.kev_url:
            raise HTTPException(409, "Configure the Kev service first")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(runtime.config.kev_url.rstrip("/") + "/model/download")
            if response.is_error:
                raise HTTPException(409, "Download unavailable or already in progress")
            return response.json()

    @app.post("/api/connectors")
    async def add_connector(request: Request):
        body = await request.json()
        return await runtime.registry.add(str(body.pop("name", "")), body)

    @app.delete("/api/connectors/{name}")
    async def remove_connector(name: str):
        await runtime.registry.disconnect(name)
        return {"ok": True}

    @app.post("/api/connectors/{name}/oauth")
    async def oauth(name: str, request: Request):
        body = await request.json()
        redirect_uri = str(request.base_url).rstrip("/") + "/api/connectors/oauth/callback"
        return await runtime.registry.begin_oauth(
            name, redirect_uri, body.get("client_id", ""), body.get("scope", "")
        )

    @app.get("/api/connectors/oauth/callback")
    async def oauth_callback(state: str, code: str):
        return await runtime.registry.finish_oauth(state, code)

    @app.post("/api/recipes/{name}", status_code=202)
    async def recipe(name: str):
        if name not in catalog.RECIPES:
            raise HTTPException(404, "Recipe not found")
        return {
            "task": store.new_task("main", catalog.RECIPES[name]["prompt"], runtime.config.default_provider)
        }

    @app.get("/api/vault/audit")
    async def secret_audit():
        return store.rows("SELECT * FROM secret_audit ORDER BY created DESC LIMIT 200")

    @app.post("/api/vault/rotate")
    async def rotate():
        from cryptography.fernet import Fernet

        runtime.vault.rotate(Fernet.generate_key())
        return {"ok": True}

    @app.post("/api/models")
    async def model(request: Request):
        body = await request.json()
        name = str(body.pop("name", ""))
        if not name or not name.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Invalid model name")
        key = body.pop("api_key", "")
        make_default = body.pop("default", False)
        config = ProviderConfig(**body)
        if key:
            environment_name = "OPENDUET_PROVIDER_" + name.upper().replace("-", "_")
            runtime.vault.put("provider:" + name, key)
            os.environ[environment_name] = key
            config.api_key_env = environment_name
        runtime.config.providers[name] = config
        store.set_preference(
            "model_configs", {key: asdict(value) for key, value in runtime.config.providers.items()}
        )
        if make_default:
            runtime.config.default_provider = name
            store.set_preference("default_provider", name)
        return {"model": name}

    async def bounded(request, limit):
        content = bytearray()
        async for chunk in request.stream():
            content.extend(chunk)
            if len(content) > limit:
                raise HTTPException(413, "Upload exceeds limit")
        return bytes(content)

    @app.post("/api/attachments", status_code=201)
    async def attachment(request: Request, name: str = "upload.txt"):
        return await ingest(runtime, await bounded(request, 20_000_000), name)

    @app.post("/api/plugins/preview")
    async def inspect_plugin(request: Request):
        return runtime.plugins.inspect(await bounded(request, 10_000_000))

    @app.post("/api/plugins/install", status_code=201)
    async def install_plugin(request: Request):
        return runtime.plugins.install(await bounded(request, 10_000_000))

    @app.delete("/api/plugins/{name}")
    async def remove_plugin(name: str):
        runtime.plugins.uninstall(name)
        return {"ok": True}

    @app.get("/api/stream")
    async def stream(request: Request):
        async def updates():
            last = ""
            while not await request.is_disconnected() and not runtime.stop.is_set():
                # Events are invalidations; private content stays behind authenticated JSON endpoints.
                marker = json.dumps(
                    store.rows(
                        "SELECT (SELECT COUNT(*) FROM events) AS events,(SELECT MAX(updated) FROM tasks) AS tasks,(SELECT COUNT(*) FROM decisions) AS decisions"
                    )
                )
                if marker != last:
                    yield "event: change\ndata: {}\n\n"
                    last = marker
                else:
                    yield ": keepalive\n\n"
                await asyncio.sleep(2)

        return StreamingResponse(
            updates(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"}
        )
