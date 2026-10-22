"""Minimal public-web HTTP/CONNECT proxy; DNS answers are pinned before connecting."""

from __future__ import annotations

import ipaddress
import json
import os
import select
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


def resolve(host, port):
    if port not in {80, 443}:
        raise ValueError("Unsupported port")
    records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    addresses = [record[4][0] for record in records]
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("Private network denied")
    return addresses[0]


class Proxy(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def upstream(self, host, port, *, plain_http=False):
        address = resolve(host, port)
        print(json.dumps({"host": host, "port": port, "allowed": True}), flush=True)
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
        if proxy:
            upstream = urlsplit(proxy)
            connection = socket.create_connection((upstream.hostname, upstream.port or 8080), timeout=20)
            if plain_http:
                # Forward proxies require the absolute target, preserving their own
                # destination policy and identity injection. They must deny private DNS.
                return connection
            connection.sendall(
                f"CONNECT {address}:{port} HTTP/1.1\r\nHost: {address}:{port}\r\n\r\n".encode()
            )
            response = bytearray()
            while b"\r\n\r\n" not in response and len(response) < 8192:
                chunk = connection.recv(1)
                if not chunk:
                    break
                response.extend(chunk)
            if b" 200 " not in response.split(b"\r\n", 1)[0]:
                connection.close()
                raise ValueError("Upstream proxy denied destination")
            return connection
        return socket.create_connection((address, port), timeout=20)

    def relay(self, connection):
        with connection:
            while True:
                readable, _, _ = select.select([self.connection, connection], [], [], 30)
                if not readable:
                    return
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    (connection if source is self.connection else self.connection).sendall(data)

    def do_CONNECT(self):
        try:
            host, port = self.path.rsplit(":", 1)
            connection = self.upstream(host.strip("[]"), int(port))
        except (ValueError, OSError):
            self.send_error(403)
            return
        self.send_response(200, "Connection established")
        self.end_headers()
        self.relay(connection)

    def do_GET(self):
        try:
            url = urlsplit(self.path)
            if url.scheme != "http" or not url.hostname or url.username or url.password:
                raise ValueError("Invalid destination")
            connection = self.upstream(url.hostname, url.port or 80, plain_http=True)
            target = url.path or "/"
            if url.query:
                target += "?" + url.query
            if os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"):
                target = "http://" + url.netloc + target
            headers = {
                key: value
                for key, value in self.headers.items()
                if key.lower() not in {"proxy-authorization", "proxy-connection", "connection"}
            }
            headers["Host"] = url.netloc
            headers["Connection"] = "close"
            connection.sendall(
                (
                    f"{self.command} {target} HTTP/1.1\r\n"
                    + "".join(f"{key}: {value}\r\n" for key, value in headers.items())
                    + "\r\n"
                ).encode()
            )
            length = min(20_000_000, int(self.headers.get("Content-Length", 0)))
            if length:
                connection.sendall(self.rfile.read(length))
            self.relay(connection)
        except (ValueError, OSError):
            self.send_error(403)

    do_POST = do_GET
    do_PUT = do_GET
    do_PATCH = do_GET
    do_DELETE = do_GET
    do_HEAD = do_GET
    do_OPTIONS = do_GET


def main():
    ThreadingHTTPServer(("0.0.0.0", 8890), Proxy).serve_forever()
