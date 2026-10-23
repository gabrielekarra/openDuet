"""One-use approvals shared by web and Telegram, always bound to an exact payload."""

from __future__ import annotations

import json
import time

from .store import uid


def preview(call, tool=None):
    arguments = json.loads(call["arguments"])
    label = tool.remote_name if tool and tool.remote_name else call["name"]
    if tool and tool.connector:
        label = tool.connector + "/" + label
    name = label.lower()
    kind = next(
        (
            label
            for label, words in {
                "email": ("mail", "message", "reply"),
                "payment": ("pay", "purchase", "checkout"),
                "signature": ("signature", "sign_document", "sign_contract"),
                "delete": ("delete", "remove"),
                "calendar": ("calendar", "event", "meeting"),
                "publish": ("publish", "post"),
            }.items()
            if any(word in name for word in words)
        ),
        "action",
    )
    summary = [kind.upper() + " · " + label]
    for key, value in arguments.items():
        shown = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
        if key in {"body", "content", "text", "value"}:
            summary.append("\n" + shown)
        else:
            summary.append(key.replace("_", " ").title() + ": " + shown)
    return {
        **call,
        "kind": kind,
        "payload": arguments,
        "expires": call["created"] + 86400,
        "display_name": label,
        "summary": "\n".join(summary),
    }


class Approvals:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store

    def decide(self, ident, action, edited=None):
        rows = self.store.rows("SELECT * FROM calls WHERE id=?", (ident,))
        if not rows:
            raise ValueError("Approval not found")
        call = rows[0]
        if self.store.task(call["task"])["status"] == "cancelled":
            raise ValueError("This task was cancelled; prepare a fresh request")
        if call["status"] not in {"pending", "deferred"}:
            raise ValueError("This action was already reviewed")
        if call["status"] == "deferred" and action == "defer":
            raise ValueError("This action is already deferred")
        if action == "approve":
            if call["created"] < time.time() - 86400:
                raise ValueError("Approval expired; prepare a fresh action")
            self.runtime.tools.check_binding(call)
        if action == "edit":
            self.runtime.tools.check_binding(call)
            arguments = json.loads(call["arguments"])
            if not isinstance(edited, dict) or set(edited) - set(arguments):
                raise ValueError("Edit only fields from the displayed payload")
            arguments.update(edited)
            self.runtime.tools.get(call["name"], arguments)
            replacement = uid()
            # Same logical call id; the old payload remains as an immutable audit event.
            with self.store.db() as db:
                changed = db.execute(
                    "UPDATE calls SET status='superseded',call_id=call_id||? "
                    "WHERE id=? AND status IN ('pending','deferred')",
                    (":superseded:" + replacement, ident),
                ).rowcount
                if not changed:
                    raise ValueError("This action was already reviewed")
                db.execute(
                    "INSERT INTO calls VALUES(?,?,?,?,?,?,?,?)",
                    (
                        replacement,
                        call["task"],
                        call["call_id"],
                        call["name"],
                        json.dumps(arguments),
                        "pending",
                        None,
                        time.time(),
                    ),
                )
                db.execute(
                    "INSERT INTO call_bindings SELECT ?,fingerprint,replay_safe FROM call_bindings WHERE call=?",
                    (replacement, ident),
                )
                task = self.store.task(call["task"])
                history = json.loads(task["history"])
                for message in history:
                    for entry in message.get("tool_calls", []):
                        if entry["id"] == call["call_id"]:
                            entry["function"]["arguments"] = json.dumps(arguments)
                db.execute("UPDATE tasks SET history=? WHERE id=?", (json.dumps(history), call["task"]))
            return {"id": replacement}
        status = {"approve": "approved", "reject": "denied", "defer": "deferred"}.get(action)
        if status is None:
            raise ValueError("Unknown approval action")
        changed = self.store.execute(
            "UPDATE calls SET status=? WHERE id=? AND status IN ('pending','deferred')", (status, ident)
        )
        if not changed:
            raise ValueError("This action was already reviewed")
        if action in {"approve", "reject"}:
            self.store.execute(
                "UPDATE decisions SET response=?,response_reason='user',response_ts=?,learning_enabled=1 WHERE event_id IN (SELECT event FROM initiatives WHERE task=?)",
                ("approve" if action == "approve" else "dismiss", time.time(), call["task"]),
            )
        self.store.execute(
            "UPDATE tasks SET status='queued' WHERE id=? AND status IN ('awaiting_approval','ready')",
            (call["task"],),
        )
        return {"ok": True}
