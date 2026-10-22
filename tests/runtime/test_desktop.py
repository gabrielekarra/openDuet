import asyncio
import json
import socket
import socketserver
import threading
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from openduet.config import ComputerConfig, Config
from openduet.runtime import Runtime
from openduet.server import create_app
from openduet.store import Store


@contextmanager
def computer():
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            self.server.connections += 1
            self.request.sendall(b"RFB 003.008\n")
            while data := self.request.recv(65536):
                self.request.sendall(data)

    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    server.connections = 0
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENDUET_TOKEN", "desktop-test-token-for-local-fixtures")
    return Config(data_dir=tmp_path)


def test_remote_desktop_auth_origin_and_bytes_relay(config):
    with computer() as target:
        config.computers["host"] = ComputerConfig(
            port=target.server_address[1], screen_lock=str(config.data_dir / "screen.lock")
        )
        app = create_app(config, start_worker=False)
        with TestClient(app) as client:
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect(
                    "/api/computers/host/desktop", headers={"Origin": "http://testserver"}
                ):
                    pass
            assert client.post("/api/login", json={"token": config.token()}).status_code == 200
            for headers in [{}, {"Origin": "https://attacker.example"}]:
                with pytest.raises(WebSocketDisconnect):
                    with client.websocket_connect("/api/computers/host/desktop", headers=headers):
                        pass
            assert target.connections == 0
            with client.websocket_connect(
                "/api/computers/host/desktop", headers={"Origin": "http://testserver"}
            ) as ws:
                assert ws.receive_bytes() == b"RFB 003.008\n"
                assert client.get("/api/state").json()["remote_desktop_active"]
                ws.send_bytes(b"private-desktop-input")
                assert ws.receive_bytes() == b"private-desktop-input"
                assert (config.data_dir / "screen.lock.remote").is_file()
                with pytest.raises(WebSocketDisconnect):
                    with client.websocket_connect(
                        "/api/computers/host/desktop", headers={"Origin": "http://testserver"}
                    ):
                        pass
                assert app.state.store.rows("SELECT * FROM messages") == []
            assert not (config.data_dir / "screen.lock.remote").exists()
            assert not app.state.runtime.desktop.active
            events = app.state.store.rows("SELECT * FROM events")
            assert "private-desktop-input" not in json.dumps(events)
            assert target.connections == 1


def test_missing_and_disabled_computers_do_not_connect(config):
    config.computers["disabled"] = ComputerConfig(enabled=False)
    with TestClient(create_app(config, start_worker=False)) as client:
        client.post("/api/login", json={"token": config.token()})
        for key in ["unknown", "disabled"]:
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect(
                    f"/api/computers/{key}/desktop", headers={"Origin": "http://testserver"}
                ):
                    pass


def test_unavailable_computer_releases_native_handoff(config):
    # Reserve a local port without listening so connection refusal is deterministic.
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        config.computers["host"] = ComputerConfig(
            port=reserved.getsockname()[1], screen_lock=str(config.data_dir / "screen.lock")
        )
        app = create_app(config, start_worker=False)
        with TestClient(app) as client:
            client.post("/api/login", json={"token": config.token()})
            with pytest.raises(WebSocketDisconnect) as ended:
                with client.websocket_connect(
                    "/api/computers/host/desktop", headers={"Origin": "http://testserver"}
                ):
                    pass
            assert ended.value.code == 1011
            assert not app.state.runtime.desktop.active
            assert not (config.data_dir / "screen.lock.remote").exists()


def test_logout_disconnects_live_desktop(config):
    with computer() as target:
        config.computers["host"] = ComputerConfig(port=target.server_address[1])
        with TestClient(create_app(config, start_worker=False)) as client:
            client.post("/api/login", json={"token": config.token()})
            with client.websocket_connect(
                "/api/computers/host/desktop", headers={"Origin": "http://testserver"}
            ) as ws:
                ws.receive_bytes()
                client.post("/api/logout")
                with pytest.raises(WebSocketDisconnect):
                    ws.receive_bytes()


def test_session_duration_closes_live_desktop(config):
    config.remote_session_seconds = 0.05
    with computer() as target:
        config.computers["host"] = ComputerConfig(port=target.server_address[1])
        with TestClient(create_app(config, start_worker=False)) as client:
            client.post("/api/login", json={"token": config.token()})
            with client.websocket_connect(
                "/api/computers/host/desktop", headers={"Origin": "http://testserver"}
            ) as ws:
                ws.receive_bytes()
                with pytest.raises(WebSocketDisconnect) as ended:
                    ws.receive_bytes()
                assert ended.value.code == 1008


async def test_native_screen_lock_is_released_before_remote_enters(config):
    import fcntl

    lock = config.data_dir / "screen.lock"
    config.data_dir.mkdir(exist_ok=True)
    native = lock.open("w")
    fcntl.flock(native, fcntl.LOCK_EX | fcntl.LOCK_NB)
    runtime = Runtime(config, Store(config.data_dir))
    entered = asyncio.Event()

    async def acquire():
        async with runtime.desktop.screen_lease(ComputerConfig(screen_lock=str(lock))):
            entered.set()
            other = lock.open("w")
            try:
                with pytest.raises(BlockingIOError):
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                other.close()

    task = asyncio.create_task(acquire())
    for _ in range(100):
        if lock.with_name("screen.lock.remote").exists():
            break
        await asyncio.sleep(0.01)
    assert not entered.is_set()
    marker = json.loads(lock.with_name("screen.lock.remote").read_text())
    assert marker["expires"] > 0
    native.close()
    await asyncio.wait_for(task, timeout=2)
    assert entered.is_set()
    assert not lock.with_name("screen.lock.remote").exists()


async def test_worker_does_not_start_jobs_during_human_session(config):
    runtime = Runtime(config, Store(config.data_dir))
    runtime.desktop.sessions["host"] = object()
    ident = runtime.store.new_task("main", "A queued task", "local")
    worker = asyncio.create_task(runtime.worker())
    await asyncio.sleep(0.1)
    assert runtime.store.task(ident)["status"] == "queued"
    runtime.stop.set()
    await asyncio.wait_for(worker, timeout=1)


def test_insecure_remote_vnc_requires_a_tunnel():
    with pytest.raises(ValueError, match="requires TLS"):
        ComputerConfig(host="192.168.1.5")
    assert ComputerConfig(host="192.168.1.5", tls=True).tls
