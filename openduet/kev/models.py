"""Explicit downloads from pinned revisions with per-file SHA-256 verification."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import httpx

ROOT = Path(os.environ.get("OPENDUET_KEV_MODELS", ".runtime/kev-models"))
MANIFEST = Path(__file__).with_name("manifest.json")
PROGRESS = {"status": "idle", "downloaded": 0, "total": 0}


def manifest():
    return json.loads(MANIFEST.read_text())["models"]


def resolve_local(model):
    return ROOT / model.replace("/", "--")


def verify(entry):
    directory = resolve_local(entry["id"])
    for file in entry["files"]:
        path = directory / file["name"]
        if not path.is_file() or path.stat().st_size != file["size"]:
            raise ValueError("Kev model is missing; start its download from Proactivity")
        with path.open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() != file["sha256"]:
                raise ValueError("Kev model checksum mismatch")
    return directory


async def download(backend):
    if backend not in {"mlx", "torch"}:
        raise ValueError("Choose mlx or torch")
    if PROGRESS["status"] == "downloading":
        raise ValueError("A model download is already running")
    entries = [entry for entry in manifest() if entry["backend"] == backend]
    PROGRESS.update(
        status="downloading",
        downloaded=0,
        total=sum(file["size"] for entry in entries for file in entry["files"]),
    )
    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            for entry in entries:
                directory = resolve_local(entry["id"])
                directory.mkdir(parents=True, exist_ok=True)
                for file in entry["files"]:
                    path = directory / file["name"]
                    if path.is_file():
                        with path.open("rb") as source:
                            if hashlib.file_digest(source, "sha256").hexdigest() == file["sha256"]:
                                PROGRESS["downloaded"] += path.stat().st_size
                                continue
                    temporary = path.with_suffix(path.suffix + ".partial")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    digest, size = hashlib.sha256(), 0
                    async with client.stream(
                        "GET",
                        f"https://huggingface.co/{entry['id']}/resolve/{entry['revision']}/{file['name']}",
                    ) as response:
                        response.raise_for_status()
                        with temporary.open("wb") as output:
                            async for chunk in response.aiter_bytes():
                                size += len(chunk)
                                if size > file["size"]:
                                    raise ValueError("Unexpected model file size")
                                output.write(chunk)
                                digest.update(chunk)
                                PROGRESS["downloaded"] += len(chunk)
                    if size != file["size"] or digest.hexdigest() != file["sha256"]:
                        temporary.unlink(missing_ok=True)
                        raise ValueError("Model checksum mismatch")
                    temporary.replace(path)
        PROGRESS["status"] = "verified"
    except BaseException:
        PROGRESS["status"] = "failed"
        raise
