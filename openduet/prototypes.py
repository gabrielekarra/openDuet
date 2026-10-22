"""Cookieless prototype origin. Opaque sandbox frames cannot use workspace APIs."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

CSP = "sandbox allow-scripts; default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src data: blob:; connect-src 'none'; form-action 'none'; base-uri 'none'; object-src 'none'"


def create_app(directory=None):
    root = Path(directory or os.environ.get("OPENDUET_PROTOTYPES", "/prototypes")).resolve()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/p/{ident}/{name:path}")
    async def prototype(ident: str, name: str):
        if len(ident) != 32 or any(c not in "0123456789abcdef" for c in ident):
            raise HTTPException(404)
        target = (root / ident / (name or "index.html")).resolve()
        if not target.is_relative_to(root / ident) or not target.is_file():
            raise HTTPException(404)
        return FileResponse(
            target,
            headers={
                "Content-Security-Policy": CSP,
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
            },
        )

    return app


def main():
    import uvicorn

    uvicorn.run(create_app(), host="0.0.0.0", port=8767, access_log=False)
