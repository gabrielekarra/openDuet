"""Start a real private installation and exercise one-use local sign-in."""

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx

from openduet.installation import local_login_url, setup


def main():
    with tempfile.TemporaryDirectory() as temporary:
        path, config = setup(Path(temporary) / "OpenDuet with spaces")
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        path.write_text(path.read_text().replace("port = 8765", f"port = {port}"))
        config.port = port
        with (Path(temporary) / "server.log").open("wb") as output:
            process = subprocess.Popen(
                [sys.executable, "-m", "openduet", "--config", str(path)],
                stdout=output,
                stderr=output,
                env={**os.environ, "OPENDUET_TOKEN": ""},
            )
            try:
                with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=2) as client:
                    for _ in range(100):
                        try:
                            if client.get("/health").status_code == 200:
                                break
                        except httpx.HTTPError:
                            pass
                        if process.poll() is not None:
                            raise AssertionError("Installed server exited before startup")
                        time.sleep(0.1)
                    else:
                        raise AssertionError("Installed server did not start")
                    assert client.get("/api/state").status_code == 401
                    code = parse_qs(urlsplit(local_login_url(config)).fragment)["setup"][0]
                    assert client.post("/api/local-session", json={"code": code}).status_code == 200
                    assert client.get("/api/state").status_code == 200
                    assert client.post("/api/local-session", json={"code": code}).status_code == 401
                    product = client.get("/api/product").json()
                    assert product["readiness"]["model"]["tested"] is False
                    assert product["readiness"]["telegram"]["paired"] is False
                    assert "accessibility" in product["mac"]
            finally:
                process.terminate()
                process.wait(timeout=15)
    print(
        "Real installation passed: private config, token file, running server, single-use local login and readiness checks"
    )


if __name__ == "__main__":
    main()
