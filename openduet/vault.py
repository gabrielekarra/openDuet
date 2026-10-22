"""Encrypted credentials; only transport adapters may resolve references."""

from __future__ import annotations

import os
import time
from pathlib import Path

from cryptography.fernet import Fernet


class Vault:
    def __init__(self, store, directory: Path):
        self.store = store
        self.key_path = directory / "vault.key"
        key = os.environ.get("OPENDUET_SECRET_KEY", "").encode()
        if not key:
            try:
                fd = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(fd, "wb") as output:
                    output.write(Fernet.generate_key())
            key = self.key_path.read_bytes()
        self.cipher = Fernet(key)
        self.resolved: set[str] = set()
        with store.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS secrets(name TEXT PRIMARY KEY, ciphertext BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS secret_audit(
                    id INTEGER PRIMARY KEY, reference TEXT, purpose TEXT, task TEXT, created REAL);
            """)

    def put(self, reference, value):
        self.store.execute(
            "INSERT OR REPLACE INTO secrets VALUES(?,?)", (reference, self.cipher.encrypt(value.encode()))
        )
        self.resolved.add(value)

    def get(self, reference, *, purpose="transport", task=None):
        rows = self.store.rows("SELECT ciphertext FROM secrets WHERE name=?", (reference,))
        if not rows:
            raise ValueError("Credential is not connected")
        value = self.cipher.decrypt(rows[0]["ciphertext"]).decode()
        self.resolved.add(value)
        self.store.execute(
            "INSERT INTO secret_audit(reference,purpose,task,created) VALUES(?,?,?,?)",
            (reference, purpose, task, time.time()),
        )
        return value

    def remove(self, reference):
        self.store.execute("DELETE FROM secrets WHERE name=?", (reference,))

    def rotate(self, key: bytes):
        if os.environ.get("OPENDUET_SECRET_KEY"):
            raise ValueError("Rotate an environment-managed key together with the operator configuration")
        cipher = Fernet(key)
        # Keep a recoverable old key until both key file and transaction are durable.
        old_key = self.key_path.read_bytes()
        backup = self.key_path.with_suffix(".previous")
        backup.write_bytes(old_key)
        backup.chmod(0o600)
        try:
            with self.store.db() as db:
                for row in db.execute("SELECT * FROM secrets").fetchall():
                    db.execute(
                        "UPDATE secrets SET ciphertext=? WHERE name=?",
                        (cipher.encrypt(self.cipher.decrypt(row["ciphertext"])), row["name"]),
                    )
                temporary = self.key_path.with_suffix(".next")
                temporary.write_bytes(key)
                temporary.chmod(0o600)
                temporary.replace(self.key_path)
        except BaseException:
            self.key_path.write_bytes(old_key)
            raise
        else:
            self.cipher = cipher
            backup.unlink()
