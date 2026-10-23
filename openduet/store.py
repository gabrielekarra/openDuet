from __future__ import annotations

import json
import re
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
                CREATE TABLE IF NOT EXISTS call_bindings(
                    call TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, replay_safe INTEGER NOT NULL);
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
                CREATE TABLE IF NOT EXISTS task_origins(task TEXT PRIMARY KEY,kind TEXT,source TEXT);
                CREATE TABLE IF NOT EXISTS task_progress(task TEXT PRIMARY KEY,title TEXT,completed INTEGER,total INTEGER,updated REAL);
                CREATE TABLE IF NOT EXISTS usage_workstream(day TEXT,kind TEXT,input INTEGER,output INTEGER,PRIMARY KEY(day,kind));
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
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='attachments'").fetchone():
            for attachment in re.findall(r'"attachment"\s*:\s*"([0-9a-f]{32})"', request):
                db.execute("UPDATE attachments SET task=? WHERE id=? AND task IS NULL", (ident, attachment))
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
        with self.db() as db:
            # Only calls explicitly recorded as read-only may be repeated. A
            # missing legacy binding supplies no evidence that replay is safe.
            db.execute(
                "UPDATE calls SET status='approved' WHERE status='executing' AND id IN "
                "(SELECT call FROM call_bindings WHERE replay_safe=1)"
            )
            db.execute("UPDATE calls SET status='uncertain' WHERE status='executing'")
            db.execute(
                "UPDATE tasks SET status='blocked',error='An action has an uncertain outcome; inspect its service' "
                "WHERE status IN ('running','queued','awaiting_approval') AND id IN "
                "(SELECT task FROM calls WHERE status='uncertain')"
            )
            db.execute("UPDATE tasks SET status='queued',error='' WHERE status='running'")

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
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            task_query = "SELECT id FROM tasks WHERE channel=?"
            if "telegram_outbox" in tables:
                db.execute(
                    "DELETE FROM telegram_outbox WHERE EXISTS(SELECT 1 FROM tasks t WHERE t.channel=? AND instr(telegram_outbox.id,t.id)>0) OR EXISTS(SELECT 1 FROM calls c JOIN tasks t ON t.id=c.task WHERE t.channel=? AND instr(telegram_outbox.id,c.id)>0) OR json_extract(payload,'$._artifact') IN (SELECT id FROM artifacts WHERE task IN ("
                    + task_query
                    + ")) OR json_extract(payload,'$._attachment') IN (SELECT id FROM attachments WHERE task IN ("
                    + task_query
                    + "))",
                    (channel, channel, channel, channel),
                )
            if "telegram_cards" in tables:
                db.execute(
                    "DELETE FROM telegram_cards WHERE json_extract(CASE WHEN json_valid(payload) THEN payload ELSE '{}' END,'$.task') IN ("
                    + task_query
                    + ")",
                    (channel,),
                )
            if "attachment_inputs" in tables:
                db.execute(
                    "DELETE FROM attachment_inputs WHERE id IN (SELECT id FROM attachments WHERE task IN ("
                    + task_query
                    + "))",
                    (channel,),
                )
            for table, column in (
                ("sources", "task"),
                ("task_surfaces", "task"),
                ("attachments", "task"),
                ("dashboard_runs", "task"),
                ("initiatives", "task"),
                ("task_origins", "task"),
                ("task_progress", "task"),
                ("task_decisions", "task"),
                ("task_reviews", "task"),
            ):
                if table in tables:
                    db.execute(
                        "DELETE FROM " + table + " WHERE " + column + " IN (" + task_query + ")", (channel,)
                    )
            if "artifact_versions" in tables:
                db.execute(
                    "DELETE FROM artifact_versions WHERE id IN (SELECT id FROM artifacts WHERE task IN ("
                    + task_query
                    + "))",
                    (channel,),
                )
                db.execute(
                    "DELETE FROM dashboard_refresh WHERE root IN (SELECT id FROM artifacts WHERE task IN ("
                    + task_query
                    + "))",
                    (channel,),
                )
            db.execute(
                "DELETE FROM message_search WHERE id IN (SELECT id FROM messages WHERE channel=?)", (channel,)
            )
            db.execute("DELETE FROM messages WHERE channel=?", (channel,))
            db.execute(
                "DELETE FROM call_bindings WHERE call IN "
                "(SELECT id FROM calls WHERE task IN (SELECT id FROM tasks WHERE channel=?))",
                (channel,),
            )
            db.execute("DELETE FROM calls WHERE task IN (SELECT id FROM tasks WHERE channel=?)", (channel,))
            db.execute(
                "DELETE FROM artifacts WHERE task IN (SELECT id FROM tasks WHERE channel=?)", (channel,)
            )
            db.execute("DELETE FROM events WHERE task IN (SELECT id FROM tasks WHERE channel=?)", (channel,))
            db.execute("DELETE FROM tasks WHERE channel=?", (channel,))
            db.execute("DELETE FROM schedules WHERE channel=?", (channel,))
            if channel != "main":
                db.execute("DELETE FROM channels WHERE id=?", (channel,))

    def usage(self, incoming=0, outgoing=0, *, kind="user"):
        day = time.strftime("%Y-%m-%d", time.gmtime())
        with self.db() as db:
            db.execute(
                "INSERT INTO usage_workstream VALUES(?,?,?,?) ON CONFLICT(day,kind) DO UPDATE SET input=input+excluded.input,output=output+excluded.output",
                (day, kind, incoming, outgoing),
            )
            db.execute(
                "INSERT INTO usage VALUES(?,?,?) ON CONFLICT(day) DO UPDATE SET "
                "input=input+excluded.input, output=output+excluded.output",
                (day, incoming, outgoing),
            )
            return dict(db.execute("SELECT * FROM usage WHERE day=?", (day,)).fetchone())
