"""Explicitly configured, dedicated-vault password managers; resolved only at private sign-in."""

from __future__ import annotations

from urllib.parse import quote, urlsplit

import httpx

from .registry import endpoint


class Credentials:
    def __init__(self, runtime):
        self.runtime = runtime

    async def sign_in(self, site, task):
        settings = self.runtime.store.preference("password_manager", {})
        mapping = settings.get("sites", {}).get(site)
        if not mapping or settings.get("provider") not in {"1password", "bitwarden"}:
            raise ValueError("Connect a dedicated password-manager vault and this site in Settings")
        page = self.runtime.browser.page
        if not page or urlsplit(page.url).hostname != site or urlsplit(page.url).scheme != "https":
            raise ValueError("Open the exact HTTPS sign-in site before requesting its credentials")
        expected_url = page.url
        base = endpoint(settings["url"]).rstrip("/")
        vault = settings["vault"]
        item_id = quote(mapping["item"], safe="")
        token = self.runtime.vault.get("password_manager.token", purpose="sign-in:" + site, task=task)
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            headers = {"Authorization": "Bearer " + token}
            if settings["provider"] == "1password":
                response = await client.get(
                    base + "/v1/vaults/" + quote(vault, safe="") + "/items/" + item_id, headers=headers
                )
                response.raise_for_status()
                fields = {
                    field.get("id", field.get("label", "")): field.get("value", "")
                    for field in response.json().get("fields", [])
                }
                username, password = fields.get("username", ""), fields.get("password", "")
            else:
                response = await client.get(base + "/object/item/" + item_id, headers=headers)
                response.raise_for_status()
                item = response.json().get("data", {})
                if vault not in (item.get("collectionIds") or []) and item.get("folderId") != vault:
                    raise ValueError("This Bitwarden item is outside the dedicated vault scope")
                username, password = (
                    item.get("login", {}).get("username", ""),
                    item.get("login", {}).get("password", ""),
                )
        if not password:
            raise ValueError("The selected item does not contain a password")
        self.runtime.private_values.update((username, password))
        # The tool result deliberately contains neither values nor page text.
        await self.runtime.browser.login(mapping["username_selector"], username, expected_url)
        await self.runtime.browser.login(mapping["password_selector"], password, expected_url)
        return {
            "private_fields_filled": True,
            "site": site,
            "note": "Submit the sign-in separately; credentials were not added to conversation history",
        }
