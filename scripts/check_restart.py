"""Kill a real server mid Telegram task; recover its database and verify one delivery."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        token = "fixture-only-restart-token-not-production"
        environment = {
            **os.environ,
            "OPENDUET_TOKEN": token,
            "OPENDUET_PREVIEW_DATA": str(root / "data"),
            "OPENDUET_PREVIEW_PAUSE_ONCE": "1",
        }
        log = (root / "server.log").open("wb")

        def start():
            return subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "tests.fixtures.openduet_preview:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--no-access-log",
                ],
                cwd=Path(__file__).resolve().parents[1],
                env=environment,
                stdout=log,
                stderr=log,
            )

        process = start()
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=3, trust_env=False) as client:

                def wait(predicate, message):
                    for _ in range(160):
                        try:
                            if predicate():
                                return
                        except httpx.HTTPError:
                            pass
                        if process.poll() is not None:
                            raise AssertionError(
                                "Server exited: " + (root / "server.log").read_text()[-3000:]
                            )
                        time.sleep(0.1)
                    raise AssertionError(message)

                wait(lambda: client.get("/health").status_code == 200, "Server never started")
                assert client.post("/api/login", json={"token": token}).status_code == 200
                assert (
                    client.post(
                        "/api/telegram/token", json={"token": "123456:fixture-only-bot-token"}
                    ).status_code
                    == 200
                )
                code = parse_qs(urlsplit(client.post("/api/telegram/pair", json={}).json()["url"]).query)[
                    "start"
                ][0]

                def update(number, text, topic=None):
                    response = client.post(
                        "/api/fixture/update",
                        json={
                            "update_id": number,
                            "message": {
                                "message_id": number,
                                "from": {"id": 12},
                                "chat": {"id": 12, "type": "private"},
                                "text": text,
                                **({"message_thread_id": topic} if topic else {}),
                            },
                        },
                    )
                    assert response.status_code == 200, response.text

                update(1, "/start " + code)
                update(2, "Create a Markdown artifact for restart acceptance", topic=27)
                wait(
                    lambda: (root / "data/.restart-barrier").exists(),
                    "Task never reached the in-flight model request",
                )
                before = client.get("/api/state").json()
                assert before["tasks"][0]["status"] == "running"
                assert not any(
                    item["method"] == "sendDocument" for item in client.get("/api/fixture/deliveries").json()
                )
                process.kill()  # actual process death: no lifespan cleanup or task cancellation handler
                process.wait(timeout=5)
                process = start()
                wait(
                    lambda: client.get("/api/state").status_code == 200, "Session did not survive the restart"
                )
                wait(
                    lambda: client.get("/api/state").json()["tasks"][0]["status"] == "ready",
                    "Interrupted safe task did not finish automatically",
                )
                wait(
                    lambda: any(
                        item["method"] == "sendDocument"
                        for item in client.get("/api/fixture/deliveries").json()
                    ),
                    "Recovered task did not deliver on Telegram",
                )
                files = [
                    item
                    for item in client.get("/api/fixture/deliveries").json()
                    if item["method"] == "sendDocument"
                ]
                assert len(files) == 1 and files[0]["payload"]["file"]
                assert files[0]["payload"]["chat_id"] == 12
                assert files[0]["payload"]["message_thread_id"] == 27
                after = client.get("/api/state").json()
                assert after["tasks"][0]["id"] == before["tasks"][0]["id"]
                assert len(after["artifacts"]) == 1
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            log.close()
    report = {
        "passed": True,
        "actual_process_kill": True,
        "automatic_resume": True,
        "same_task": True,
        "same_chat_and_topic": True,
        "one_document": True,
        "session_persisted": True,
        "transports": "disposable Telegram/model fixtures",
    }
    output = Path(".runtime/restart-acceptance.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(report)


if __name__ == "__main__":
    main()
