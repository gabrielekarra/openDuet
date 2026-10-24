"""Disposable loopback fixture: no user services, real credentials or app effects."""
import base64
import hashlib
import http.server
import json
import queue
import sys
import socketserver
import threading
import urllib.parse
from pathlib import Path

from contract_protocol import dispatch

streams = {}
authorizations = {}

class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *_): pass
    @property
    def origin(self): return f"http://127.0.0.1:{self.server.server_port}"
    def response(self, status, value=None, headers=None):
        body = b"" if value is None else json.dumps(value).encode()
        self.send_response(status)
        if value is not None: self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for key, val in (headers or {}).items(): self.send_header(key, val)
        self.end_headers()
        if body: self.wfile.write(body)
    def sse(self, session=False):
        self.send_response(200); self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        if session: self.send_header("MCP-Session-Id", "fixture-session")
        self.end_headers()
    def event(self, value, event="message"):
        data = value if isinstance(value, str) else json.dumps(value)
        self.wfile.write(f"event: {event}\ndata: {data}\n\n".encode()); self.wfile.flush()
    def do_GET(self):
        url = urllib.parse.urlsplit(self.path); path = url.path
        if path in ("/legacy", "/fallback"):
            self.sse(); channel = queue.Queue(); key = str(id(channel)); streams[key] = channel
            self.event("/legacy/messages?session=" + key, "endpoint")
            try:
                while True: self.event(channel.get(timeout=60))
            except (BrokenPipeError, ConnectionResetError, queue.Empty): pass
            finally: streams.pop(key, None)
            return
        if path.startswith("/.well-known/oauth-protected-resource"):
            return self.response(200, {"resource": self.origin + "/oauth/mcp", "authorization_servers": [self.origin], "scopes_supported": ["tools"]})
        if path == "/.well-known/oauth-authorization-server":
            return self.response(200, {"issuer": self.origin, "authorization_endpoint": self.origin + "/authorize", "token_endpoint": self.origin + "/token",
                "registration_endpoint": self.origin + "/register", "revocation_endpoint": self.origin + "/revoke", "token_endpoint_auth_methods_supported": ["none", "client_secret_post"], "code_challenge_methods_supported": ["S256"]})
        if path == "/authorize":
            query = dict(urllib.parse.parse_qsl(url.query)); authorizations["fixture-code"] = query
            callback = query["redirect_uri"] + "?" + urllib.parse.urlencode({"state": query["state"], "code": "fixture-code"})
            return self.response(302, headers={"Location": callback})
        if path == "/oauth/mcp": return self.response(401, headers={"WWW-Authenticate": f'Bearer resource_metadata="{self.origin}/.well-known/oauth-protected-resource/oauth/mcp", scope="tools"'})
        return self.response(405)
    def do_POST(self):
        url = urllib.parse.urlsplit(self.path); path = url.path
        size = int(self.headers.get("Content-Length", 0))
        if size > 1_000_000: return self.response(413)
        body = self.rfile.read(size)
        if path == "/register": return self.response(201, {"client_id": "fixture-public", "token_endpoint_auth_method": "none"})
        if path == "/revoke": return self.response(200, {})
        if path == "/token":
            form = dict(urllib.parse.parse_qsl(body.decode()))
            if form.get("client_id") == "fixture-confidential" and form.get("client_secret") != "fixture-private-client": return self.response(401)
            if form.get("resource") != self.origin + "/oauth/mcp": return self.response(400)
            if form.get("grant_type") == "authorization_code":
                query = authorizations.get(form.get("code"), {})
                challenge = base64.urlsafe_b64encode(hashlib.sha256(form.get("code_verifier", "").encode()).digest()).decode().rstrip("=")
                if query.get("code_challenge") != challenge or form.get("redirect_uri") != query.get("redirect_uri"): return self.response(400)
                return self.response(200, {"token_type": "Bearer", "access_token": "fixture-first", "refresh_token": "fixture-refresh", "expires_in": 1})
            if form.get("grant_type") == "refresh_token" and form.get("refresh_token") == "fixture-refresh":
                return self.response(200, {"token_type": "Bearer", "access_token": "fixture-renewed", "expires_in": 3600})
            return self.response(400)
        if path == "/fallback": return self.response(405)
        if path == "/redirect": return self.response(307, headers={"Location": self.origin + "/mcp"})
        if path == "/unauthorized": return self.response(401)
        if path == "/oauth/mcp" and self.headers.get("Authorization") != "Bearer fixture-renewed": return self.response(401)
        value = json.loads(body)
        if "id" not in value: return self.response(202)
        method, args = value["method"], value.get("params", {})
        if path.startswith('/profiles/') and method in {'tools/list', 'tools/call'}:
            service = path.rsplit('/', 1)[-1]
            result = dispatch(service, method, args, sys.argv[2] if len(sys.argv) > 2 else '')
            return self.response(200, {"jsonrpc": "2.0", "id": value["id"], "result": result}, {"MCP-Session-Id": "fixture-session"})
        if method != "initialize" and path not in ("/legacy/messages",) and (self.headers.get("MCP-Session-Id") != "fixture-session" or self.headers.get("MCP-Protocol-Version") != "2025-11-25"):
            return self.response(400)
        if method == "initialize": result = {"protocolVersion": "2025-11-25", "serverInfo": {"name": "Disposable service fixture", "version": "1"}, "capabilities": {"tools": {"listChanged": True}}}
        elif method == "tools/list":
            if not args.get("cursor"): result = {"tools": [{"name": "echo", "description": "Fixture echo", "inputSchema": {"type": "object"}, "annotations": {"readOnlyHint": True}}], "nextCursor": "second"}
            else: result = {"tools": [{"name": "read_events", "inputSchema": {"type": "object", "properties": {"service": {"type": "string"}, "cursor": {"type": "string"}, "force_error": {"type": "boolean"}}, "required": ["service"], "additionalProperties": False}, "annotations": {"readOnlyHint": True}}, {"name": "delayed", "inputSchema": {"type": "object"}}]}
        elif method == "tools/call":
            if args["name"] == "delayed": threading.Event().wait(5)
            result = {"content": [{"type": "text", "text": "fixture-ok"}], "structuredContent": args.get("arguments", {})}
            if args["name"] == "read_events":
                arguments = args.get("arguments", {})
                page = bool(arguments.get("cursor"))
                service = arguments["service"]
                if arguments.get("force_error"):
                    result = {"isError": True, "content": [{"type": "text", "text": "Disposable provider error"}]}
                else:
                    records = {
                        "gmail": {"messages": [{"id": "mail-1", "threadId": "thread-1", "labelIds": ["INBOX"] if page else ["INBOX", "UNREAD"], "payload": {"headers": [{"name": "Subject", "value": "Review proposal"}, {"name": "From", "value": "client@example.test"}], "mimeType": "text/plain", "body": {"data": "UGxlYXNlIHJldmlldyB0aGUgcHJvcG9zYWw"}}}], **({} if page else {"nextPageToken": "page-2"})},
                        "google-calendar": {"items": [{"id": "meeting-1", "summary": "Planning", "start": {"dateTime": "2026-10-24T11:00:00Z" if page else "2026-10-24T10:00:00Z"}, "end": {"dateTime": "2026-10-24T12:00:00Z"}, "htmlLink": "https://calendar.google.com/event?eid=fixture"}], **({} if page else {"nextPageToken": "page-2"})},
                        "slack": {"messages": [{"ts": "1792800000.000001" if page else "1792800000.000000", "text": "Please review", "user": "U1"}], "response_metadata": {"next_cursor": "" if page else "page-2"}},
                        "stripe": {"data": [{"id": "in-2" if page else "in-1", "object": "invoice", "number": "TEST-2" if page else "TEST-1", "amount_due": 12345, "currency": "eur", "customer_email": "client@example.test", "hosted_invoice_url": "https://invoice.stripe.com/i/fixture"}], "has_more": not page},
                    }
                    result = {"content": [], "structuredContent": records[service]}
        else: return self.response(400)
        reply = {"jsonrpc": "2.0", "id": value["id"], "result": result}
        if path == "/legacy/messages":
            streams[dict(urllib.parse.parse_qsl(url.query))["session"]].put(reply)
            return self.response(202)
        if path == "/stream":
            self.sse(session=True); self.event(reply); self.close_connection = True; return
        return self.response(200, reply, {"MCP-Session-Id": "fixture-session"})

class FixtureServer(http.server.ThreadingHTTPServer):
    def server_bind(self):
        # HTTPServer otherwise performs a reverse-DNS lookup at startup. This
        # disposable loopback server does not need DNS or an external network.
        socketserver.TCPServer.server_bind(self)
        self.server_name = "localhost"
        self.server_port = self.server_address[1]

if sys.argv[1] == "--stdio-profile":
    for line in sys.stdin:
        value = json.loads(line)
        if "id" not in value:
            continue
        if value['method'] == 'initialize':
            result = {"protocolVersion": "2025-11-25", "serverInfo": {"name": "provider contract fixture", "version": "1"}, "capabilities": {"tools": {}}}
        else:
            result = dispatch(sys.argv[2], value['method'], value.get('params', {}), sys.argv[3] if len(sys.argv) > 3 else '')
        print(json.dumps({"jsonrpc": "2.0", "id": value["id"], "result": result}), flush=True)
    sys.exit(0)

if sys.argv[1] == "--stdio":
    for line in sys.stdin:
        value = json.loads(line)
        if "id" not in value:
            continue
        method = value["method"]
        if method == "initialize": result = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}}}
        elif method == "tools/list": result = {"tools": [{"name": "echo", "inputSchema": {"type": "object"}}]}
        else: result = {"structuredContent": value.get("params", {}).get("arguments", {})}
        print(json.dumps({"jsonrpc": "2.0", "id": value["id"], "result": result}), flush=True)
    sys.exit(0)

print("Loopback fixture binding", file=sys.stderr, flush=True)
server = FixtureServer(("127.0.0.1", 0), Handler)
Path(sys.argv[1]).write_text(str(server.server_port))
print("Loopback fixture ready", file=sys.stderr, flush=True)
server.serve_forever()
