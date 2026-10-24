"""Deterministic wire normalization for common MCP service records; originals stay untrusted."""

from __future__ import annotations

import base64
from datetime import UTC, datetime


def timestamp(value, fallback=None):
    if isinstance(value, dict):
        value = value.get("dateTime", value.get("date"))
    try:
        number = float(value)
        return number / 1000 if number > 100_000_000_000 else number
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.timestamp()
        except (TypeError, ValueError):
            return fallback


def normalize(raw, kind, connector):
    # Stripe webhooks wrap a resource. Use its identity so subsequent updates
    # edit the same record; preserve the envelope as provenance.
    envelope = None
    if isinstance(raw.get("data"), dict) and isinstance(raw["data"].get("object"), dict):
        envelope, raw = raw, raw["data"]["object"]
    item = dict(raw)
    payload = dict(raw.get("payload", raw))
    if not item.get("id"):
        for key in ("Id", "uuid", "uid", "uri", "envelopeId", "sub"):
            if raw.get(key):
                item["id"] = str(raw[key])
                break
    subject = (
        raw.get("subject")
        or raw.get("title")
        or raw.get("name")
        or raw.get("emailSubject")
        or raw.get("summary")
    )
    if subject:
        item.setdefault("subject", subject)
    if isinstance(raw.get("properties"), dict):
        properties = raw["properties"]
        if not item.get("subject"):
            item["subject"] = (
                properties.get("dealname")
                or " ".join(str(properties.get(key) or "") for key in ("firstname", "lastname")).strip()
            )
        item.setdefault("sender", properties.get("email", ""))
        if not item.get("subject"):
            for value in properties.values():
                if isinstance(value, dict) and isinstance(value.get("title"), list):
                    item["subject"] = "".join(
                        str(part.get("plain_text", part.get("text", {}).get("content", "")))
                        for part in value["title"]
                    )[:1000]
                    break
    if "Id" in raw and ("DocNumber" in raw or "TotalAmt" in raw):
        item["subject"] = "Invoice " + str(raw.get("DocNumber", raw["Id"]))
        payload["amount_unit"] = "major currency units (provider value; no conversion applied)"
        payload["currency"] = raw.get("CurrencyRef", {}).get("value", "")
    if "envelopeId" in raw:
        payload["document_status"] = raw.get("status", "")
    if isinstance(raw.get("urls"), dict):
        item.setdefault(
            "links", [raw["urls"][key] for key in ("edit_url", "view_url") if raw["urls"].get(key)]
        )
    if isinstance(raw.get("payload"), dict) and isinstance(raw["payload"].get("headers"), list):
        headers = {entry["name"].lower(): entry.get("value", "") for entry in raw["payload"]["headers"]}
        item.setdefault("subject", headers.get("subject", ""))
        item.setdefault("sender", headers.get("from", ""))
        payload.update(
            message_id=headers.get("message-id", raw.get("id", "")),
            in_reply_to=headers.get("in-reply-to", ""),
            thread_id=raw.get("threadId", ""),
            to=headers.get("to", ""),
        )
        item.setdefault("body", raw.get("snippet", ""))
        body = raw["payload"].get("body", {}).get("data", "")
        if body and raw["payload"].get("mimeType") == "text/plain":
            try:
                item["body"] = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode(
                    "utf-8", errors="replace"
                )[:16000]
            except (ValueError, TypeError):
                pass
        labels = raw.get("labelIds", [])
        item["kind"] = "mail.sent" if "SENT" in labels else kind
        payload["unread"] = "UNREAD" in labels
        payload["labels"] = labels
    if "threadId" in raw:
        payload.setdefault("thread_id", raw["threadId"])
        item.setdefault("links", ["https://mail.google.com/mail/u/0/#all/" + str(raw["threadId"])])
    if raw.get("object") == "invoice":
        item.setdefault("subject", "Invoice " + str(raw.get("number") or raw.get("id", "")))
        item.setdefault("sender", raw.get("customer_email", ""))
        item.setdefault("text", raw.get("description") or "")
        item.setdefault("links", [raw["hosted_invoice_url"]] if raw.get("hosted_invoice_url") else [])
        payload["amount_unit"] = "minor currency units (provider value; no conversion applied)"
        payload["currency"] = raw.get("currency", "")
        if envelope:
            payload["provider_event"] = {
                key: envelope[key] for key in ("id", "type", "created") if key in envelope
            }
    if kind.startswith("calendar."):
        for field in ("start", "end"):
            if field in raw:
                payload[field] = timestamp(raw[field])
            elif field + "_time" in raw:
                payload[field] = timestamp(raw[field + "_time"])
        if not item.get("subject"):
            item["subject"] = raw.get("summary", raw.get("subject", ""))
        item.setdefault("links", [raw["htmlLink"]] if raw.get("htmlLink") else [])
    if "body" in item and isinstance(item["body"], dict):
        body = item["body"]
        # HTML remains inert data; the model does not get permission from it.
        item["body"] = str(body.get("content", body.get("text", "")))
    if "ts" in raw and (kind.startswith("chat.") or connector == "slack"):
        item.setdefault("id", raw["ts"])
        item.setdefault("sender", raw.get("user", ""))
        item.setdefault("occurred_at", timestamp(raw["ts"]))
        payload.setdefault("thread_id", raw.get("thread_ts", raw["ts"]))
    if "sender" in item and isinstance(item["sender"], dict):
        item["sender"] = item["sender"].get("emailAddress", {}).get("address", "")
    if isinstance(raw.get("from"), dict):
        item.setdefault("sender", raw["from"].get("emailAddress", {}).get("address", ""))
    for key in (
        "internalDate",
        "receivedDateTime",
        "sentDateTime",
        "updated_at",
        "created",
        "modifiedTime",
        "lastModifiedDateTime",
    ):
        if key in raw and timestamp(raw[key]) is not None:
            item.setdefault("occurred_at", timestamp(raw[key]))
            break
    payload.setdefault("sender", item.get("sender", item.get("from", "")))
    payload.setdefault("subject", item.get("subject", ""))
    item["payload"] = payload
    return item
