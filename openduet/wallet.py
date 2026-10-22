"""Opt-in, approval-gated purchase scopes. Card credentials never become tool results."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import httpx

from .store import uid


class StripeIssuing:
    def __init__(self, vault, client=None):
        self.vault = vault
        self.client = client or httpx.AsyncClient(
            base_url="https://api.stripe.com", timeout=20, follow_redirects=False
        )

    async def request(self, method, path, data=None):
        key = self.vault.get("wallet.stripe.key", purpose="purchase-card")
        response = await self.client.request(
            method, path, data=data, headers={"Authorization": "Bearer " + key}
        )
        if response.is_error:
            raise ValueError("The card issuer rejected this operation")
        return response.json()

    async def create_purchase_card(self, scope):
        cardholder = self.vault.get("wallet.stripe.cardholder", purpose="purchase-card")
        values = {
            "type": "virtual",
            "currency": scope["currency"].lower(),
            "cardholder": cardholder,
            "status": "active",
            "spending_controls[spending_limits][0][amount]": scope["amount"],
            "spending_controls[spending_limits][0][interval]": "all_time",
            "spending_controls[spending_limits][1][amount]": scope["amount"],
            "spending_controls[spending_limits][1][interval]": "per_authorization",
        }
        card = await self.request("POST", "/v1/issuing/cards", values)
        return {"id": card["id"], "last4": card.get("last4", "")}

    async def cancel_card(self, handle):
        await self.request("POST", "/v1/issuing/cards/" + handle, {"status": "canceled"})

    async def private_card(self, handle):
        return await self.request("GET", "/v1/issuing/cards/" + handle + "?expand[]=number&expand[]=cvc")


class Wallet:
    def __init__(self, runtime, provider=None):
        self.runtime, self.store = runtime, runtime.store
        self.provider = provider or StripeIssuing(runtime.vault)
        with self.store.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS purchases(
                    id TEXT PRIMARY KEY,task TEXT,merchant TEXT,amount INTEGER,currency TEXT,
                    expires REAL,card TEXT,status TEXT,created REAL,authorization TEXT UNIQUE);
            """)

    def settings(self):
        return {
            "enabled": False,
            "daily_cap": 0,
            "monthly_cap": 0,
            "currency": "EUR",
            "merchants": [],
        } | self.store.preference("wallet", {})

    async def purchase(self, arguments, task):
        settings = self.settings()
        if not settings["enabled"]:
            raise ValueError("Purchase cards are disabled; connect an eligible issuer in Settings")
        merchant, amount, currency = arguments["merchant"], arguments["amount"], arguments["currency"].upper()
        if (
            merchant not in settings["merchants"]
            or currency != settings["currency"]
            or not isinstance(amount, int)
            or amount <= 0
        ):
            raise ValueError("Merchant, currency or purchase amount is outside the configured scope")
        now = time.time()
        ident = uid()
        with self.store.db() as db:
            db.execute("BEGIN IMMEDIATE")
            for days, cap in ((1, settings["daily_cap"]), (30, settings["monthly_cap"])):
                spent = db.execute(
                    "SELECT COALESCE(SUM(amount),0) FROM purchases WHERE created>? AND status!='cancelled'",
                    (now - days * 86400,),
                ).fetchone()[0]
                if amount + spent > cap:
                    raise ValueError("Purchase exceeds the configured spending cap")
            db.execute(
                "INSERT INTO purchases VALUES(?,?,?,?,?,?,NULL,'issuing',?,NULL)",
                (ident, task, merchant, amount, currency, now + 900, now),
            )
        scope = {
            "id": ident,
            "merchant": merchant,
            "amount": amount,
            "currency": currency,
            "expires": now + 900,
        }
        try:
            card = await self.provider.create_purchase_card(scope)
        except Exception:
            # An issuer timeout is uncertain: reserve the cap until the operator verifies it.
            self.store.execute("UPDATE purchases SET status='uncertain' WHERE id=?", (ident,))
            raise ValueError(
                "Card issuance outcome is uncertain; verify it with the issuer before retrying"
            ) from None
        self.store.execute("UPDATE purchases SET card=?,status='active' WHERE id=?", (card["id"], ident))
        return scope | {
            "purchase": ident,
            "last4": card["last4"],
            "status": "active",
            "note": "Card data is available only to the private checkout adapter",
        }

    def authorize(self, event):
        data = event["data"]["object"]
        card = data.get("card")
        card = card.get("id") if isinstance(card, dict) else card
        merchant = str(data.get("merchant_data", {}).get("network_id", ""))
        with self.store.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM purchases WHERE card=?", (card,)).fetchone()
            if row and row["authorization"] == data["id"] and row["status"] in {"authorized", "spent"}:
                return True
            if not row or row["status"] != "active" or row["expires"] <= time.time():
                return False
            if (
                merchant != row["merchant"]
                or data.get("currency", "").upper() != row["currency"]
                or not 0 < data.get("pending_request", {}).get("amount", 0) <= row["amount"]
            ):
                return False
            changed = db.execute(
                "UPDATE purchases SET status='authorized',authorization=? WHERE id=? AND status='active'",
                (data["id"], row["id"]),
            ).rowcount
            return bool(changed)

    def verify_webhook(self, content, signature):
        values = {}
        for item in signature.split(","):
            key, _, value = item.partition("=")
            values.setdefault(key, []).append(value)
        stamp = values.get("t", ["0"])[0]
        if abs(time.time() - int(stamp)) > 300:
            raise ValueError("Expired issuer signature")
        secret = self.runtime.vault.get("wallet.stripe.webhook", purpose="issuer-webhook")
        digest = hmac.new(secret.encode(), stamp.encode() + b"." + content, hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(digest, value) for value in values.get("v1", [])):
            raise ValueError("Invalid issuer signature")
        return json.loads(content)

    async def cancel(self, ident):
        rows = self.store.rows("SELECT * FROM purchases WHERE id=?", (ident,))
        if not rows or not rows[0]["card"]:
            raise ValueError("Purchase card not found")
        await self.provider.cancel_card(rows[0]["card"])
        self.store.execute(
            "UPDATE purchases SET status=? WHERE id=?",
            ("spent" if rows[0]["status"] == "authorized" else "cancelled", ident),
        )
        return {"cancelled": ident}

    async def tick(self):
        for row in self.store.rows(
            "SELECT id FROM purchases WHERE card IS NOT NULL AND ((status='active' AND expires<?) OR status='authorized')",
            (time.time(),),
        ):
            try:
                await self.cancel(row["id"])
            except (ValueError, httpx.HTTPError):
                pass

    async def checkout(self, purchase, expected_url, selectors, task):
        from urllib.parse import urlsplit

        row = self.store.rows("SELECT * FROM purchases WHERE id=? AND task=?", (purchase, task))
        if not row or row[0]["status"] != "active" or row[0]["expires"] <= time.time():
            raise ValueError("An active approved purchase card is required")
        allowed = self.store.preference("wallet", {}).get("checkout_hosts", {})
        if (
            urlsplit(expected_url).hostname != allowed.get(row[0]["merchant"])
            or urlsplit(expected_url).scheme != "https"
        ):
            raise ValueError("Checkout must match the operator-configured merchant HTTPS host")
        if set(selectors) != {"number", "cvc", "exp_month", "exp_year"}:
            raise ValueError("Checkout requires exact card field selectors")
        card = await self.provider.private_card(row[0]["card"])
        fields = {selectors[field]: str(card[field]) for field in selectors}
        self.runtime.private_values.update(fields.values())
        for selector, value in fields.items():
            await self.runtime.browser.login(selector, value, expected_url)
        return {
            "private_checkout_fields_filled": True,
            "purchase": purchase,
            "note": "Submit checkout separately; issuer authorizes only the approved scope",
        }

    async def close(self):
        if hasattr(self.provider, "client"):
            await self.provider.client.aclose()
