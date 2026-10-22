"""On-demand control of the user's own Mac. No screen-sharing server or background sensor."""

from __future__ import annotations

import asyncio
import plistlib
import sys
from pathlib import Path

from .store import uid

PROTECTED = (
    "keychain",
    "1password",
    "bitwarden",
    "keepass",
    "passwords",
    "lastpass",
    "dashlane",
    "enpass",
    "roboform",
    "protonpass",
    "proton.pass",
)


class MacHost:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.elements = {}
        self.snapshot_id = ""
        self.pid = None
        self.lock = asyncio.Lock()
        self.awake = None

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
            apps = sorted([*directory.glob("*.app"), *directory.glob("*/*.app")])
            if directory == Path("/System/Applications"):
                apps.append(Path("/System/Library/CoreServices/Finder.app"))
            for app in apps:
                try:
                    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
                    name, bundle = app.stem, info["CFBundleIdentifier"]
                    if not isinstance(bundle, str):
                        continue
                    if not any(word in (name + bundle).lower() for word in PROTECTED):
                        found.append({"name": name, "bundle_id": bundle})
                except (OSError, ValueError, KeyError):
                    continue
        return found

    def foreground(self):
        self.check()
        try:
            from AppKit import NSWorkspace
        except ImportError:
            raise ValueError("Install the mac extra from the repository: uv sync --extra mac") from None
        front = NSWorkspace.sharedWorkspace().frontmostApplication()
        if not front or any(word in str(front.bundleIdentifier()).lower() for word in PROTECTED):
            raise ValueError("This application is protected")
        if str(front.bundleIdentifier()) not in {item["bundle_id"] for item in self.apps()}:
            raise ValueError("The foreground application is not permitted")
        return front

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
        except ImportError:
            raise ValueError("Install the mac extra from the repository: uv sync --extra mac") from None
        if not AX.AXIsProcessTrusted():
            raise ValueError("Grant Accessibility to the Python/terminal running OpenDuet in macOS Settings")
        front = self.foreground()
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
        elif action == "key":
            import Quartz

            keys = {
                "RETURN": (36, 0),
                "ESCAPE": (53, 0),
                "TAB": (48, 0),
                "DELETE": (51, 0),
                "LEFT": (123, 0),
                "RIGHT": (124, 0),
                "DOWN": (125, 0),
                "UP": (126, 0),
                "CMD_L": (37, Quartz.kCGEventFlagMaskCommand),
                "CMD_A": (0, Quartz.kCGEventFlagMaskCommand),
                "CMD_F": (3, Quartz.kCGEventFlagMaskCommand),
                "CMD_T": (17, Quartz.kCGEventFlagMaskCommand),
                "CMD_W": (13, Quartz.kCGEventFlagMaskCommand),
                "CMD_Z": (6, Quartz.kCGEventFlagMaskCommand),
            }
            if value not in keys:
                raise ValueError("Choose a supported key: " + ", ".join(keys))
            code, flags = keys[value]
            for down in (True, False):
                event = Quartz.CGEventCreateKeyboardEvent(None, code, down)
                Quartz.CGEventSetFlags(event, flags)
                Quartz.CGEventPostToPid(self.pid, event)
            error = 0
        else:
            operation = {
                "click": "AXPress",
                "open": "AXOpen",
                "raise": "AXRaise",
                "scroll_down": "AXScrollDown",
                "scroll_up": "AXScrollUp",
            }.get(action)
            if not operation:
                raise ValueError("Unsupported native action")
            error = AX.AXUIElementPerformAction(target, operation)
        if error:
            raise ValueError("The application refused the action; observe its current state")
        return {"performed": action}

    async def tick(self):
        if self.enabled and (self.awake is None or self.awake.returncode is not None):
            import os

            self.awake = await asyncio.create_subprocess_exec(
                "/usr/bin/caffeinate",
                "-i",
                "-w",
                str(os.getpid()),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        elif not self.enabled and self.awake and self.awake.returncode is None:
            self.awake.terminate()
            await self.awake.wait()
            self.awake = None

    async def close(self):
        if self.awake and self.awake.returncode is None:
            self.awake.terminate()
            await self.awake.wait()

    async def screenshot(self, task=None):
        self.check()
        # Refuse protected foreground apps before capturing any display pixels.
        await asyncio.to_thread(self.foreground)
        directory = self.runtime.config.data_dir / "attachments"
        directory.mkdir(exist_ok=True, mode=0o700)
        ident = uid()
        path = directory / (ident + ".png")
        await self.command("/usr/sbin/screencapture", "-x", "-D", "1", "-t", "png", str(path))
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
