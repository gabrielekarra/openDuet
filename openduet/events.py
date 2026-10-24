"""Versioned connector events with durable cursors and content-based edit detection."""

from __future__ import annotations

import hashlib
import json
import time

from pydantic import BaseModel, Field

from .mappers import normalize, timestamp


class ConnectorEvent(BaseModel):
    version: int = 1
    id: str = Field(max_length=200)
    source: str = Field(max_length=300)
    kind: str = Field(max_length=80)
    occurred_at: float
    actors: list[str] = Field(default_factory=list, max_length=30)
    subject: str = Field(default="", max_length=1000)
    text: str = Field(default="", max_length=16000)
    links: list[str] = Field(default_factory=list, max_length=20)
    payload: dict = Field(default_factory=dict)


class EventStore:
    def __init__(self, store):
        self.store = store
        with store.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS connector_events(
                    id TEXT PRIMARY KEY,connector TEXT,record TEXT,hash TEXT,kind TEXT,data TEXT,created REAL,processed INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS event_heads(connector TEXT,record TEXT,hash TEXT,PRIMARY KEY(connector,record));
                CREATE TABLE IF NOT EXISTS connector_cursors(connector TEXT PRIMARY KEY,cursor TEXT,next_poll REAL,error TEXT);
            """)

    def ingest(self, connector, records, default_kind="mail.received", cursor=None, now=None):
        now = now or time.time()
        identifiers = []
        if len(records) > 200:
            records = records[:200]
        with self.store.db() as db:
            db.execute("BEGIN IMMEDIATE")
            for raw in records:
                raw = normalize(raw, default_kind, connector)
                record = str(raw.get("id", raw.get("message_id", raw.get("record_id", ""))))[:200]
                if not record:
                    continue
                kind = str(raw.get("kind", default_kind))[:80]
                payload = raw.get("payload", raw)
                subject = str(raw.get("subject", raw.get("summary", raw.get("title", ""))))[:1000]
                body = str(raw.get("text", raw.get("body", raw.get("description", ""))))[:16000]
                actors = raw.get("actors", [str(raw.get("sender", raw.get("from", "")))])
                stamp = raw.get("occurred_at", raw.get("updated_at", raw.get("sent_at", now)))
                stamp = timestamp(stamp, now)
                stable = {"subject": subject, "text": body, "actors": actors, "payload": payload}
                digest = hashlib.sha256(json.dumps(stable, sort_keys=True, default=str).encode()).hexdigest()
                previous = db.execute(
                    "SELECT hash FROM event_heads WHERE connector=? AND record=?", (connector, record)
                ).fetchone()
                if previous and previous["hash"] == digest:
                    continue
                if previous and kind == "mail.received":
                    old = db.execute(
                        "SELECT data FROM connector_events WHERE connector=? AND record=? AND hash=?",
                        (connector, record, previous["hash"]),
                    ).fetchone()
                    old_payload = json.loads(old["data"])["payload"] if old else {}
                    if "INBOX" in old_payload.get("labels", []) and "INBOX" not in payload.get("labels", []):
                        kind = "mail.archived"
                    elif old_payload.get("unread") is True and payload.get("unread") is False:
                        kind = "mail.read"
                if previous and kind.startswith("calendar."):
                    kind = "calendar.event_changed"
                ident = hashlib.sha256((connector + ":" + record + ":" + digest).encode()).hexdigest()[:32]
                event = ConnectorEvent(
                    id=ident,
                    source=connector + ":" + record,
                    kind=kind,
                    occurred_at=stamp,
                    actors=[
                        str(value)[:300] for value in (actors if isinstance(actors, list) else [actors])[:30]
                    ],
                    subject=subject,
                    text=body,
                    links=raw.get("links", [raw["url"]] if raw.get("url") else [])[:20],
                    payload=payload,
                )
                if len(event.model_dump_json()) > 100000:
                    raise ValueError("Connector event payload is too large")
                db.execute(
                    "INSERT OR IGNORE INTO connector_events(id,connector,record,hash,kind,data,created) VALUES(?,?,?,?,?,?,?)",
                    (ident, connector, record, digest, kind, event.model_dump_json(), now),
                )
                db.execute("INSERT OR REPLACE INTO event_heads VALUES(?,?,?)", (connector, record, digest))
                identifiers.append(ident)
            if cursor is not None:
                db.execute(
                    "INSERT INTO connector_cursors VALUES(?,?,0,'') ON CONFLICT(connector) DO UPDATE SET cursor=excluded.cursor",
                    (connector, json.dumps(cursor)),
                )
        return identifiers

    def forget(self, connector):
        with self.store.db() as db:
            db.execute("DELETE FROM connector_events WHERE connector=?", (connector,))
            db.execute("DELETE FROM event_heads WHERE connector=?", (connector,))
            db.execute("DELETE FROM connector_cursors WHERE connector=?", (connector,))


def unpack(result):
    if result.get("isError"):
        raise ValueError("The connector reported a polling error")
    if result.get("structuredContent"):
        data = result["structuredContent"]
    else:
        data = result
        for content in result.get("content", []):
            if content.get("type") == "text":
                try:
                    data = json.loads(content["text"])
                    break
                except ValueError:
                    continue
    if isinstance(data, list):
        return data, None
    if not isinstance(data, dict):
        raise ValueError("Event tool must return an object or array")
    if isinstance(data.get("QueryResponse"), dict):
        data = data["QueryResponse"]
    for wrapper in ("catalog", "data"):
        if isinstance(data.get(wrapper), dict):
            nested = data[wrapper]
            if any(
                isinstance(nested.get(key), list) for key in ("products", "items", "results", "edges")
            ) or (
                isinstance(nested.get("products"), dict) and isinstance(nested["products"].get("edges"), list)
            ):
                data = nested
    if isinstance(data.get("products"), dict) and isinstance(data["products"].get("edges"), list):
        data = data["products"]
    for key in (
        "events",
        "messages",
        "items",
        "data",
        "results",
        "invoices",
        "value",
        "files",
        "Invoice",
        "envelopes",
        "collection",
        "products",
        "elements",
        "payrolls",
        "employees",
        "edges",
    ):
        if isinstance(data.get(key), list):
            records = data[key]
            if key == "edges":
                records = [edge.get("node", edge) for edge in records if isinstance(edge, dict)]
            cursor = data.get(
                "next_cursor",
                data.get(
                    "nextCursor",
                    data.get("nextPageToken", data.get("@odata.nextLink", data.get("continuation"))),
                ),
            )
            if cursor is None and isinstance(data.get("response_metadata"), dict):
                cursor = data["response_metadata"].get("next_cursor")
            if cursor is None and data.get("has_more") and records:
                cursor = records[-1].get("id")
            if cursor is None and isinstance(data.get("pagination"), dict):
                cursor = data["pagination"].get("next_page")
            # A returned current cursor is not necessarily the next page.
            if cursor is None and "cursor" in data and "has_more" not in data:
                cursor = data["cursor"]
            if len(records) > 200:
                raise ValueError("Event pages must contain at most 200 records; reduce the page size")
            if not all(isinstance(record, dict) for record in records):
                raise ValueError("Event records must be objects")
            return records, cursor or None
    return [], None
