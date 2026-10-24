"""Sources are scoped to the task that actually retrieved them."""

from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urlsplit


def source_url(data, depth=0):
    if depth > 5:
        return ""
    if isinstance(data, dict):
        for key in (
            "url",
            "web_url",
            "html_url",
            "htmlLink",
            "webLink",
            "webViewLink",
            "permalink",
            "source_url",
            "hosted_invoice_url",
            "uri",
            "edit_url",
            "view_url",
            "scheduling_url",
        ):
            value = data.get(key)
            if isinstance(value, str):
                try:
                    parsed = urlsplit(value)
                except ValueError:
                    continue
                if (
                    parsed.scheme in {"http", "https"}
                    and parsed.hostname
                    and not parsed.username
                    and not parsed.password
                ):
                    return value
        for link in (data.get("links") or [])[:20]:
            if isinstance(link, str) and (url := source_url({"url": link}, depth + 1)):
                return url
        for key in ("structuredContent", "items", "results", "events", "messages", "data", "urls", "node"):
            if key in data and (url := source_url(data[key], depth + 1)):
                return url
        for block in data.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                try:
                    if url := source_url(json.loads(block.get("text", "")), depth + 1):
                        return url
                except (ValueError, TypeError):
                    pass
    elif isinstance(data, list):
        for item in data[:20]:
            if url := source_url(item, depth + 1):
                return url
    return ""


def source_records(data, path="result", depth=0):
    """Bounded record references retain their own URL and result locator."""
    if depth > 5:
        return []
    if isinstance(data, list):
        return [
            (
                f"{path}[{index}].node" if isinstance(item.get("node"), dict) else f"{path}[{index}]",
                item["node"] if isinstance(item.get("node"), dict) else item,
            )
            for index, item in enumerate(data[:20])
            if isinstance(item, dict)
        ]
    if not isinstance(data, dict):
        return []
    for key in (
        "structuredContent",
        "items",
        "results",
        "events",
        "messages",
        "data",
        "invoices",
        "value",
        "QueryResponse",
        "Invoice",
        "files",
        "envelopes",
        "collection",
        "products",
        "elements",
        "payrolls",
        "employees",
        "edges",
        "catalog",
    ):
        if key in data:
            found = source_records(data[key], path + "." + key, depth + 1)
            if found:
                return found
    for index, block in enumerate(data.get("content") or []):
        if isinstance(block, dict) and block.get("type") == "text":
            try:
                found = source_records(
                    json.loads(block.get("text", "")), f"{path}.content[{index}]", depth + 1
                )
                if found:
                    return found
            except (ValueError, TypeError):
                pass
    return []


class Sources:
    def __init__(self, store):
        self.store = store
        with store.db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS sources(id TEXT,task TEXT,tool TEXT,url TEXT,excerpt TEXT,PRIMARY KEY(id,task))"
            )

    def register(self, task, tool, data):
        encoded = json.dumps(data, ensure_ascii=False, default=str)
        ident = "s" + hashlib.sha256((task + tool + encoded).encode()).hexdigest()[:12]
        records = source_records(data)
        # A collection source must not silently link to its first record.
        url = "" if records else source_url(data)
        self.store.execute(
            "INSERT OR IGNORE INTO sources VALUES(?,?,?,?,?)",
            (ident, task, tool, url[:2000], encoded[:16000]),
        )
        references = []
        for locator, record in records:
            locator = str(record.get("locator", locator))[:500]
            excerpt = json.dumps({"locator": locator, "record": record}, ensure_ascii=False, default=str)
            source = "s" + hashlib.sha256((task + tool + excerpt).encode()).hexdigest()[:12]
            url = source_url(record)
            self.store.execute(
                "INSERT OR IGNORE INTO sources VALUES(?,?,?,?,?)",
                (source, task, tool, url[:2000], excerpt[:16000]),
            )
            references.append(
                {
                    "source_id": source,
                    "url": url[:2000],
                    "locator": locator,
                    "record_id": str(
                        next(
                            (
                                record[key]
                                for key in ("id", "Id", "uuid", "uid", "uri", "envelopeId", "sub", "ts")
                                if record.get(key) is not None
                            ),
                            "",
                        )
                    )[:200],
                }
            )
        return {"source_id": ident, "sources": references, "data": data}

    def require(self, task, text):
        known = {row["id"] for row in self.listing(task)}
        unknown = set(re.findall(r"\[\^([a-zA-Z0-9_-]+)\]", text)) - known
        if unknown:
            raise ValueError("Unverified artifact source: " + ", ".join(sorted(unknown)))

    def listing(self, task):
        return self.store.rows("SELECT * FROM sources WHERE task=?", (task,))

    def validate(self, task, text):
        known = {row["id"] for row in self.listing(task)}
        return re.sub(
            r"\[\^([a-zA-Z0-9_-]+)\]",
            lambda match: match[0] if match[1] in known else "[Unverified source: " + match[1] + "]",
            text,
        )
