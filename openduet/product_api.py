"""Console endpoints; the application's auth middleware protects every route except signed callbacks."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from dataclasses import asdict
from pathlib import Path

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from . import catalog
from .approvals import preview
from .attachments import ingest
from .config import ProviderConfig
from .diagnostics import readiness


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
            "directory": catalog.directory()
            + [
                dict(item, capability=item["description"], setup_url="", scopes=[])
                for item in runtime.plugins.connections()
            ],
            "recipes": catalog.RECIPES,
            "plugins": runtime.plugins.listing(),
            "skills": runtime.plugins.descriptions(),
            "suggestions": store.rows(
                "SELECT task,content FROM events WHERE kind='suggest_connector' ORDER BY id DESC LIMIT 100"
            ),
            "mac": runtime.mac.health(),
            "readiness": readiness(runtime),
            "mail_accounts": runtime.mail.listing(),
            "wallet": runtime.wallet.settings(),
            "purchases": store.rows(
                "SELECT id,task,merchant,amount,currency,expires,status,created FROM purchases ORDER BY created DESC LIMIT 100"
            ),
            "approvals": [
                preview(call, runtime.tools.catalog.get(call["name"]))
                for call in store.rows(
                    "SELECT * FROM calls WHERE status IN ('pending','deferred','uncertain')"
                )
            ],
            "sources": store.rows(
                "SELECT id,task,tool,url,substr(excerpt,1,1000) AS excerpt FROM sources ORDER BY rowid DESC LIMIT 100"
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

    @app.post("/api/telegram/outbox/{ident}/resolve")
    async def telegram_receipt(ident: str, request: Request):
        body = await request.json()
        if body.get("verified") is not True or body.get("action") not in {"sent", "retry"}:
            raise ValueError("Verify delivery in Telegram before resolving an uncertain receipt")
        status = "sent" if body["action"] == "sent" else "pending"
        if not store.execute(
            "UPDATE telegram_outbox SET status=?,retry_at=0 WHERE id=? AND status='uncertain'",
            (status, ident),
        ):
            raise ValueError("Receipt already reviewed")
        return {"ok": True}

    @app.post("/api/telegram/session")
    async def miniapp_session(request: Request):
        body = await request.json()
        runtime.telegram.validate_init_data(str(body.get("init_data", ""))[:10000])
        owner = runtime.telegram.settings()
        expiry = (
            str(int(time.time() + 1800))
            + ":tg:"
            + str(owner["owner_id"])
            + ":"
            + owner.get("session_nonce", "")
        )
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

    @app.post("/api/initiatives/{ident}")
    async def review_initiative(ident: str, request: Request):
        body = await request.json()
        runtime.attention.review_initiative(ident, body.get("action"), body.get("hours", 1))
        return {"ok": True}

    @app.get("/api/kev")
    async def kev_health():
        if not runtime.config.kev_url:
            return {"ready": False, "message": "Configure the separate Kev service to enable local inference"}
        try:
            async with httpx.AsyncClient(
                timeout=5, trust_env=runtime.config.kev_url.startswith("https://")
            ) as client:
                response = await client.get(runtime.config.kev_url.rstrip("/") + "/health")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError:
            return {"ready": False, "message": "Kev unavailable: brief-only mode"}

    @app.post("/api/kev/download", status_code=202)
    async def kev_download():
        if not runtime.config.kev_url:
            raise HTTPException(409, "Configure the Kev service first")
        async with httpx.AsyncClient(
            timeout=10, trust_env=runtime.config.kev_url.startswith("https://")
        ) as client:
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
        await runtime.registry.finish_oauth(state, code)
        return RedirectResponse("/?view=connections", status_code=303)

    @app.post("/api/recipes/{name}", status_code=202)
    async def recipe(name: str):
        if name not in catalog.RECIPES:
            raise HTTPException(404, "Recipe not found")
        task = store.new_task("main", catalog.RECIPES[name]["prompt"], runtime.config.default_provider)
        owner = runtime.telegram.settings()
        if owner.get("paired"):
            store.execute(
                "INSERT INTO task_surfaces VALUES(?,'telegram',?,NULL,NULL,NULL)", (task, owner["owner_chat"])
            )
        return {"task": task}

    @app.get("/api/vault/audit")
    async def secret_audit():
        return store.rows("SELECT * FROM secret_audit ORDER BY created DESC LIMIT 200")

    @app.post("/api/vault/rotate")
    async def rotate():
        from cryptography.fernet import Fernet

        runtime.vault.rotate(Fernet.generate_key())
        return {"ok": True}

    @app.get("/api/connectors/{name}/tools")
    async def connector_tools(name: str):
        if name not in runtime.config.connectors:
            raise HTTPException(404, "Connection not found")
        return runtime.redact_data(
            {
                "tools": [
                    {
                        "name": tool.remote_name,
                        "description": tool.description,
                        "read_only": tool.risk == "read",
                        "parameters": tool.parameters,
                    }
                    for tool in runtime.tools.catalog.values()
                    if tool.connector == name
                ]
            }
        )

    @app.post("/api/mail-accounts")
    async def add_mail(request: Request):
        return await runtime.mail.add(await request.json())

    @app.delete("/api/mail-accounts/{name}")
    async def disconnect_mail(name: str):
        await runtime.mail.disconnect(name)
        return {"ok": True}

    @app.post("/api/models")
    async def model(request: Request):
        body = await request.json()
        name = str(body.pop("name", ""))
        if not name or not name.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Invalid model name")
        key = body.pop("api_key", "")
        clear_key = body.pop("clear_api_key", False)
        make_default = body.pop("default", False)
        config = ProviderConfig(**body)
        if key:
            environment_name = "OPENDUET_PROVIDER_" + hashlib.sha256(name.encode()).hexdigest()[:24].upper()
            runtime.vault.put("provider:" + name, key)
            os.environ[environment_name] = key
            config.api_key_env = environment_name
        elif not clear_key and name in runtime.config.providers:
            config.api_key_env = runtime.config.providers[name].api_key_env
        if clear_key:
            runtime.vault.remove("provider:" + name)
            config.api_key_env = ""
        runtime.config.providers[name] = config
        checks = store.preference("provider_checks", {})
        checks.pop(name, None)
        store.set_preference("provider_checks", checks)
        store.set_preference(
            "model_configs", {key: asdict(value) for key, value in runtime.config.providers.items()}
        )
        if make_default:
            runtime.config.default_provider = name
            store.set_preference("default_provider", name)
        return {"model": name}

    @app.post("/api/models/{name}/test")
    async def test_model(name: str):
        from .diagnostics import model_probe

        return await model_probe(runtime, name)

    @app.get("/api/models/{name}/available")
    async def list_models(name: str):
        from .diagnostics import available_models

        try:
            return {"models": await available_models(runtime.config.providers[name])}
        except (httpx.HTTPError, ValueError):
            raise HTTPException(
                400,
                "Could not list models. Check the server URL and credentials, or enter its model id manually.",
            ) from None

    @app.post("/api/voice")
    async def voice(request: Request):
        body = await request.json()
        path = str(body.get("model", ""))
        if path and not Path(path).expanduser().is_dir():
            raise ValueError("Select an already downloaded local faster-whisper model directory")
        runtime.config.voice_model = str(Path(path).expanduser().resolve()) if path else ""
        store.set_preference("voice_model", runtime.config.voice_model)
        return {"enabled": bool(path)}

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
                        "SELECT (SELECT COUNT(*) FROM events) AS events,(SELECT MAX(updated) FROM tasks) AS tasks,(SELECT COUNT(*) FROM decisions) AS decisions,(SELECT MAX(rowid) FROM preferences) AS preferences"
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
