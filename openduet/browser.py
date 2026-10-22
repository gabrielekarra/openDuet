from __future__ import annotations

from urllib.parse import urlsplit


class Browser:
    """Dedicated persistent browser. All navigation and interaction requires host approval.

    The configured origin allowlist is enforced on every browser request, including redirects,
    subresources and popups. Run on your own VM for a separate computer's security boundary.
    """

    def __init__(self, directory, hosts):
        self.directory = directory
        self.hosts = set(hosts)
        self.context = self.page = self.runtime = None

    def allowed(self, url):
        parsed = urlsplit(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname in self.hosts
            and not parsed.username
            and not parsed.password
        )

    async def start(self):
        if self.context:
            return
        if not self.hosts:
            raise ValueError("Configure browser_hosts before using the browser")
        from playwright.async_api import async_playwright

        self.runtime = await async_playwright().start()
        self.context = await self.runtime.chromium.launch_persistent_context(
            str(self.directory),
            headless=True,
            accept_downloads=False,
            service_workers="block",
            args=["--disable-dev-shm-usage"],
        )

        async def route(request):
            if self.allowed(request.request.url):
                await request.continue_()
            else:
                await request.abort()

        await self.context.route("**/*", route)
        # WebSocket connections bypass HTTP routing in Chromium.
        await self.context.route_web_socket("**/*", lambda socket: socket.close())
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.page.set_default_timeout(15000)

    async def run(self, action, url="", selector="", text=""):
        await self.start()
        if action == "open":
            if not self.allowed(url):
                raise ValueError("Browser URL is outside browser_hosts")
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        elif action == "click":
            await self.page.locator(selector).click()
        elif action == "fill":
            element = self.page.locator(selector)
            if await element.get_attribute("type") == "password":
                raise ValueError("Use the private login form for passwords")
            await element.fill(text)
        elif action != "read":
            raise ValueError("Unknown browser action")
        # Do not return DOM values, cookies or password fields to a model.
        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "text": (await self.page.locator("body").inner_text())[:24000],
        }

    async def login(self, selector, value):
        await self.start()
        if not self.allowed(self.page.url):
            raise ValueError("Open an allowed login page first")
        await self.page.locator(selector).fill(value)

    async def close(self):
        if self.context:
            await self.context.close()
        if self.runtime:
            await self.runtime.stop()
