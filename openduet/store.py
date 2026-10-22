from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


def uid():
    return uuid.uuid4().hex


class Store:
    """Single-user durable state. Each write is committed before an external effect."""

    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = directory / "openduet.db"
        with self.db() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS channels(id TEXT PRIMARY KEY, name TEXT NOT NULL);
                INSERT OR IGNORE INTO channels VALUES('main', 'Home');
                CREATE TABLE IF NOT EXISTS messages(
                    id TEXT PRIMARY KEY, channel TEXT NOT NULL, role TEXT NOT NULL,
                    content TEXT NOT NULL, task TEXT, created REAL NOT NULL);
                CREATE VIRTUAL TABLE IF NOT EXISTS message_search USING fts5(id UNINDEXED, content);
                CREATE TABLE IF NOT EXISTS tasks(
                    id TEXT PRIMARY KEY, channel TEXT NOT NULL, request TEXT NOT NULL, provider TEXT NOT NULL,
                    status TEXT NOT NULL, history TEXT NOT NULL, turns INTEGER DEFAULT 0,
                    created REAL NOT NULL, updated REAL NOT NULL, error TEXT DEFAULT '');
                CREATE TABLE IF NOT EXISTS calls(
                    id TEXT PRIMARY KEY, task TEXT NOT NULL, call_id TEXT NOT NULL, name TEXT NOT NULL,
                    arguments TEXT NOT NULL, status TEXT NOT NULL, result TEXT,
                    created REAL NOT NULL, UNIQUE(task, call_id));
                CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY, content TEXT NOT NULL, created REAL);
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_search USING fts5(id UNINDEXED, content);
                CREATE TABLE IF NOT EXISTS artifacts(
                    id TEXT PRIMARY KEY, task TEXT NOT NULL, title TEXT NOT NULL, format TEXT NOT NULL,
                    filename TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS schedules(
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, prompt TEXT NOT NULL, channel TEXT NOT NULL,
                    provider TEXT NOT NULL, interval INTEGER NOT NULL, next_run REAL NOT NULL,
                    enabled INTEGER DEFAULT 1);
                CREATE TABLE IF NOT EXISTS events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, content TEXT NOT NULL,
                    task TEXT, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS usage(day TEXT PRIMARY KEY, input INTEGER, output INTEGER);
                CREATE TABLE IF NOT EXISTS preferences(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)
        self.path.chmod(0o600)

    @contextmanager
    def db(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def rows(self, sql, args=()):
        with self.db() as db:
            return [dict(r) for r in db.execute(sql, args)]

    def execute(self, sql, args=()):
        with self.db() as db:
            return db.execute(sql, args).rowcount

    def preference(self, key, default=None):
        rows = self.rows("SELECT value FROM preferences WHERE key=?", (key,))
        return json.loads(rows[0]["value"]) if rows else default

    def set_preference(self, key, value):
        self.execute("INSERT OR REPLACE INTO preferences VALUES(?,?)", (key, json.dumps(value)))

    def event(self, kind, content, task=None):
        self.execute(
            "INSERT INTO events(kind,content,task,created) VALUES(?,?,?,?)",
            (kind, content, task, time.time()),
        )

    def message(self, channel, role, content, task=None, db=None):
        ident = uid()
        if db is None:
            with self.db() as conn:
                return self.message(channel, role, content, task, conn)
        db.execute(
            "INSERT INTO messages VALUES(?,?,?,?,?,?)", (ident, channel, role, content, task, time.time())
        )
        db.execute("INSERT INTO message_search VALUES(?,?)", (ident, content))
        return ident

    def new_task(self, channel, request, provider, db=None):
        ident, now = uid(), time.time()
        if db is None:
            with self.db() as conn:
                return self.new_task(channel, request, provider, conn)
        db.execute(
            "INSERT INTO tasks(id,channel,request,provider,status,history,created,updated) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (ident, channel, request, provider, "queued", "[]", now, now),
        )
        self.message(channel, "user", request, ident, db)
        return ident

    def task(self, ident):
        found = self.rows("SELECT * FROM tasks WHERE id=?", (ident,))
        if not found:
            raise KeyError(ident)
        return found[0]

    def status(self, ident, status, error=""):
        self.execute(
            "UPDATE tasks SET status=?, error=?, updated=? WHERE id=?", (status, error, time.time(), ident)
        )

    def recover(self):
        # An effect might have happened without its receipt being committed. Never replay automatically.
        self.execute("UPDATE calls SET status='uncertain' WHERE status='executing'")
        self.execute(
            "UPDATE tasks SET status='interrupted', error='Service restarted; review before resuming' "
            "WHERE status='running'"
        )

    def search(self, query, memory=False):
        if not memory and not self.preference("search_chats", True):
            return []
        # Quote user input so FTS operators and punctuation cannot change the query or crash parsing.
        words = [w.replace('"', '""') for w in query.split()[:20] if w]
        if not words:
            return []
        table, source = ("memory_search", "memories") if memory else ("message_search", "messages")
        return self.rows(
            f"SELECT s.* FROM {table} f JOIN {source} s ON s.id=f.id "
            f"WHERE {table} MATCH ? ORDER BY rank LIMIT 12",
            (" OR ".join('"' + w + '"' for w in words),),
        )

    def memory(self, content):
        ident = uid()
        with self.db() as db:
            db.execute("INSERT INTO memories VALUES(?,?,?)", (ident, content, time.time()))
            db.execute("INSERT INTO memory_search VALUES(?,?)", (ident, content))
        return ident

    def forget_memory(self, ident):
        with self.db() as db:
            db.execute("DELETE FROM memories WHERE id=?", (ident,))
            db.execute("DELETE FROM memory_search WHERE id=?", (ident,))

    def delete_channel(self, channel):
        if self.rows("SELECT id FROM tasks WHERE channel=? AND status IN ('running','queued')", (channel,)):
            raise ValueError("Stop active tasks before deleting this channel")
        # Delete generated context as well as the search index. Old checkpoints must not resurrect a chat.
        with self.db() as db:
            db.execute(
                "DELETE FROM message_search WHERE id IN (SELECT id FROM messages WHERE channel=?)", (channel,)
            )
            db.execute("DELETE FROM messages WHERE channel=?", (channel,))
            db.execute("DELETE FROM calls WHERE task IN (SELECT id FROM tasks WHERE channel=?)", (channel,))
            db.execute(
                "DELETE FROM artifacts WHERE task IN (SELECT id FROM tasks WHERE channel=?)", (channel,)
            )
            db.execute("DELETE FROM events WHERE task IN (SELECT id FROM tasks WHERE channel=?)", (channel,))
            db.execute("DELETE FROM tasks WHERE channel=?", (channel,))
            db.execute("DELETE FROM schedules WHERE channel=?", (channel,))
            if channel != "main":
                db.execute("DELETE FROM channels WHERE id=?", (channel,))

    def usage(self, incoming=0, outgoing=0):
        day = time.strftime("%Y-%m-%d", time.gmtime())
        with self.db() as db:
            db.execute(
                "INSERT INTO usage VALUES(?,?,?) ON CONFLICT(day) DO UPDATE SET "
                "input=input+excluded.input, output=output+excluded.output",
                (day, incoming, outgoing),
            )
            return dict(db.execute("SELECT * FROM usage WHERE day=?", (day,)).fetchone())
