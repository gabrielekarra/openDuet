"""Run against the disposable preview fixture. Requires Playwright and local Chromium."""

import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH"), args=["--no-sandbox"]
        )
        page = await browser.new_page(viewport={"width": 1440, "height": 1080})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto("http://127.0.0.1:8766")
        await page.locator("#token").fill(os.environ["OPENDUET_TOKEN"])
        await page.locator("#login-form button").click()
        await page.locator("#prompt").wait_for()
        await page.locator("#prompt").fill("Prepare a weekly brief")
        await page.locator("#compose button[type=submit]").click()
        await page.get_by_text("The preview draft is ready.", exact=False).first.wait_for(timeout=15000)
        await page.get_by_role("button", name="Make", exact=False).first.click()
        await page.get_by_role("heading", name="A little space for the week").first.wait_for()
        await page.get_by_role("button", name="Edit", exact=True).first.click()
        await page.locator("#editor-content").fill("# Revised draft\nReviewed in the browser smoke test.")
        await page.locator("#save-artifact").click()
        await page.locator("#editor").wait_for(state="hidden")
        await page.get_by_role("button", name="Home", exact=False).first.click()
        await page.locator("#prompt").fill("Remember my meeting preference")
        await page.locator("#compose button[type=submit]").click()
        await page.get_by_role("button", name="Approve once").first.wait_for(timeout=15000)
        await page.get_by_role("button", name="Approve once").first.click()
        await page.get_by_role("button", name="Memory", exact=False).first.click()
        await page.get_by_text("I prefer morning meetings. UI test fixture.", exact=True).wait_for(
            timeout=15000
        )
        for name in ["Tasks", "Routines", "Connections", "Settings", "Home"]:
            await page.get_by_role("button", name=name, exact=False).first.click()
            await page.wait_for_timeout(100)
        Path(".runtime/screenshots").mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=".runtime/screenshots/openduet-desktop.png", full_page=True)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.screenshot(path=".runtime/screenshots/openduet-mobile.png", full_page=True)
        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
            "Mobile page overflows"
        )
        assert not errors, errors
        await page.set_viewport_size({"width": 1440, "height": 1080})
        await page.get_by_role("button", name="Computers", exact=False).first.click()
        async with page.expect_popup() as popup:
            await page.get_by_role("link", name="Open desktop", exact=False).click()
        remote = await popup.value
        remote.on("pageerror", lambda error: errors.append(str(error)))
        await remote.get_by_text("View mode · agent paused", exact=True).wait_for(timeout=15000)
        await remote.wait_for_function("document.querySelector('#remote-screen canvas')?.width === 320")
        await remote.get_by_role("button", name="Take control", exact=True).click()
        await remote.locator("#remote-screen canvas").click(position={"x": 50, "y": 50})
        await remote.keyboard.press("a")
        await remote.wait_for_function(
            "async () => (await (await fetch('/api/fixture/desktop-events')).json()).some(e => e.type === 'key' && e.keysym === 97)"
        )
        events = await (await remote.request.get("http://127.0.0.1:8766/api/fixture/desktop-events")).json()
        assert any(event["type"] == "pointer" and event["mask"] == 1 for event in events)
        await remote.screenshot(path=".runtime/screenshots/openduet-remote-desktop.png", full_page=True)
        await remote.get_by_role("button", name="Disconnect", exact=True).click()
        await remote.get_by_text("Disconnected. Agent work can continue.", exact=True).wait_for()
        assert not errors, errors
        await browser.close()
        print("Browser smoke passed: workspace, mobile layout and remote desktop mouse/keyboard input")


asyncio.run(main())
