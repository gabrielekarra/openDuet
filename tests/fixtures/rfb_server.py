"""Synthetic RFB 3.8 desktop for noVNC tests, never a real host desktop."""

import socketserver
import struct
import threading


class FixtureDesktop(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), RFBHandler)
        self.events = []

    def start(self):
        threading.Thread(target=self.serve_forever, daemon=True).start()
        return self


class RFBHandler(socketserver.BaseRequestHandler):
    def read(self, count):
        result = bytearray()
        while len(result) < count:
            chunk = self.request.recv(count - len(result))
            if not chunk:
                raise EOFError
            result.extend(chunk)
        return bytes(result)

    def handle(self):
        try:
            self.request.sendall(b"RFB 003.008\n")
            self.read(12)
            self.request.sendall(b"\x01\x01")
            self.read(1)
            self.request.sendall(struct.pack("!I", 0))
            self.read(1)
            name = b"OpenDuet synthetic test desktop"
            pixel_format = struct.pack("!BBBBHHHBBBxxx", 32, 24, 0, 1, 255, 255, 255, 16, 8, 0)
            self.request.sendall(
                struct.pack("!HH", 320, 200) + pixel_format + struct.pack("!I", len(name)) + name
            )
            dirty = True
            pending = False

            def update():
                shade = len(self.server.events) % 128
                pixel = bytes((80 + shade, 110, 140, 0))
                rectangle = struct.pack("!HHHHi", 0, 0, 320, 200, 0)
                self.request.sendall(b"\x00\x00\x00\x01" + rectangle + pixel * (320 * 200))

            while True:
                kind = self.read(1)[0]
                if kind == 0:
                    self.read(19)
                elif kind == 2:
                    count = struct.unpack("!xH", self.read(3))[0]
                    self.read(count * 4)
                elif kind == 3:
                    request = self.read(9)
                    pending = True
                    if dirty or request[0] == 0:
                        update()
                        dirty = pending = False
                elif kind == 4:
                    down, keysym = struct.unpack("!BxxI", self.read(7))
                    self.server.events.append({"type": "key", "down": down, "keysym": keysym})
                    dirty = True
                elif kind == 5:
                    mask, x, y = struct.unpack("!BHH", self.read(5))
                    self.server.events.append({"type": "pointer", "mask": mask, "x": x, "y": y})
                    dirty = True
                elif kind == 6:
                    size = struct.unpack("!xxxI", self.read(7))[0]
                    self.read(size)
                elif kind == 248:
                    header = self.read(8)
                    self.read(header[7])
                else:
                    return
                if dirty and pending:
                    update()
                    dirty = pending = False
        except (EOFError, OSError):
            return
