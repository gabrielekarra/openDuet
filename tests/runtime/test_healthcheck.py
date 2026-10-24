"""Exercise real loopback responses, failure status, proxy isolation and timeout."""

from contextlib import contextmanager
from socketserver import BaseRequestHandler, TCPServer
from threading import Event, Thread

import pytest

from openduet.healthcheck import healthy


@contextmanager
def endpoint(response, delay=0):
    requests = []

    class Handler(BaseRequestHandler):
        def handle(self):
            requests.append(self.request.recv(4096))
            if delay:
                Event().wait(delay)
            self.request.sendall(response)

    with TCPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        try:
            yield server.server_address[1], requests
        finally:
            server.shutdown()
            thread.join(timeout=1)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (b"HTTP/1.1 200 OK", True),
        (b"HTTP/1.0 200 OK", True),
        (b"HTTP/1.1 302 Found", False),
        (b"HTTP/1.1 503 Unavailable", False),
        (b"not an HTTP response", False),
    ],
)
def test_local_health_requires_http_200_despite_outbound_proxy(monkeypatch, status, expected):
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.setenv(key, "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")
    monkeypatch.setenv("no_proxy", "")
    with endpoint(status + b"\r\nContent-Length: 0\r\n\r\n") as (port, requests):
        assert healthy(port) is expected
        assert requests == [b"GET /health HTTP/1.0\r\nHost: localhost\r\n\r\n"]


def test_stalled_service_fails_without_waiting_for_its_response():
    with endpoint(b"HTTP/1.1 200 OK\r\n\r\n", delay=0.2) as (port, _):
        assert healthy(port, timeout=0.03) is False


def test_closed_service_and_invalid_port_fail():
    with TCPServer(("127.0.0.1", 0), BaseRequestHandler) as server:
        port = server.server_address[1]
    assert healthy(port) is False
    assert healthy(0) is False
    assert healthy(65536) is False
