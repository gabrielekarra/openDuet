"""Execute an interactive prototype in Chromium and prove its credential/API boundary."""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
from playwright.async_api import async_playwright


async def main():
    hits = []

    class Parent(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path.startswith("/api/private"):
                hits.append(self.path)
            content = b"Owner fixture"
            self.send_response(200)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "null")
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.end_headers()
            self.wfile.write(content)

    parent = ThreadingHTTPServer(("127.0.0.1", 0), Parent)
    threading.Thread(target=parent.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{parent.server_port}"
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        ident = "a" * 32
        (root / ident).mkdir()
        script = """window.probe={};for(const field of ['storage','parent','cookie']){try{if(field==='storage')localStorage.getItem('x');if(field==='parent')window.parent.localStorage.getItem('owner');if(field==='cookie')document.cookie;}catch{window.probe[field]=true;}}fetch(PARENT+'/api/private',{credentials:'include'}).then(()=>window.probe.network=false).catch(()=>window.probe.network=true);""".replace(
            "PARENT", json.dumps(origin)
        )
        (root / ident / "index.html").write_text(
            '<button id="counter" onclick="this.textContent=String(Number(this.textContent)+1)">0</button><script>'
            + script
            + "</script>"
        )
        environment = {"PATH": os.environ["PATH"], "OPENDUET_PROTOTYPES": str(root)}
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "openduet.prototypes:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                "8767",
                "--no-access-log",
            ],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            async with httpx.AsyncClient(trust_env=False) as client:
                for _ in range(60):
                    try:
                        if (await client.get("http://127.0.0.1:8767/health")).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(0.1)
                else:
                    raise AssertionError("Prototype fixture did not start")
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    executable_path=os.environ.get("CHROMIUM_PATH"), args=["--no-sandbox"]
                )
                page = await browser.new_page()
                await page.goto(origin)
                await page.evaluate("localStorage.setItem('owner','fixture-private-owner-data')")
                await page.context.add_cookies(
                    [
                        {
                            "name": "openduet",
                            "value": "fixture-only-owner-cookie",
                            "domain": "127.0.0.1",
                            "path": "/",
                            "httpOnly": True,
                        }
                    ]
                )
                await page.set_content(
                    f'<iframe title="Prototype fixture" sandbox="allow-scripts" src="http://127.0.0.1:8767/p/{ident}/index.html"></iframe>'
                )
                frame = page.frame_locator("iframe")
                await frame.locator("#counter").click()
                await frame.locator("#counter").click()
                assert await frame.locator("#counter").text_content() == "2"
                child = next(frame for frame in page.frames if frame != page.main_frame)
                await child.wait_for_function("window.probe?.network===true")
                values = await child.evaluate("window.probe")
                assert all(values.get(key) for key in ["storage", "parent", "cookie", "network"]), values
                assert hits == [], hits
                await browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            parent.shutdown()
            parent.server_close()
    print(
        "Prototype acceptance passed: runnable JS, opaque storage, inaccessible parent credentials and blocked API/network"
    )


asyncio.run(main())
