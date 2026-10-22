"""Fail-closed placeholder until an isolated computer service is configured."""

from urllib.parse import urlsplit


class Browser:
    def __init__(self, directory, hosts):
        self.directory, self.hosts = directory, set(hosts)
        self.context = self.page = None

    def allowed(self, url):
        parsed = urlsplit(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname in self.hosts
            and not parsed.username
            and not parsed.password
        )

    async def run(self, **arguments):
        raise ValueError(
            "Configure computer_url for the separate isolated browser service; see docs/SELF-HOSTING.md"
        )

    async def login(self, selector, value, expected_url):
        if self.page and self.page.url != expected_url:
            raise ValueError("Browser page changed; refresh before private sign-in")
        raise ValueError("Private sign-in requires the isolated computer service")

    async def close(self):
        pass
