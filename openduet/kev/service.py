"""Separate inference process; the console remains responsive while Kev is busy."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import models
from .schema import Bool, Choice, Score


class Batch(BaseModel):
    context: str = Field(max_length=50000)
    questions: list[dict] = Field(max_length=32)


def create_service(backend_name=None):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    name = backend_name or os.environ.get("OPENDUET_KEV_BACKEND", "torch")
    device = os.environ.get("OPENDUET_KEV_DEVICE", "cpu")
    backend = None
    lock = asyncio.Lock()
    download_task = None
    state = {
        "ready": False,
        "backend": name,
        "device": device,
        "latency_ms": None,
        "model": next(
            (
                entry["id"]
                for entry in models.manifest()
                if entry["backend"] == name and entry["role"] == "decision"
            ),
            "fake",
        ),
        "revision": next(
            (
                entry["revision"]
                for entry in models.manifest()
                if entry["backend"] == name and entry["role"] == "decision"
            ),
            "fixture",
        ),
    }

    @app.get("/health")
    async def health():
        return state | {
            "download": models.PROGRESS,
            "disk_bytes": sum(path.stat().st_size for path in models.ROOT.rglob("*") if path.is_file())
            if models.ROOT.exists()
            else 0,
        }

    @app.post("/model/download", status_code=202)
    async def download():
        nonlocal download_task, backend
        if download_task and not download_task.done():
            raise HTTPException(409, "Download already running")

        async def perform():
            nonlocal backend
            try:
                await models.download(name)
                state["ready"] = False
                backend = None
            except (OSError, ValueError):
                state["ready"] = False

        download_task = asyncio.create_task(perform())
        return {"started": True}

    @app.post("/decide")
    async def decide(batch: Batch):
        nonlocal backend
        questions = []
        for spec in batch.questions:
            kind = spec.pop("kind")
            cls = {"bool": Bool, "score": Score, "choice": Choice}.get(kind)
            if cls is None:
                raise HTTPException(422, "Unknown question type")
            try:
                if "options" in spec:
                    spec["options"] = tuple(spec["options"])
                questions.append(cls(**spec))
            except (ValueError, TypeError):
                raise HTTPException(422, "Invalid typed question") from None
        async with lock:

            def run():
                nonlocal backend
                if backend is None:
                    if name == "mlx":
                        from .adapter import KevDecisionBackend

                        models.verify(next(entry for entry in models.manifest() if entry["backend"] == "mlx"))
                        backend = KevDecisionBackend()
                    elif name == "fake":
                        from .backends import FakeBackend

                        backend = FakeBackend()
                    else:
                        from .backends import TorchBackend

                        backend = TorchBackend(device)
                started = time.perf_counter()
                results = backend.decide_many(batch.context, questions, calibrators=[None] * len(questions))
                state.update(ready=True, latency_ms=(time.perf_counter() - started) * 1000)
                return [asdict(result) for result in results]

            try:
                return await asyncio.to_thread(run)
            except Exception:
                state["ready"] = False
                raise HTTPException(503, "Kev is unavailable; download and verify its pinned model") from None

    return app


def main():
    import uvicorn

    uvicorn.run(create_service(), host="0.0.0.0", port=8768, access_log=False)
