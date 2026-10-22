"""On-demand control of the user's own Mac. No screen-sharing server or background sensor."""

from __future__ import annotations

import asyncio
import plistlib
import sys
from pathlib import Path

from .store import uid

PROTECTED = ("keychain", "1password", "bitwarden", "keepass", "passwords")


class MacHost:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.elements = {}
        self.snapshot_id = ""
        self.pid = None
        self.lock = asyncio.Lock()

    @property
    def enabled(self):
        return sys.platform == "darwin" and self.store.preference("mac_enabled", False)

    def check(self):
        if not self.enabled:
            raise ValueError("Enable Mac access in Settings on the Mac running OpenDuet")

    def apps(self):
        self.check()
        found = []
        for directory in (Path("/Applications"), Path("/System/Applications"), Path.home() / "Applications"):
            for app in sorted(directory.glob("*.app")):
                try:
                    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
                    name, bundle = app.stem, info["CFBundleIdentifier"]
                    if not any(word in (name + bundle).lower() for word in PROTECTED):
                        found.append({"name": name, "bundle_id": bundle})
                except (OSError, ValueError, KeyError):
                    continue
        return found

    async def command(self, *arguments):
        child = await asyncio.create_subprocess_exec(
            *arguments, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
        )
        try:
            output, _ = await asyncio.wait_for(child.communicate(), timeout=15)
        except BaseException:
            if child.returncode is None:
                child.kill()
                await child.wait()
            raise
        if child.returncode:
            raise ValueError(
                "macOS refused this operation; check Screen Recording and Accessibility permissions"
            )
        return output

    async def open_app(self, bundle_id):
        if bundle_id not in {a["bundle_id"] for a in self.apps()}:
            raise ValueError("Choose an installed, permitted application from mac_apps")
        await self.command("/usr/bin/open", "-b", bundle_id)
        self.elements.clear()
        return {"opened": bundle_id}

    def observe(self):
        self.check()
        try:
            import ApplicationServices as AX
            from AppKit import NSWorkspace
        except ImportError:
            raise ValueError("Install OpenDuet with the mac extra: pip install 'openduet[mac]'") from None
        if not AX.AXIsProcessTrusted():
            raise ValueError("Grant Accessibility to the Python/terminal running OpenDuet in macOS Settings")
        front = NSWorkspace.sharedWorkspace().frontmostApplication()
        if not front or any(word in str(front.bundleIdentifier()).lower() for word in PROTECTED):
            raise ValueError("This application is protected")
        allowed = {a["bundle_id"] for a in self.apps()}
        if str(front.bundleIdentifier()) not in allowed:
            raise ValueError("The foreground application is not permitted")
        self.pid = front.processIdentifier()
        self.elements.clear()
        self.snapshot_id = uid()

        def attribute(element, name, default=""):
            error, value = AX.AXUIElementCopyAttributeValue(element, name, None)
            return default if error or value is None else value

        root = AX.AXUIElementCreateApplication(self.pid)
        queue = list(attribute(root, "AXWindows", []))
        records = []
        visited = 0
        while queue and visited < 600:
            element = queue.pop(0)
            visited += 1
            role = str(attribute(element, "AXRole"))
            if role == "AXSecureTextField" or attribute(element, "AXProtectedContent", False):
                continue
            label = str(attribute(element, "AXTitle") or attribute(element, "AXDescription"))[:300]
            value = str(attribute(element, "AXValue"))[:1000]
            error, actions = AX.AXUIElementCopyActionNames(element, None)
            identifier = str(len(records) + 1)
            self.elements[identifier] = element
            records.append(
                {
                    "id": identifier,
                    "role": role,
                    "label": label,
                    "value": value,
                    "actions": [] if error else list(actions or []),
                }
            )
            queue.extend(attribute(element, "AXChildren", []))
        return {"snapshot": self.snapshot_id, "app": str(front.localizedName()), "elements": records}

    async def act(self, snapshot, element, action, value=""):
        self.check()
        import ApplicationServices as AX
        from AppKit import NSWorkspace

        front = NSWorkspace.sharedWorkspace().frontmostApplication()
        if (
            snapshot != self.snapshot_id
            or element not in self.elements
            or front.processIdentifier() != self.pid
        ):
            raise ValueError("Stale screen: call mac_observe again before acting")
        target = self.elements[element]
        self.elements = {}
        if action == "type":
            error = AX.AXUIElementSetAttributeValue(target, "AXValue", value)
        else:
            operation = {"click": "AXPress", "open": "AXOpen", "raise": "AXRaise"}.get(action)
            if not operation:
                raise ValueError("Unsupported native action")
            error = AX.AXUIElementPerformAction(target, operation)
        if error:
            raise ValueError("The application refused the action; observe its current state")
        return {"performed": action}

    async def screenshot(self, task=None):
        self.check()
        # Refuse protected foreground apps before capturing any display pixels.
        await asyncio.to_thread(self.observe)
        directory = self.runtime.config.data_dir / "attachments"
        directory.mkdir(exist_ok=True, mode=0o700)
        ident = uid()
        path = directory / (ident + ".png")
        await self.command("/usr/sbin/screencapture", "-x", "-t", "png", str(path))
        if not path.is_file() or path.stat().st_size > 20_000_000:
            path.unlink(missing_ok=True)
            raise ValueError("Screen capture unavailable or too large")
        path.chmod(0o600)
        self.store.execute(
            "INSERT INTO attachments VALUES(?,?,?,?,?,?)",
            (ident, task, "screen.png", "image/png", path.name, path.stat().st_size),
        )
        return {
            "attachment": ident,
            "name": "screen.png",
            "note": "Screenshot ready for the owner in Telegram",
        }
