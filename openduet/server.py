from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .artifacts import create as create_artifact
from .config import Config
from .runtime import Runtime
from .store import Store, uid


class Message(BaseModel):
    content: str = Field(min_length=1, max_length=32000)
    channel: str = "main"
    provider: str = ""


class Decision(BaseModel):
    approve: bool


class Channel(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class Memory(BaseModel):
    content: str = Field(min_length=1, max_length=16000)


class Schedule(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    prompt: str = Field(min_length=1, max_length=16000)
    channel: str = "main"
    provider: str = ""
    interval: int = Field(default=10800, ge=900, le=31536000)
    next_run: float = Field(default_factory=time.time)


class Settings(BaseModel):
    search_chats: bool = True
    disabled_connectors: list[str] = Field(default_factory=list, max_length=200)
    skills: dict[str, str] = Field(default_factory=dict, max_length=30)


class Login(BaseModel):
    token: str = Field(max_length=4096)


class BrowserLogin(BaseModel):
    selector: str = Field(min_length=1, max_length=1000)
    value: str = Field(min_length=1, max_length=4096)


class Resolution(BaseModel):
    happened: bool
    receipt: str = Field(min_length=1, max_length=4000)


class Artifact(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    format: str
    content: str = Field(max_length=100000)


class Import(BaseModel):
    memories: list[Memory] = Field(default_factory=list, max_length=200)


def create_app(config: Config, *, start_worker=True, provider_factory=None):
    token = config.token()
    store = Store(config.data_dir)
    runtime = Runtime(config, store, **({"provider_factory": provider_factory} if provider_factory else {}))
    login_attempts = {}

    def signature(value):
        return hmac.new(token.encode(), value.encode(), hashlib.sha256).hexdigest()

    def valid_session(value):
        try:
            expiry, sig = value.split(".", 1)
            return int(expiry) > time.time() and hmac.compare_digest(sig, signature(expiry))
        except (ValueError, AttributeError):
            return False

    @asynccontextmanager
    async def lifespan(app):
        worker = asyncio.create_task(runtime.worker()) if start_worker else None
        yield
        await runtime.close()
        if worker:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass

    app = FastAPI(title="OpenDuet", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store, app.state.runtime = store, runtime

    @app.middleware("http")
    async def security(request: Request, call_next):
        if request.url.path.startswith("/api/"):
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc != request.headers.get("host"):
                return JSONResponse({"detail": "Cross-origin access denied"}, status_code=403)
            if request.url.path != "/api/login":
                bearer = request.headers.get("authorization", "").removeprefix("Bearer ")
                if not hmac.compare_digest(bearer, token) and not valid_session(
                    request.cookies.get("openduet")
                ):
                    return JSONResponse({"detail": "Sign in to OpenDuet"}, status_code=401)
        if (
            request.headers.get("content-length", "0").isdigit()
            and int(request.headers.get("content-length", "0")) > 2_000_000
        ):
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        response = await call_next(request)
        for key, value in {
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'",
        }.items():
            response.headers.setdefault(key, value)
        return response

    @app.exception_handler(KeyError)
    async def missing(request, error):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    @app.exception_handler(ValueError)
    async def invalid(request, error):
        return JSONResponse({"detail": str(error)}, status_code=400)

    def channel_exists(channel):
        if not store.rows("SELECT id FROM channels WHERE id=?", (channel,)):
            raise HTTPException(404, "Channel not found")

    def provider_name(value):
        name = value or config.default_provider
        if name not in config.providers:
            raise HTTPException(400, "Unknown provider")
        return name

    @app.post("/api/login")
    async def login(body: Login, request: Request):
        address = request.client.host if request.client else "unknown"
        attempts = [t for t in login_attempts.get(address, []) if t > time.time() - 60]
        if len(attempts) >= 5:
            raise HTTPException(429, "Too many attempts; wait a minute")
        login_attempts[address] = attempts + [time.time()]
        if not hmac.compare_digest(body.token, token):
            raise HTTPException(401, "Incorrect access token")
        expiry = str(int(time.time() + 12 * 3600))
        result = JSONResponse({"ok": True})
        result.set_cookie(
            "openduet",
            expiry + "." + signature(expiry),
            httponly=True,
            samesite="strict",
            secure=request.url.scheme == "https",
            max_age=12 * 3600,
        )
        login_attempts.pop(address, None)
        return result

    @app.post("/api/logout")
    async def logout():
        result = JSONResponse({"ok": True})
        result.delete_cookie("openduet")
        return result

    @app.get("/api/state")
    async def state():
        return {
            "channels": store.rows("SELECT * FROM channels"),
            "tasks": store.rows(
                "SELECT id,channel,request,provider,status,created,updated,error FROM tasks "
                "ORDER BY created DESC LIMIT 100"
            ),
            "approvals": store.rows(
                "SELECT * FROM calls WHERE status IN ('pending','uncertain') ORDER BY created"
            ),
            "artifacts": store.rows("SELECT * FROM artifacts ORDER BY created DESC LIMIT 100"),
            "schedules": store.rows("SELECT * FROM schedules ORDER BY next_run"),
            "memories": store.rows("SELECT * FROM memories ORDER BY created DESC"),
            "providers": {
                n: {"model": p.model, "kind": p.kind, "base_url": p.base_url, "tools": p.tools}
                for n, p in config.providers.items()
            },
            "default_provider": config.default_provider,
            "voice": bool(config.voice_model),
            "connectors": {
                n: {"enabled": runtime.tools.enabled(n), "error": runtime.tools.errors.get(n)}
                for n in config.connectors
            },
            "browser": {
                "enabled": config.browser,
                "hosts": config.browser_hosts,
                "url": runtime.browser.page.url if runtime.browser.page else "",
            },
            "settings": {
                "search_chats": store.preference("search_chats", True),
                "disabled_connectors": store.preference("disabled_connectors", []),
                "skills": store.preference("skills", {}),
            },
            "usage": store.usage(),
            "daily_token_budget": config.daily_token_budget,
        }

    @app.get("/api/messages")
    async def messages(channel: str = "main", before: float = 1e20):
        return list(
            reversed(
                store.rows(
                    "SELECT * FROM messages WHERE channel=? AND created<? ORDER BY created DESC LIMIT 100",
                    (channel, before),
                )
            )
        )

    @app.post("/api/messages", status_code=202)
    async def send(body: Message):
        channel_exists(body.channel)
        return {"task": store.new_task(body.channel, body.content, provider_name(body.provider))}

    @app.get("/api/search")
    async def search(q: str):
        return store.search(q[:1000])

    @app.post("/api/channels", status_code=201)
    async def new_channel(body: Channel):
        ident = uid()
        store.execute("INSERT INTO channels VALUES(?,?)", (ident, body.name))
        return {"id": ident}

    @app.delete("/api/channels/{ident}")
    async def delete_channel(ident: str):
        channel_exists(ident)
        files = store.rows(
            "SELECT filename FROM artifacts WHERE task IN (SELECT id FROM tasks WHERE channel=?)", (ident,)
        )
        store.delete_channel(ident)
        for file in files:
            (config.data_dir / "artifacts" / file["filename"]).unlink(missing_ok=True)
        return {"ok": True}

    @app.post("/api/tasks/{ident}/{action}")
    async def task_action(ident: str, action: str):
        task = store.task(ident)
        if action == "cancel":
            runtime.cancel(ident)
        elif action == "complete" and task["status"] == "ready":
            store.status(ident, "completed")
        elif action == "resume" and task["status"] in {
            "failed",
            "interrupted",
            "blocked",
            "awaiting_approval",
        }:
            if store.rows(
                "SELECT id FROM calls WHERE task=? AND status IN ('pending','executing','uncertain')",
                (ident,),
            ):
                raise HTTPException(409, "Review pending or uncertain actions before resuming")
            store.execute("UPDATE tasks SET turns=0 WHERE id=?", (ident,))
            store.status(ident, "queued")
        else:
            raise HTTPException(409, "Action unavailable for this task state")
        return {"ok": True}

    @app.post("/api/approvals/{ident}")
    async def approval(ident: str, body: Decision):
        found = store.rows("SELECT * FROM calls WHERE id=?", (ident,))
        if not found:
            raise HTTPException(404, "Approval not found")
        call = found[0]
        if call["created"] < time.time() - 86400 and body.approve:
            raise HTTPException(409, "Approval expired; reject it and prepare a fresh action")
        if body.approve:
            try:
                runtime.tools.get(call["name"], json.loads(call["arguments"]))
            except Exception:
                raise HTTPException(409, "Tool unavailable or access revoked") from None
        changed = store.execute(
            "UPDATE calls SET status=? WHERE id=? AND status='pending'",
            ("approved" if body.approve else "denied", ident),
        )
        if not changed:
            raise HTTPException(409, "This action was already reviewed")
        # An action approved while the worker is still running will be noticed on its next pass.
        store.execute(
            "UPDATE tasks SET status='queued' WHERE id=? AND status='awaiting_approval'", (call["task"],)
        )
        return {"ok": True}

    @app.post("/api/calls/{ident}/resolve")
    async def resolve(ident: str, body: Resolution):
        changed = store.execute(
            "UPDATE calls SET status=?,result=? WHERE id=? AND status='uncertain'",
            (
                "succeeded" if body.happened else "denied",
                json.dumps({"user_verified": True, "happened": body.happened, "receipt": body.receipt}),
                ident,
            ),
        )
        if not changed:
            raise HTTPException(409, "Action is not uncertain")
        return {"ok": True}

    @app.post("/api/memories", status_code=201)
    async def memory(body: Memory):
        return {"id": store.memory(body.content)}

    @app.delete("/api/memories/{ident}")
    async def forget(ident: str):
        if store.rows("SELECT id FROM tasks WHERE status IN ('running','queued','awaiting_approval')"):
            raise HTTPException(409, "Stop active tasks before forgetting memory")
        store.forget_memory(ident)
        # Remove persisted prompt copies so forgotten information cannot reappear through resume.
        store.execute(
            "UPDATE tasks SET history='[]',status='cancelled' WHERE status IN ('blocked','interrupted','failed')"
        )
        store.execute("UPDATE tasks SET history='[]' WHERE status IN ('ready','completed','cancelled')")
        return {"ok": True}

    @app.post("/api/settings")
    async def settings(body: Settings):
        if sum(len(v) for v in body.skills.values()) > 20000:
            raise HTTPException(400, "Skill instructions exceed 20,000 characters")
        for key, value in body.model_dump().items():
            store.set_preference(key, value)
        return {"ok": True}

    @app.post("/api/connectors/refresh")
    async def refresh():
        if runtime.current:
            raise HTTPException(409, "Wait for the active task before refreshing tool discovery")
        await runtime.tools.refresh()
        return {"errors": runtime.tools.errors}

    @app.post("/api/schedules", status_code=201)
    async def schedule(body: Schedule):
        channel_exists(body.channel)
        ident = uid()
        store.execute(
            "INSERT INTO schedules VALUES(?,?,?,?,?,?,?,1)",
            (
                ident,
                body.name,
                body.prompt,
                body.channel,
                provider_name(body.provider),
                body.interval,
                body.next_run,
            ),
        )
        return {"id": ident}

    @app.delete("/api/schedules/{ident}")
    async def unschedule(ident: str):
        store.execute("DELETE FROM schedules WHERE id=?", (ident,))
        return {"ok": True}

    @app.get("/api/artifacts/{ident}")
    async def download(ident: str):
        rows = store.rows("SELECT * FROM artifacts WHERE id=?", (ident,))
        if not rows:
            raise HTTPException(404, "Artifact not found")
        item = rows[0]
        # Generated HTML/SVG must never execute in the authenticated application's origin.
        return FileResponse(
            config.data_dir / "artifacts" / item["filename"],
            filename=item["filename"],
            media_type="application/octet-stream",
            headers={"Content-Security-Policy": "sandbox; default-src 'none'"},
        )

    @app.get("/api/artifact-text/{ident}")
    async def artifact_text(ident: str):
        rows = store.rows("SELECT * FROM artifacts WHERE id=?", (ident,))
        if not rows or rows[0]["format"] not in {"md", "txt", "csv", "html"}:
            raise HTTPException(400, "This format can be edited in its native application")
        return {"content": (config.data_dir / "artifacts" / rows[0]["filename"]).read_text()}

    @app.post("/api/artifacts/{ident}/versions", status_code=201)
    async def edit_artifact(ident: str, body: Artifact):
        rows = store.rows("SELECT * FROM artifacts WHERE id=?", (ident,))
        if not rows:
            raise HTTPException(404, "Artifact not found")
        return create_artifact(store, config.data_dir / "artifacts", rows[0]["task"], **body.model_dump())

    @app.post("/api/browser/login")
    async def browser_login(body: BrowserLogin):
        if not config.browser or runtime.current:
            raise HTTPException(409, "Pause browser work before entering a login")
        runtime.private_values.add(body.value)
        await runtime.browser.login(body.selector, body.value)
        return {"ok": True}

    @app.post("/api/transcribe")
    async def transcribe(request: Request):
        if not config.voice_model:
            raise HTTPException(409, "Configure a local voice_model to enable transcription")
        from tempfile import TemporaryDirectory

        from faster_whisper import WhisperModel

        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > 8_000_000:
                raise HTTPException(413, "Recording exceeds 8 MB")

        def decode():
            with TemporaryDirectory(dir=config.data_dir) as directory:
                path = Path(directory) / "recording.audio"
                path.write_bytes(data)
                # Operator supplies an already downloaded model. No implicit network downloads.
                model = WhisperModel(
                    config.voice_model, device="cpu", compute_type="int8", local_files_only=True
                )
                segments, _ = model.transcribe(str(path), vad_filter=True)
                return " ".join(s.text for s in segments)[:32000]

        return {"text": await asyncio.to_thread(decode)}

    @app.get("/api/events")
    async def events(after: int = 0):
        return store.rows("SELECT * FROM events WHERE id>? ORDER BY id LIMIT 100", (after,))

    @app.get("/api/export")
    async def export():
        return JSONResponse(
            {
                "format": "openduet-v1",
                "memories": store.rows("SELECT * FROM memories"),
                "channels": store.rows("SELECT * FROM channels"),
                "messages": store.rows("SELECT * FROM messages ORDER BY created"),
            },
            headers={"Content-Disposition": 'attachment; filename="openduet-export.json"'},
        )

    @app.post("/api/import")
    async def import_memory(body: Import):
        return {"ids": [store.memory(m.content) for m in body.memories]}

    app.mount("/", StaticFiles(directory=Path(__file__).parent / "web", html=True), name="web")
    return app
