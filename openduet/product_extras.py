"""Deliverable, private login and issuer endpoints for the authenticated console."""

import json

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse

from .registry import endpoint


def install(app, runtime):
    store = runtime.store

    @app.post("/api/password-manager")
    async def password_manager(request: Request):
        body = await request.json()
        if body.get("provider") not in {"1password", "bitwarden"} or not body.get("vault"):
            raise ValueError("Choose a dedicated 1Password or Bitwarden vault")
        endpoint(body["url"])
        token = body.pop("token", "")
        runtime.vault.put("password_manager.token", token)
        store.set_preference("password_manager", body)
        return {"ok": True}

    @app.post("/api/wallet")
    async def wallet_settings(request: Request):
        body = await request.json()
        for field in ("key", "cardholder", "webhook"):
            value = body.pop(field, "")
            if value:
                if field == "key" and value.startswith("sk_live_") and not runtime.config.wallet_allow_live:
                    raise ValueError(
                        "Live issuing must be explicitly enabled by the operator; use a test-mode issuer first"
                    )
                runtime.vault.put("wallet.stripe." + field, value)
        if any(not isinstance(body.get(key), int) or body[key] < 0 for key in ("daily_cap", "monthly_cap")):
            raise ValueError("Caps must be nonnegative integers in minor currency units")
        if not isinstance(body.get("merchants"), list) or not isinstance(
            body.get("checkout_hosts", {}), dict
        ):
            raise ValueError("Invalid merchant scope")
        if not isinstance(body.get("categories", []), list) or any(
            not isinstance(item, str) or not item.replace("_", "").isalnum()
            for item in body.get("categories", [])
        ):
            raise ValueError("Merchant categories must use the issuer's category names")
        if body.get("enabled"):
            required = {"wallet.stripe.key", "wallet.stripe.cardholder", "wallet.stripe.webhook"}
            present = {row["name"] for row in store.rows("SELECT name FROM secrets")}
            if not required <= present or not body["merchants"] or not runtime.config.public_url:
                raise ValueError(
                    "An eligible issuer, authorization webhook, public HTTPS URL and merchant scope are required"
                )
        store.set_preference("wallet", body)
        return {"ok": True}

    @app.post("/api/wallet/webhook")
    async def issuer_webhook(request: Request):
        data = await request.body()
        if len(data) > 1_000_000:
            raise HTTPException(413)
        event = runtime.wallet.verify_webhook(data, request.headers.get("stripe-signature", ""))
        if event.get("type") == "issuing_authorization.request":
            return {"approved": runtime.wallet.authorize(event)}
        return {"received": True}

    @app.post("/api/purchases/{ident}/cancel")
    async def cancel_purchase(ident: str):
        return await runtime.wallet.cancel(ident)

    @app.get("/api/make/{ident}")
    async def artifact_preview(ident: str):
        rows = store.rows("SELECT * FROM artifacts WHERE id=?", (ident,))
        if not rows:
            raise HTTPException(404, "Artifact not found")
        item = rows[0]
        versions = runtime.make.versions(ident)
        selected = next((version for version in versions if version["id"] == ident), {})
        content = selected.get("spec", "")
        if not content and item["format"] in {"md", "txt", "csv", "html"}:
            content = (runtime.config.data_dir / "artifacts" / item["filename"]).read_text()
        spec = None
        if content.lstrip().startswith("{"):
            try:
                spec = json.loads(content)
            except ValueError:
                pass
        return item | {
            "versions": versions,
            "version": selected.get("version", 1),
            "content": content,
            "spec": spec,
            "metadata": json.loads(selected.get("metadata", "{}")),
            "preview_url": runtime.config.prototype_url.rstrip("/") + "/p/" + ident + "/index.html",
        }

    @app.get("/api/make/{ident}/slides/{name}")
    async def slide_preview(ident: str, name: str):
        import re

        if not re.fullmatch(r"[0-9a-f]{32}", ident) or not re.fullmatch(r"slide-[0-9]+\.png", name):
            raise HTTPException(404)
        if not store.rows("SELECT id FROM artifacts WHERE id=?", (ident,)):
            raise HTTPException(404)
        path = runtime.config.data_dir / "artifacts" / "previews" / ident / name
        if not path.is_file():
            raise HTTPException(404)
        return FileResponse(path, media_type="image/png")

    @app.get("/api/make/{ident}/diff/{other}")
    async def artifact_diff(ident: str, other: str):
        return {"diff": runtime.make.diff(ident, other)}

    @app.post("/api/artifacts/{ident}/revise", status_code=202)
    async def revise(ident: str, request: Request):
        body = await request.json()
        return {"task": runtime.make.revise(ident, body.get("changes", ""))}

    @app.get("/api/attachments/{ident}")
    async def download_attachment(ident: str):
        rows = store.rows("SELECT * FROM attachments WHERE id=?", (ident,))
        if not rows:
            raise HTTPException(404)
        item = rows[0]
        return FileResponse(
            runtime.config.data_dir / "attachments" / item["filename"],
            filename=item["name"],
            media_type="application/octet-stream",
            headers={"Content-Security-Policy": "sandbox; default-src 'none'"},
        )
