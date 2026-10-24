"""A real loopback HTTP process with disposable service-shaped records."""

import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory


@contextmanager
def loopback_server(effect_file=""):
    with TemporaryDirectory(prefix="openduet-mcp-") as directory:
        port = Path(directory) / "port"
        server = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).with_name("mcp_http_server.py")),
                str(port),
                str(effect_file),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.monotonic() + 10
            while not port.exists():
                if server.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("Disposable MCP server did not start")
                time.sleep(0.05)
            yield "http://127.0.0.1:" + port.read_text()
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
