"""Real Chromium acceptance against disposable bot/model transports."""

import asyncio
import io
import os
import time
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from openpyxl import Workbook
from playwright.async_api import async_playwright, expect

from tests.fixtures.mcp_process import loopback_server


async def check_in_flight_refresh(page):
    await page.locator("#navigation [data-view=make]").click()
    await expect(page.locator("#content h1")).to_have_text("Make")
    await page.evaluate("window.fixtureStreams.forEach(stream=>stream.close())")
    blocked, release = asyncio.Event(), asyncio.Event()
    first_response = True

    async def hold_snapshot(route):
        nonlocal first_response
        response = await route.fetch()
        if first_response:
            first_response = False
            blocked.set()
            await release.wait()
            await route.fulfill(response=response)
        else:
            snapshot = await response.json()
            snapshot["artifacts"][0]["title"] = "Latest refresh evidence"
            await route.fulfill(response=response, json=snapshot)

    await page.route("**/api/state", hold_snapshot)
    first = asyncio.create_task(page.evaluate("import('/app.js').then(app=>app.refresh(false))"))
    try:
        await asyncio.wait_for(blocked.wait(), timeout=5)
        await page.evaluate("import('/app.js').then(app=>app.refresh(false))")
        release.set()
        await first
        await expect(page.get_by_role("heading", name="Latest refresh evidence", exact=True)).to_be_visible(
            timeout=5000
        )
    finally:
        release.set()
        await first
        await page.unroute("**/api/state", hold_snapshot)


async def main():
    output = Path(".runtime/screenshots/console")
    output.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH"), args=["--no-sandbox"]
        )
        page = await browser.new_page(viewport={"width": 1280, "height": 960})
        await page.add_init_script(
            "const BaseEventSource=window.EventSource;window.fixtureStreams=[];"
            "window.EventSource=class extends BaseEventSource{constructor(...args){super(...args);window.fixtureStreams.push(this);}};"
        )
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto("http://127.0.0.1:8766")
        await page.locator("#token").fill(os.environ["OPENDUET_TOKEN"])
        await page.locator("#login-form button").click()
        await page.locator("#bot-form").wait_for()
        await page.locator("#bot-form input").fill("123456:fixture-token-not-production")
        await page.locator("#bot-form button").click()
        pairing = page.get_by_role("link", name="Pair my Telegram account", exact=True)
        await pairing.wait_for()
        update_base = int(time.time() * 1000)
        code = parse_qs(urlsplit(await pairing.get_attribute("href")).query)["start"][0]
        response = await page.request.post(
            "http://127.0.0.1:8766/api/fixture/update",
            data={
                "update_id": update_base,
                "message": {
                    "message_id": 1,
                    "from": {"id": 12, "first_name": "Fixture Owner"},
                    "chat": {"id": 12, "type": "private"},
                    "text": "/start " + code,
                },
            },
        )
        assert response.ok
        await page.get_by_text("Paired with", exact=False).wait_for(timeout=15000)

        async def update(identifier, text):
            response = await page.request.post(
                "http://127.0.0.1:8766/api/fixture/update",
                data={
                    "update_id": update_base + identifier,
                    "message": {
                        "message_id": identifier,
                        "from": {"id": 12},
                        "chat": {"id": 12, "type": "private"},
                        "text": text,
                    },
                },
            )
            assert response.ok

        await update(2, "Prepare a weekly brief")
        await page.locator("#navigation [data-view=make]").click()
        await page.get_by_role("heading", name="A little space for the week").first.wait_for(timeout=15000)
        await page.locator("[data-preview]").first.click()
        await page.locator("#work-preview[open]").wait_for()
        await page.locator("#work-preview form button").click()
        await update(3, "Remember my meeting preference")
        await page.locator("#navigation [data-view=tasks]").click()
        approve = page.get_by_role("button", name="Approve", exact=True).first
        await approve.wait_for(timeout=15000)
        await approve.click()
        await page.locator("#navigation [data-view=settings]").click()
        await page.get_by_text("I prefer morning meetings. UI test fixture.", exact=True).wait_for(
            timeout=15000
        )
        with loopback_server() as origin:
            await page.locator("#navigation [data-view=connections]").click()
            quickbooks = page.locator(".directory-item").filter(
                has=page.get_by_role("heading", name="QuickBooks", exact=True)
            )
            await expect(quickbooks.get_by_role("link", name="Setup guide", exact=True)).to_be_visible()
            assert await quickbooks.get_by_role("button", name="Connect", exact=True).count() == 0
            gusto = page.locator(".directory-item").filter(
                has=page.get_by_role("heading", name="Gusto", exact=True)
            )
            await expect(gusto).to_contain_text("fresh dedicated OpenDuet profile")
            form = page.locator("#connector-form")
            await form.locator("[name=name]").fill("oauth-fixture")
            await form.locator("[name=url]").fill(origin + "/oauth/mcp")
            await form.locator("button").click()
            await page.locator('[data-oauth="oauth-fixture"]').click()
            await page.locator("#oauth-form [name=client_id]").fill("fixture-confidential")
            await page.locator("#oauth-form [name=client_secret]").fill("fixture-private-client")
            await page.locator("#oauth-form button").first.click()
            await page.wait_for_url("**/?view=connections")
            await page.locator('[data-oauth="oauth-fixture"]').wait_for()
            discovered = await (
                await page.request.get("http://127.0.0.1:8766/api/connectors/oauth-fixture/tools")
            ).json()
            assert any(tool["name"] == "echo" for tool in discovered["tools"]), discovered
            await update(4, "Read the connected fixture")
            await page.locator("#navigation [data-view=chat]").click()
            await page.get_by_text("Connected service verified.", exact=True).wait_for(timeout=15000)
            await page.locator("#navigation [data-view=connections]").click()
            for service, kind in [("gmail", "mail.received"), ("google-calendar", "calendar.event")]:
                form = page.locator("#connector-form")
                await form.locator("[name=name]").fill(service)
                await form.locator("[name=url]").fill(origin + "/mcp")
                await form.locator("summary").click()
                await form.locator("[name=poll_tool]").fill("read_events")
                await form.locator("[name=event_kind]").fill(kind)
                await form.locator("[name=cursor_argument]").fill("cursor")
                await form.locator("[name=poll_arguments]").fill('{"service":"' + service + '"}')
                async with page.expect_response(
                    lambda response: (
                        response.url.endswith("/api/connectors") and response.request.method == "POST"
                    )
                ) as response:
                    await form.locator("button").click()
                assert (await response.value).ok
                await page.locator('[data-oauth="' + service + '"]').wait_for()
            await page.locator("#navigation [data-view=proactivity]").click()
            await expect(page.locator("#attention-form [name=brief_time]")).to_have_value("07:30")
            await update(5, "Send my morning brief at 08:15 and poll every 900 seconds")
            await page.locator("#navigation [data-view=tasks]").click()
            await page.get_by_role("button", name="Approve", exact=True).first.click()
            await page.locator("#navigation [data-view=proactivity]").click()
            await expect(page.locator("#attention-form [name=brief_time]")).to_have_value("08:15")
            await expect(page.locator("[data-cadence=gmail] [name=seconds]")).to_have_value("900")
            await page.locator("#attention-form [name=brief_time]").fill("08:30")
            await page.locator("#attention-form").evaluate("form => form.dataset.acceptancePending = 'true'")
            await page.locator("#attention-form button").first.click()
            await expect(page.locator("[data-acceptance-pending]")).to_have_count(0)
            await expect(page.locator("#attention-form [name=brief_time]")).to_have_value("08:30")
            await page.locator("[data-cadence=gmail] [name=seconds]").fill("1200")
            async with page.expect_response(
                lambda response: (
                    response.url.endswith("/api/proactivity") and response.request.method == "POST"
                )
            ) as response:
                await page.locator("[data-cadence=gmail] button").click()
            assert (await response.value).ok
            preferences = (await (await page.request.get("http://127.0.0.1:8766/api/product")).json())[
                "proactivity"
            ]["preferences"]
            assert preferences["brief_time"] == "08:30" and preferences["connector_cadence"]["gmail"] == 1200
            visible_state = await (await page.request.get("http://127.0.0.1:8766/api/state")).text()
            assert "fixture-private-client" not in visible_state
            await page.locator("#navigation [data-view=connections]").click()
            await page.locator('[data-disconnect="oauth-fixture"]').click()
            await expect(page.locator('[data-oauth="oauth-fixture"]')).to_have_count(0)
            for service in ["gmail", "google-calendar"]:
                await page.locator('[data-disconnect="' + service + '"]').click()
                await expect(page.locator('[data-oauth="' + service + '"]')).to_have_count(0)
        buffer, book = io.BytesIO(), Workbook()
        book.active.title = "Revenue"
        book.active["A1"] = 100
        book.save(buffer)
        await page.locator("#navigation [data-view=chat]").click()
        await page.locator("#attachment").set_input_files(
            {"name": "remove-me.txt", "mimeType": "text/plain", "buffer": b"Removed fixture data"}
        )
        await expect(page.locator("#attachment-status")).to_have_text("remove-me.txt")
        await page.get_by_role("button", name="Remove attachment", exact=True).click()
        await expect(page.locator("#attachment-status")).to_have_text("")
        uploading, release_upload = asyncio.Event(), asyncio.Event()
        uploaded_id = None

        async def hold_upload(route):
            nonlocal uploaded_id
            response = await route.fetch()
            uploaded_id = (await response.json())["attachment"]
            uploading.set()
            await release_upload.wait()
            await route.fulfill(response=response)

        await page.route("**/api/attachments?name=budget.xlsx", hold_upload)
        try:
            await page.locator("#attachment").set_input_files(
                {
                    "name": "budget.xlsx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "buffer": buffer.getvalue(),
                }
            )
            await asyncio.wait_for(uploading.wait(), timeout=5)
            await page.locator("#prompt").fill("Create sourced report fixture")
            await page.evaluate("import('/app.js').then(app=>app.refresh(true))")
            await expect(page.locator("#prompt")).to_have_value("Create sourced report fixture")
            await expect(page.locator("#compose button[type=submit]")).to_be_disabled()
            release_upload.set()
            await expect(page.locator("#attachment-status")).to_have_text("budget.xlsx")
        finally:
            release_upload.set()
            await page.unroute("**/api/attachments?name=budget.xlsx", hold_upload)
        other = await (
            await page.request.post(
                "http://127.0.0.1:8766/api/channels", data={"name": "Draft isolation fixture"}
            )
        ).json()
        await page.evaluate("import('/app.js').then(app=>app.refresh(true))")
        await page.locator("#channel").select_option(other["id"])
        await expect(page.locator("#prompt")).to_have_value("")
        await expect(page.locator("#attachment-status")).to_have_text("")
        await page.locator("#channel").select_option("main")
        await expect(page.locator("#prompt")).to_have_value("Create sourced report fixture")
        await expect(page.locator("#attachment-status")).to_have_text("budget.xlsx")
        async with page.expect_request(
            lambda request: request.url.endswith("/api/messages") and request.method == "POST"
        ) as sent:
            await page.locator("#compose").get_by_role("button", name="Send", exact=True).click()
        assert (await sent.value).post_data_json["attachments"] == [uploaded_id]
        assert (await sent.value).post_data_json["channel"] == "main"
        await page.locator("#navigation [data-view=make]").click()
        report = page.locator(".artifact").filter(
            has=page.get_by_role("heading", name="Sourced input report", exact=True)
        )
        try:
            await report.get_by_role("button", name="Open", exact=True).click(timeout=15000)
        except Exception:
            snapshot = await (await page.request.get("http://127.0.0.1:8766/api/state")).json()
            print(
                "Source export diagnostics:",
                {
                    "tasks": [
                        {key: task[key] for key in ("id", "status", "error")} for task in snapshot["tasks"]
                    ],
                    "artifacts": [
                        {key: artifact[key] for key in ("id", "title")} for artifact in snapshot["artifacts"]
                    ],
                    "view": await page.locator("#content h1").text_content(),
                    "page_errors": errors,
                },
            )
            raise
        await page.get_by_text("budget.xlsx · 'Revenue'!A1", exact=True).click()
        await expect(page.locator(".artifact-sources details[open] pre")).to_have_text("100")
        response = await page.request.get(
            "http://127.0.0.1:8766" + await page.locator("#work-preview a.button").first.get_attribute("href")
        )
        assert response.ok
        with zipfile.ZipFile(io.BytesIO(await response.body())) as archive:
            assert b'w:anchor="src_' in archive.read("word/document.xml")
        for width in [1440, 768, 390]:
            await page.set_viewport_size({"width": width, "height": 960})
            assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            await page.screenshot(path=str(output / f"source-preview-{width}.png"), full_page=True)
        await page.locator("#work-preview form button").click()
        for width in [1280, 375]:
            await page.set_viewport_size({"width": width, "height": 960 if width == 1280 else 812})
            for theme in ["light", "dark"]:
                await page.evaluate(
                    '(theme)=>{localStorage.setItem("theme",theme);document.documentElement.dataset.theme=theme}',
                    theme,
                )
                for view in ["telegram", "tasks", "make", "proactivity", "connections", "settings", "chat"]:
                    if width == 375 and view in ["connections", "settings", "chat"]:
                        await page.locator("#more-button").click()
                        await page.locator("#more-links [data-view=" + view + "]").click()
                    else:
                        await page.locator("#navigation [data-view=" + view + "]").click()
                    await expect(page.locator("#content h1")).to_have_text(
                        {
                            "telegram": "Telegram",
                            "tasks": "Tasks",
                            "make": "Make",
                            "proactivity": "Proactivity",
                            "connections": "Connections",
                            "settings": "Settings",
                            "chat": "Chat",
                        }[view]
                    )
                    assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                        width,
                        theme,
                        view,
                    )
                    await page.screenshot(path=str(output / f"{view}-{theme}-{width}.png"), full_page=True)
        deliveries = await (await page.request.get("http://127.0.0.1:8766/api/fixture/deliveries")).json()
        assert any(item["method"] == "sendDocument" for item in deliveries), deliveries
        await page.set_viewport_size({"width": 1280, "height": 960})
        await check_in_flight_refresh(page)
        assert not errors, errors
        await browser.close()
        print(
            "Browser acceptance passed: bot pairing → shared task → Make file → approval → HTTP OAuth connection → discovered tool task → disconnect; 28 responsive/dark screenshots"
        )


if __name__ == "__main__":
    asyncio.run(main())
