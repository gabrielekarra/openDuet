"""Lighthouse acceptance for the disposable authenticated preview (never a production audit token)."""

import json
import os
import subprocess
import tempfile
from pathlib import Path


def main():
    binary = os.environ.get("LIGHTHOUSE_BIN", "lighthouse")
    results = {}
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        headers = directory / "headers.json"
        headers.write_text(json.dumps({"Authorization": "Bearer " + os.environ["OPENDUET_TOKEN"]}))
        headers.chmod(0o600)
        for view in ["telegram", "tasks"]:
            report = directory / (view + ".json")
            subprocess.run(
                [
                    binary,
                    "http://127.0.0.1:8766/?view=" + view,
                    "--only-categories=accessibility",
                    "--chrome-flags=--headless --no-sandbox --disable-dev-shm-usage",
                    "--extra-headers=" + str(headers),
                    "--output=json",
                    "--output-path=" + str(report),
                    "--quiet",
                ],
                check=True,
            )
            data = json.loads(report.read_text())
            score = data["categories"]["accessibility"]["score"] * 100
            failures = {key: item["title"] for key, item in data["audits"].items() if item.get("score") == 0}
            results[view] = {
                "score": score,
                "failures": failures,
                "lighthouse_version": data["lighthouseVersion"],
            }
    output = Path(".runtime/screenshots/accessibility.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results))
    assert all(item["score"] >= 95 for item in results.values()), "Accessibility score below acceptance floor"


if __name__ == "__main__":
    main()
