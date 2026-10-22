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
        for key in ("structuredContent", "items", "results", "events", "messages", "data"):
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
        url = source_url(data)
        self.store.execute(
            "INSERT OR IGNORE INTO sources VALUES(?,?,?,?,?)",
            (ident, task, tool, url[:2000], encoded[:16000]),
        )
        return {"source_id": ident, "data": data}

    def listing(self, task):
        return self.store.rows("SELECT * FROM sources WHERE task=?", (task,))

    def validate(self, task, text):
        known = {row["id"] for row in self.listing(task)}
        return re.sub(
            r"\[\^([a-zA-Z0-9_-]+)\]",
            lambda match: match[0] if match[1] in known else "[Unverified source: " + match[1] + "]",
            text,
        )
