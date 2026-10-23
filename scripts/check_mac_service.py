"""Actual launchd login-service acceptance on a Mac with a signed-in GUI session."""

import json
import os
import re
import signal
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx

from openduet.installation import LABEL, local_login_url, service, setup


def main():
    domain = "gui/" + str(os.getuid())
    capability = subprocess.run(["/bin/launchctl", "print", domain], capture_output=True)
    report = {"gui_session": capability.returncode == 0, "passed": False}
    output = Path(".runtime/mac-service-acceptance.json")
    output.parent.mkdir(exist_ok=True)
    if capability.returncode:
        report["reason"] = "Runner has no signed-in GUI session; physical Mac acceptance is required"
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(report)
        return
    with tempfile.TemporaryDirectory() as temporary:
        path, config = setup(Path(temporary) / "OpenDuet login fixture")
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        path.write_text(path.read_text().replace("port = 8765", f"port = {port}"))
        config.port = port
        try:
            service(path, "install")
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=2) as client:

                def wait_ready():
                    for _ in range(120):
                        try:
                            if client.get("/health").status_code == 200:
                                return
                        except httpx.HTTPError:
                            pass
                        time.sleep(0.25)
                    raise AssertionError("Login service did not become healthy")

                wait_ready()
                code = parse_qs(urlsplit(local_login_url(config)).fragment)["setup"][0]
                assert client.post("/api/local-session", json={"code": code}).status_code == 200
                assert client.get("/api/state").status_code == 200
                data = subprocess.run(
                    ["/bin/launchctl", "print", domain + "/" + LABEL], capture_output=True, check=True
                ).stdout.decode()
                process = int(re.search(r"\bpid = (\d+)", data)[1])
                os.kill(process, signal.SIGTERM)
                restarted = process
                for _ in range(120):
                    result = subprocess.run(
                        ["/bin/launchctl", "print", domain + "/" + LABEL], capture_output=True
                    )
                    match = re.search(rb"\bpid = (\d+)", result.stdout)
                    if match and int(match[1]) != process:
                        restarted = int(match[1])
                        break
                    time.sleep(0.25)
                wait_ready()
                assert process != restarted
                assert client.get("/api/state").status_code == 200, (
                    "Private token/session must survive a service restart"
                )
                assert client.post("/api/local-session", json={"code": code}).status_code == 401
                report.update(passed=True, restarted=True, session_persisted=True)
        finally:
            service(path, "uninstall")
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(report)


if __name__ == "__main__":
    main()
