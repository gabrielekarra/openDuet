"""Direct TLS IMAP/SMTP accounts: encrypted app passwords, bounded reads and reviewed sends."""

from __future__ import annotations

import asyncio
import email.policy
import imaplib
import json
import re
import smtplib
import ssl
import time
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses, make_msgid, parsedate_to_datetime

from .store import uid

LIMIT = 131072


def mailbox(value):
    # RFC 3501 modified UTF-7, then IMAP string quoting. User input never
    # becomes a raw command or search clause.
    chunks = []
    pending = []

    def flush():
        if pending:
            import base64

            chunks.append(
                "&"
                + base64.b64encode("".join(pending).encode("utf-16-be"))
                .decode()
                .rstrip("=")
                .replace("/", ",")
                + "-"
            )
            pending.clear()

    for c in value:
        if 0x20 <= ord(c) <= 0x7E:
            flush()
            chunks.append("&-" if c == "&" else c)
        else:
            if ord(c) < 32:
                raise ValueError("Mailbox names cannot contain control characters")
            pending.append(c)
    flush()
    return '"' + "".join(chunks).replace("\\", "\\\\").replace('"', '\\"') + '"'


def sent_folder(client):
    status, rows = client.list()
    if status != "OK":
        return ""
    for row in rows or []:
        if not isinstance(row, bytes):
            continue
        match = re.match(rb'^\(([^)]*)\)\s+(?:"(?:[^"\\]|\\.)*"|NIL)\s+(.+)$', row)
        if not match or b"\\sent" not in match[1].lower().split():
            continue
        value = match[2].decode("ascii").strip('"').replace('\\"', '"').replace("\\\\", "\\")
        import base64

        def decode(match):
            if not match[1]:
                return "&"
            data = match[1].replace(",", "/")
            return base64.b64decode(data + "=" * (-len(data) % 4)).decode("utf-16-be")

        return re.sub(r"&([^-]*)-", decode, value)
    return ""


def html_text(value):
    from html.parser import HTMLParser

    class Reader(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.parts = []
            self.hidden = 0

        def handle_starttag(self, tag, attrs):
            if tag in {"script", "style", "head"}:
                self.hidden += 1
            elif tag in {"br", "p", "div", "li", "tr"} and not self.hidden:
                self.parts.append("\n")

        def handle_endtag(self, tag):
            if tag in {"script", "style", "head"} and self.hidden:
                self.hidden -= 1

        def handle_data(self, data):
            if not self.hidden:
                self.parts.append(data)

    parser = Reader()
    parser.feed(value)
    return "".join(parser.parts)


def record(raw, metadata, alias, validity, number):
    message = BytesParser(policy=email.policy.default).parsebytes(raw)
    parts = []
    for part in message.walk():
        if part.get_content_type() == "text/plain" and part.get_content_disposition() != "attachment":
            try:
                parts.append(part.get_content())
            except (LookupError, UnicodeError):
                pass
    if not parts:
        for part in message.walk():
            if part.get_content_type() == "text/html" and part.get_content_disposition() != "attachment":
                try:
                    parts.append(html_text(part.get_content()))
                except (LookupError, UnicodeError):
                    pass
    body = "\n".join(parts)
    # Quoted prior correspondence is not the sender's new promise/request.
    body = re.split(r"\n(?:On .{1,300}wrote:|Il .{1,300}ha scritto:)", body, maxsplit=1)[0]
    body = "\n".join(line for line in body.splitlines() if not line.lstrip().startswith(">"))[:16000]
    try:
        stamp = parsedate_to_datetime(str(message.get("Date", ""))).timestamp()
    except (TypeError, ValueError, OverflowError):
        stamp = time.time()
    sender = getaddresses([str(message.get("From", ""))])[0][1] if message.get("From") else ""
    mid = str(message.get("Message-ID", ""))[:500]
    return {
        "id": f"{alias}:{validity}:{number}",
        "kind": "mail.sent" if alias == "sent" else "mail.received",
        "subject": str(message.get("Subject", ""))[:1000],
        "text": body,
        "actors": [sender],
        "occurred_at": stamp,
        "payload": {
            "sender": sender,
            "to": str(message.get("To", ""))[:2000],
            "message_id": mid,
            "in_reply_to": str(message.get("In-Reply-To", ""))[:500],
            "references": str(message.get("References", ""))[-2000:],
            "uid": number,
            "uidvalidity": validity,
            "mailbox": alias,
            "unread": b"\\Seen" not in metadata,
            "truncated": len(raw) >= LIMIT,
        },
    }


class MailAccounts:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.store.execute(
            "CREATE TABLE IF NOT EXISTS native_mail_cursors(account TEXT,mailbox TEXT,value TEXT,PRIMARY KEY(account,mailbox))"
        )

    def listing(self):
        return self.store.preference("mail_accounts", {})

    def credentials(self, name):
        if name not in self.listing() or not self.runtime.tools.enabled(name):
            raise ValueError("Mail access was disconnected")
        return json.loads(self.runtime.vault.get("mail:" + name, purpose="mail transport"))

    @staticmethod
    def connection(config, credentials):
        client = imaplib.IMAP4_SSL(
            config["imap_host"], config["imap_port"], ssl_context=ssl.create_default_context(), timeout=20
        )
        try:
            client.login(credentials["username"], credentials["password"])
        except BaseException:
            client.shutdown()
            raise
        return client

    def validate(self, config, credentials):
        client = self.connection(config, credentials)
        try:
            if config.get("sent") == "auto":
                config["sent"] = sent_folder(client)
            for alias in ("inbox", "sent"):
                if config.get(alias) and client.select(mailbox(config[alias]), readonly=True)[0] != "OK":
                    raise ValueError("Mailbox unavailable")
        finally:
            client.logout()
        if config["smtp_host"]:
            with smtplib.SMTP_SSL(
                config["smtp_host"], config["smtp_port"], context=ssl.create_default_context(), timeout=20
            ) as sender:
                sender.login(credentials["username"], credentials["password"])
                sender.noop()

    async def add(self, values):
        fields = {
            "label",
            "imap_host",
            "imap_port",
            "smtp_host",
            "smtp_port",
            "inbox",
            "sent",
            "username",
            "password",
        }
        if set(values) - fields:
            raise ValueError("Unknown mail setting")
        credentials = {key: str(values.get(key, "")) for key in ("username", "password")}
        if not credentials["username"] or not 1 <= len(credentials["password"]) <= 8192:
            raise ValueError("Enter an account name and app password in this private form")
        if len(credentials["username"]) > 500 or any(c in credentials["username"] for c in "\r\n"):
            raise ValueError("Invalid mail account name")
        config = {
            key: str(values.get(key, default))
            for key, default in {
                "label": "Mail",
                "imap_host": "",
                "smtp_host": "",
                "inbox": "INBOX",
                "sent": "",
            }.items()
        }
        if any(len(value) > 300 or any(ord(c) < 32 for c in value) for value in config.values()):
            raise ValueError("Invalid mail account settings")
        for key in ("imap_host", "smtp_host"):
            if (key == "imap_host" or config[key]) and not re.fullmatch(r"[a-zA-Z0-9.:-]+", config[key]):
                raise ValueError("Enter a TLS mail hostname, without URL path or credentials")
        config.update(
            imap_port=int(values.get("imap_port", 993)), smtp_port=int(values.get("smtp_port", 465))
        )
        if any(not 1 <= config[key] <= 65535 for key in ("imap_port", "smtp_port")):
            raise ValueError("Invalid TLS mail port")
        try:
            await asyncio.to_thread(self.validate, config, credentials)
        except Exception:
            raise ValueError(
                "Could not verify this TLS mail account. Check hostnames, mailbox names and the provider app password. SMTP must support implicit TLS, usually port 465."
            ) from None
        name = "email_" + uid()[:12]
        self.runtime.vault.put("mail:" + name, json.dumps(credentials))
        accounts = self.listing()
        accounts[name] = config
        self.store.set_preference("mail_accounts", accounts)
        await self.runtime.tools.refresh()
        return {"id": name}

    async def disconnect(self, name):
        disabled = set(self.store.preference("disabled_connectors", []))
        disabled.add(name)
        self.store.set_preference("disabled_connectors", sorted(disabled))
        self.runtime.attention.forget_connector(name)
        self.store.execute("DELETE FROM native_mail_cursors WHERE account=?", (name,))
        accounts = self.listing()
        accounts.pop(name, None)
        self.store.set_preference("mail_accounts", accounts)
        self.runtime.vault.remove("mail:" + name)
        await self.runtime.tools.refresh()

    def read_batch(
        self, config, credentials, alias, previous=None, limit=50, only_uid=None, expected_validity=None
    ):
        client = self.connection(config, credentials)
        try:
            if alias not in {"inbox", "sent"} or not config.get(alias):
                raise ValueError("This mailbox is not connected")
            if client.select(mailbox(config[alias]), readonly=True)[0] != "OK":
                raise ValueError("Mailbox unavailable")
            raw_validity = client.response("UIDVALIDITY")[1]
            if not raw_validity or not raw_validity[0]:
                raise ValueError("Server did not identify mailbox UID validity")
            validity = raw_validity[0].decode("ascii")
            if expected_validity and validity != expected_validity:
                raise ValueError("Mailbox changed; list messages again before reading")
            cursor = int(previous.get("uid", 0)) if previous and previous.get("validity") == validity else 0
            if only_uid:
                numbers = [only_uid]
            else:
                status, data = (
                    client.uid("search", None, "UID", f"{cursor + 1}:*")
                    if cursor
                    else client.uid("search", None, "ALL")
                )
                if status != "OK":
                    raise ValueError("Could not search mailbox")
                numbers = sorted(int(x) for x in (data[0] or b"").split() if x.isdigit() and int(x) > cursor)
                numbers = numbers[:limit] if cursor else numbers[-limit:]
            records = []
            for number in numbers:
                status, data = client.uid("fetch", str(number), f"(UID FLAGS BODY.PEEK[]<0.{LIMIT}>)")
                if status != "OK":
                    raise ValueError("Could not fetch mail")
                pieces = [item for item in data if isinstance(item, tuple)]
                if not pieces:
                    continue
                metadata, raw = pieces[0]
                if len(raw) > LIMIT:
                    raise ValueError("Mail response exceeded its bound")
                records.append(record(raw, metadata, alias, validity, number))
            return records, {"validity": validity, "uid": max([cursor, *numbers])}
        finally:
            client.logout()

    async def poll(self):
        now = time.time()
        for name, config in list(self.listing().items()):
            if not self.runtime.tools.enabled(name):
                continue
            state = self.store.rows("SELECT next_poll FROM connector_cursors WHERE connector=?", (name,))
            if state and state[0]["next_poll"] > now:
                continue
            try:
                credentials = self.credentials(name)
                for alias in ("inbox", "sent"):
                    if not config.get(alias):
                        continue
                    saved = self.store.rows(
                        "SELECT value FROM native_mail_cursors WHERE account=? AND mailbox=?", (name, alias)
                    )
                    previous = json.loads(saved[0]["value"]) if saved else None
                    records, cursor = await asyncio.to_thread(
                        self.read_batch, config, credentials, alias, previous
                    )
                    if name not in self.listing() or not self.runtime.tools.enabled(name):
                        break
                    self.runtime.attention.events.ingest(
                        name, records, "mail.sent" if alias == "sent" else "mail.received"
                    )
                    self.store.execute(
                        "INSERT OR REPLACE INTO native_mail_cursors VALUES(?,?,?)",
                        (name, alias, json.dumps(cursor)),
                    )
                if name not in self.listing() or not self.runtime.tools.enabled(name):
                    continue
                cadence = self.runtime.attention.preferences()["connector_cadence"].get(
                    name, self.runtime.attention.preferences()["poll_seconds"]
                )
                self.store.execute(
                    "INSERT INTO connector_cursors VALUES(?,NULL,?,'') ON CONFLICT(connector) DO UPDATE SET next_poll=excluded.next_poll,error=''",
                    (name, now + cadence),
                )
            except Exception:
                self.store.execute(
                    "INSERT INTO connector_cursors VALUES(?,NULL,?,?) ON CONFLICT(connector) DO UPDATE SET next_poll=excluded.next_poll,error=excluded.error",
                    (name, now + 60, "Mail polling failed; check the account and app password"),
                )

    def send(self, config, credentials, arguments):
        for key in ("to", "subject", "in_reply_to"):
            if any(c in str(arguments.get(key, "")) for c in "\r\n"):
                raise ValueError("Mail headers cannot contain newlines")
        recipients = getaddresses([arguments["to"]])
        if len(recipients) != 1 or "@" not in recipients[0][1]:
            raise ValueError("Use one explicit recipient")
        message = EmailMessage()
        message["From"] = credentials["username"]
        message["To"] = arguments["to"]
        message["Subject"] = arguments["subject"]
        message["Message-ID"] = make_msgid()
        if arguments.get("in_reply_to"):
            message["In-Reply-To"] = arguments["in_reply_to"]
        message.set_content(arguments["body"])
        with smtplib.SMTP_SSL(
            config["smtp_host"], config["smtp_port"], context=ssl.create_default_context(), timeout=20
        ) as sender:
            sender.login(credentials["username"], credentials["password"])
            rejected = sender.send_message(message)
            if rejected:
                raise ValueError("SMTP rejected the recipient")
        return {"accepted_by_smtp": True, "message_id": message["Message-ID"], "to": arguments["to"]}

    def tools(self):
        from .tools import Tool, schema

        tools = []
        for name, config in self.listing().items():
            if not self.runtime.tools.enabled(name):
                continue

            async def listing(arguments, task, name=name, config=config):
                alias = arguments.get("mailbox", "inbox")
                records, _ = await asyncio.to_thread(
                    self.read_batch, config, self.credentials(name), alias, None, 50
                )
                query = arguments.get("query", "").lower()
                return {
                    "messages": [
                        row for row in records if query in (row["subject"] + " " + row["text"]).lower()
                    ][-arguments.get("limit", 10) :],
                    "note": "Bounded to the latest 50 messages in this connected mailbox",
                }

            async def reading(arguments, task, name=name, config=config):
                records, _ = await asyncio.to_thread(
                    self.read_batch,
                    config,
                    self.credentials(name),
                    arguments["mailbox"],
                    None,
                    1,
                    arguments["uid"],
                    arguments["uidvalidity"],
                )
                return {"messages": records}

            async def sending(arguments, task, name=name, config=config):
                credentials = self.credentials(name)
                return await asyncio.to_thread(self.send, config, credentials, arguments)

            prefix = name + "_"
            tools.append(
                Tool(
                    prefix + "list",
                    f"Read recent mail in {config['label']}. Query filters the latest 50 messages; results contain stable UID references.",
                    schema(
                        {
                            "mailbox": {"enum": ["inbox", "sent"]},
                            "query": {"type": "string", "maxLength": 200},
                            "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                        },
                        [],
                    ),
                    listing,
                    False,
                    name,
                    "list_mail",
                    "read",
                )
            )
            tools.append(
                Tool(
                    prefix + "read",
                    f"Read one message in {config['label']} using the mailbox/uid/uidvalidity from list_mail.",
                    schema(
                        {
                            "mailbox": {"enum": ["inbox", "sent"]},
                            "uid": {"type": "integer", "minimum": 1},
                            "uidvalidity": {"type": "string", "maxLength": 50},
                        }
                    ),
                    reading,
                    False,
                    name,
                    "read_mail",
                    "read",
                )
            )
            if config["smtp_host"]:
                tools.append(
                    Tool(
                        prefix + "send",
                        f"Send an email from {config['label']}. The exact recipient, subject and body require approval.",
                        schema(
                            {
                                "to": {"type": "string", "maxLength": 500},
                                "subject": {"type": "string", "maxLength": 300},
                                "body": {"type": "string", "maxLength": 40000},
                                "in_reply_to": {"type": "string", "maxLength": 500},
                            },
                            ["to", "subject", "body"],
                        ),
                        sending,
                        True,
                        name,
                        "send_email",
                        "consequential",
                    )
                )
        return tools
