"""Authenticated RFB relay and exclusive human handoff. Pixels never enter model context."""

from __future__ import annotations

import asyncio
import json
import os
import ssl
import time
from contextlib import asynccontextmanager
from pathlib import Path

from anyio import BrokenResourceError, CancelScope, ClosedResourceError
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from .store import uid


class DesktopBusy(ValueError):
    pass


class DesktopRelay:
    def __init__(self, runtime):
        self.runtime = runtime
        self.sessions: dict[str, WebSocket] = {}

    @property
    def active(self):
        return bool(self.sessions)

    async def close(self):
        for socket in list(self.sessions.values()):
            try:
                await socket.close(code=1001)
            except (RuntimeError, WebSocketDisconnect, ClosedResourceError, BrokenResourceError, OSError):
                pass

    @asynccontextmanager
    async def screen_lease(self, config):
        if not config.screen_lock:
            yield
            return
        import fcntl

        ident = uid()
        lock = Path(config.screen_lock).expanduser()
        lock.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        marker = lock.with_name(lock.name + ".remote")
        request_fd = os.open(str(marker) + ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(request_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(request_fd)
            raise DesktopBusy("This computer already has a remote session") from None
        descriptor = None
        heartbeat = None
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)

            def renew():
                tmp = marker.with_name(marker.name + "." + ident)
                fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, "w") as file:
                    json.dump({"id": ident, "expires": time.time() + 15}, file)
                os.replace(tmp, marker)

            async def keep_alive():
                while True:
                    renew()
                    await asyncio.sleep(3)

            renew()
            heartbeat = asyncio.create_task(keep_alive())
            until = time.monotonic() + 20
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= until:
                        raise DesktopBusy("OpenDuet is finishing a desktop action. Stop that task and retry")
                    await asyncio.sleep(0.1)
            yield
        finally:
            if heartbeat:
                heartbeat.cancel()
            # Release OS resources before any await: ASGI cancellation can recur during teardown.
            try:
                marker.unlink(missing_ok=True)
            finally:
                if descriptor is not None:
                    os.close(descriptor)
                os.close(request_fd)
            if heartbeat:
                with CancelScope(shield=True):
                    await asyncio.gather(heartbeat, return_exceptions=True)

    async def connect(self, socket, key, config, valid_session):
        if self.active:
            await socket.close(code=1008, reason="A remote desktop session is already open")
            return
        # Register before awaiting anything, excluding simultaneous connections.
        self.sessions[key] = socket
        writer = None
        try:
            if self.runtime.current:
                ident, task = self.runtime.current
                self.runtime.cancel(ident)
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=15)
                except asyncio.CancelledError:
                    pass
                except TimeoutError:
                    raise DesktopBusy("An agent action is still settling; retry shortly") from None
            async with self.screen_lease(config):
                context = ssl.create_default_context(cafile=config.ca_file or None) if config.tls else None
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(config.host, config.port, ssl=context), timeout=8
                )
                await socket.accept(
                    subprotocol="binary" if "binary" in socket.scope.get("subprotocols", []) else None
                )
                self.runtime.store.event("desktop_connected", f"Remote desktop opened: {config.name}")

                async def from_computer():
                    while True:
                        data = await reader.read(65536)
                        if not data:
                            return
                        await socket.send_bytes(data)

                async def to_computer():
                    while True:
                        event = await socket.receive()
                        if event["type"] == "websocket.disconnect":
                            return
                        data = event.get("bytes")
                        if data is None or len(data) > 1_048_576:
                            await socket.close(code=1009, reason="Binary desktop frames only; maximum 1 MB")
                            return
                        writer.write(data)
                        await writer.drain()

                async def expiry():
                    started = time.monotonic()
                    while (
                        valid_session()
                        and time.monotonic() - started < self.runtime.config.remote_session_seconds
                    ):
                        await asyncio.sleep(1)
                    await socket.close(code=1008, reason="Remote desktop session expired")

                tasks = [asyncio.create_task(fn()) for fn in (from_computer, to_computer, expiry)]
                try:
                    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                finally:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
        except DesktopBusy as error:
            await socket.close(code=1013, reason=str(error)[:120])
        except (OSError, TimeoutError, ssl.SSLError, RuntimeError):
            try:
                await socket.close(
                    code=1011, reason="Computer unavailable. Check screen sharing on that computer"
                )
            except RuntimeError:
                pass
        finally:
            self.sessions.pop(key, None)
            self.runtime.store.event("desktop_disconnected", f"Remote desktop closed: {config.name}")
            if writer:
                writer.close()
                try:
                    with CancelScope(shield=True):
                        await asyncio.wait_for(writer.wait_closed(), timeout=2)
                except (OSError, TimeoutError):
                    pass
