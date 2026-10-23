"""Actual TLS IMAP/SMTP loopback fixtures; no external accounts or disabled verification."""

import asyncio
import email.policy
import ipaddress
import json
import ssl
from datetime import UTC, datetime, timedelta
from email.parser import BytesParser

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from openduet.config import Config
from openduet.mail_accounts import mailbox
from openduet.runtime import Runtime
from openduet.store import Store


@pytest.fixture
async def mail_server(tmp_path, monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "OpenDuet TLS fixture")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    cert = tmp_path / "fixture.pem"
    cert.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    private = tmp_path / "fixture.key"
    private.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
    )
    private.chmod(0o600)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, private)
    original = ssl.create_default_context

    def trusted(*args, **kwargs):
        ctx = original(cafile=str(cert))
        assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
        return ctx

    monkeypatch.setattr(ssl, "create_default_context", trusted)
    sent = []
    commands = []

    async def imap(reader, writer):
        writer.write(b"* OK OpenDuet fixture ready\r\n")
        await writer.drain()
        selected = "INBOX"
        try:
            while raw := await reader.readline():
                line = raw.decode().strip()
                parts = line.split(" ", 2)
                tag, command = parts[:2]
                args = parts[2] if len(parts) > 2 else ""
                commands.append(command)
                if command == "CAPABILITY":
                    response = f"* CAPABILITY IMAP4rev1\r\n{tag} OK done\r\n"
                elif command == "LOGIN":
                    response = f"{tag} OK login\r\n"
                elif command == "EXAMINE":
                    selected = args
                    response = f"* FLAGS (\\Seen)\r\n* 1 EXISTS\r\n* OK [UIDVALIDITY 100] stable mailbox\r\n{tag} OK [READ-ONLY] examined\r\n"
                elif command == "UID" and args.startswith("SEARCH"):
                    response = f"* SEARCH 1\r\n{tag} OK search\r\n"
                elif command == "UID" and args.startswith("FETCH"):
                    assert "BODY.PEEK[]" in args
                    sender = "owner@example.test" if "Sent" in selected else "client@example.test"
                    body = (
                        "I will send the proposal by Friday."
                        if "Sent" in selected
                        else "Please check the proposal.\r\n> Quoted older request"
                    )
                    message = f"From: {sender}\r\nTo: owner@example.test\r\nSubject: Project proposal\r\nDate: Thu, 22 Oct 2026 09:00:00 +0000\r\nMessage-ID: <fixture-{sender}@example.test>\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{body}\r\n".encode()
                    writer.write(
                        f"* 1 FETCH (UID 1 FLAGS () BODY[] {{{len(message)}}}\r\n".encode()
                        + message
                        + f")\r\n{tag} OK fetched\r\n".encode()
                    )
                    await writer.drain()
                    continue
                elif command == "LOGOUT":
                    writer.write(f"* BYE\r\n{tag} OK logout\r\n".encode())
                    await writer.drain()
                    break
                else:
                    response = f"{tag} BAD unknown\r\n"
                writer.write(response.encode())
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def smtp(reader, writer):
        writer.write(b"220 fixture\r\n")
        await writer.drain()
        try:
            while line := await reader.readline():
                command = line.decode().split()[0].upper()
                if command == "EHLO":
                    reply = b"250-fixture\r\n250-AUTH PLAIN\r\n250 SIZE 100000\r\n"
                elif command == "AUTH":
                    reply = b"235 Authenticated\r\n"
                elif command in {"MAIL", "RCPT", "NOOP", "RSET"}:
                    reply = b"250 OK\r\n"
                elif command == "DATA":
                    writer.write(b"354 Send data\r\n")
                    await writer.drain()
                    body = bytearray()
                    while chunk := await reader.readline():
                        if chunk == b".\r\n":
                            break
                        body.extend(chunk)
                    sent.append(BytesParser(policy=email.policy.default).parsebytes(bytes(body)))
                    reply = b"250 accepted\r\n"
                elif command == "QUIT":
                    writer.write(b"221 bye\r\n")
                    await writer.drain()
                    break
                else:
                    reply = b"500 unknown\r\n"
                writer.write(reply)
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    imap_server = await asyncio.start_server(imap, "127.0.0.1", 0, ssl=context)
    smtp_server = await asyncio.start_server(smtp, "127.0.0.1", 0, ssl=context)
    yield {
        "imap": imap_server.sockets[0].getsockname()[1],
        "smtp": smtp_server.sockets[0].getsockname()[1],
        "sent": sent,
        "commands": commands,
    }
    imap_server.close()
    smtp_server.close()
    await imap_server.wait_closed()
    await smtp_server.wait_closed()


async def test_direct_mail_real_tls_poll_dedup_reviewed_send_and_disconnect(tmp_path, mail_server):
    runtime = Runtime(Config(data_dir=tmp_path / "workspace"), Store(tmp_path / "workspace"))
    account = await runtime.mail.add(
        {
            "label": "Fixture mailbox",
            "username": "owner@example.test",
            "password": "fixture-app-password-not-a-real-secret",
            "imap_host": "127.0.0.1",
            "imap_port": mail_server["imap"],
            "smtp_host": "127.0.0.1",
            "smtp_port": mail_server["smtp"],
            "inbox": "INBOX",
            "sent": "Sent",
        }
    )
    name = account["id"]
    assert mail_server["sent"] == []
    assert "fixture-app-password" not in json.dumps(runtime.store.preference("mail_accounts", {}))
    await runtime.mail.poll()
    assert len(runtime.store.rows("SELECT * FROM connector_events")) == 2
    assert {row["kind"] for row in runtime.store.rows("SELECT kind FROM connector_events")} == {
        "mail.received",
        "mail.sent",
    }
    runtime.store.execute("UPDATE connector_cursors SET next_poll=0")
    await runtime.mail.poll()
    assert len(runtime.store.rows("SELECT * FROM connector_events")) == 2
    assert "SELECT" not in mail_server["commands"] and "EXAMINE" in mail_server["commands"]
    tool = name + "_send"
    task = runtime.store.new_task("main", "Send the reviewed reply", "local")
    payload = {
        "to": "client@example.test",
        "subject": "Reviewed proposal",
        "body": "This exact text was approved.",
    }
    history = [
        {
            "role": "assistant",
            "tool_calls": [{"id": "send", "function": {"name": tool, "arguments": json.dumps(payload)}}],
        }
    ]
    runtime.checkpoint(task, history, 0)
    assert not await runtime.process_calls(runtime.store.task(task), history)
    assert mail_server["sent"] == []
    call = runtime.store.rows("SELECT * FROM calls")[0]
    runtime.approvals.decide(call["id"], "approve")
    assert await runtime.process_calls(runtime.store.task(task), history)
    assert len(mail_server["sent"]) == 1
    actual = mail_server["sent"][0]
    assert actual["To"] == payload["to"] and actual["Subject"] == payload["subject"]
    assert actual.get_content().strip() == payload["body"]
    with pytest.raises(ValueError):
        runtime.approvals.decide(call["id"], "approve")
    await runtime.mail.disconnect(name)
    with pytest.raises(ValueError):
        runtime.tools.get(tool, payload)
    assert runtime.store.rows("SELECT * FROM connector_events") == []
    assert name not in runtime.mail.listing()
    await runtime.close()


def test_mailbox_names_are_quoted_and_unicode_encoded():
    assert mailbox("[Gmail]/Sent Mail") == '"[Gmail]/Sent Mail"'
    assert mailbox("Foo & Bar") == '"Foo &- Bar"'
    assert mailbox("Posta inviata") == '"Posta inviata"'
    with pytest.raises(ValueError):
        mailbox("INBOX\r\nLOGOUT")
