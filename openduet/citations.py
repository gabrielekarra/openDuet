"""Sources are scoped to the task that actually retrieved them."""

from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urlsplit


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
        urls = re.findall(r'https?://[^\s<>"\\]+', encoded)
        url = next((u for u in urls if not urlsplit(u).username), "")
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
