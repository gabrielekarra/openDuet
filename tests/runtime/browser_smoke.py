"""Real Chromium acceptance against disposable bot/model transports."""

import asyncio
import os
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.async_api import async_playwright, expect


async def main():
    output = Path(".runtime/screenshots/console")
    output.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH"), args=["--no-sandbox"]
        )
        page = await browser.new_page(viewport={"width": 1280, "height": 960})
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
        assert not errors, errors
        await browser.close()
        print(
            "Browser acceptance passed: bot pairing → shared task → Make file → approval; 28 responsive/dark screenshots"
        )


asyncio.run(main())
