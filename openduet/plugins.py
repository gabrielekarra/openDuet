"""Declarative Agent Skills/Claude plugin bundles. Installation never runs plugin code."""

from __future__ import annotations

import io
import json
import re
import shutil
import zipfile
from pathlib import Path

import yaml


def skill(path):
    text = path.read_text()[:100000]
    metadata = {}
    if text.startswith("---\n"):
        _, front, body = text.split("---", 2)
        metadata = yaml.safe_load(front) or {}
    else:
        body = text
    return {
        "name": str(metadata.get("name", path.parent.name if path.name == "SKILL.md" else path.stem))[:100],
        "description": str(metadata.get("description", body.splitlines()[0] if body else ""))[:1000],
        "body": body.strip(),
    }


class Plugins:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.directory = runtime.config.data_dir / "plugins"
        self.directory.mkdir(exist_ok=True, mode=0o700)
        self.bundled = Path(__file__).parent / "bundled"

    def skills(self):
        items = {}
        for directory in (self.bundled, self.directory, Path(self.runtime.config.skills_dir)):
            for path in [*directory.glob("**/SKILL.md"), *directory.glob("**/commands/*.md")]:
                if path.is_symlink():
                    continue
                item = skill(path)
                items[item["name"]] = item
        for name, body in self.store.preference("skills", {}).items():
            items[name] = {"name": name, "description": "User-provided skill: " + name, "body": body}
        return items

    def descriptions(self):
        return [{"name": item["name"], "description": item["description"]} for item in self.skills().values()]

    def load(self, name):
        item = self.skills().get(name)
        if not item:
            raise ValueError("Skill not installed")
        return item["body"]

    def inspect(self, data):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            files = archive.infolist()
            if len(files) > 300 or sum(item.file_size for item in files) > 10_000_000:
                raise ValueError("Plugin archive exceeds limits")
            allowed = {".md", ".json", ".txt", ".png", ".svg"}
            for item in files:
                path = Path(item.filename)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or (item.external_attr >> 16) & 0o170000 == 0o120000
                ):
                    raise ValueError("Invalid plugin path")
                if (
                    not item.is_dir()
                    and path.suffix.lower() not in allowed
                    and path.name not in {"LICENSE", "NOTICE", ".gitignore"}
                ):
                    raise ValueError("Plugin bundles cannot contain executable code")
            candidates = [
                name for name in archive.namelist() if name in {"plugin.json", ".claude-plugin/plugin.json"}
            ]
            if not candidates:
                raise ValueError("A plugin.json or .claude-plugin/plugin.json manifest is required")
            metadata = json.loads(archive.read(candidates[0]))
            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", metadata.get("name", "")):
                raise ValueError("Invalid plugin name")
            if metadata.get("hooks"):
                raise ValueError("Executable plugin hooks are not supported")
            declared = metadata.get("commands", [])
            if isinstance(declared, str):
                declared = [declared]
            if not isinstance(declared, list) or any(
                not isinstance(item, str)
                or Path(item).is_absolute()
                or ".." in Path(item).parts
                or Path(item).suffix not in {"", ".md"}
                for item in declared
            ):
                raise ValueError("Plugin commands must be declarative Markdown")
            connectors = metadata.get("connectors", [])
            if ".mcp.json" in archive.namelist():
                connectors += list(json.loads(archive.read(".mcp.json")).get("mcpServers", {}).values())
            if any(item.get("command") for item in connectors):
                raise ValueError("Plugin executable connectors need operator configuration")
            return metadata | {"connectors": connectors, "files": [item.filename for item in files]}

    def install(self, data):
        metadata = self.inspect(data)
        target = self.directory / metadata["name"]
        if target.exists():
            raise ValueError("Uninstall this plugin before installing a replacement")
        temporary = self.directory / (metadata["name"] + ".partial")
        temporary.mkdir(mode=0o700)
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                archive.extractall(temporary)
            temporary.replace(target)
        except BaseException:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        self.store.event("plugin_installed", metadata["name"])
        return metadata

    def uninstall(self, name):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", name):
            raise ValueError("Invalid plugin name")
        shutil.rmtree(self.directory / name, ignore_errors=True)
        self.store.event("plugin_uninstalled", name)

    def listing(self):
        result = []
        for root in (self.bundled, self.directory):
            for path in root.glob("*/plugin.json"):
                result.append(json.loads(path.read_text()))
            for path in root.glob("*/.claude-plugin/plugin.json"):
                result.append(json.loads(path.read_text()))
        return result

    def connections(self):
        """Directory suggestions only: installing never connects an account."""
        entries = []
        for plugin in self.listing():
            root = self.bundled / plugin["name"]
            if not root.exists():
                root = self.directory / plugin["name"]
            connectors = list(plugin.get("connectors", []))
            if (root / ".mcp.json").is_file():
                values = json.loads((root / ".mcp.json").read_text()).get("mcpServers", {})
                connectors += [{"name": key, **value} for key, value in values.items()]
            for index, connector in enumerate(connectors):
                entries.append(
                    {
                        "id": plugin["name"] + "-" + str(index),
                        "name": connector.get("name", plugin["name"]),
                        "url": connector.get("url", ""),
                        "plugin": plugin["name"],
                        "description": connector.get("description", plugin.get("description", "")),
                    }
                )
        return entries


def local_archive(directory):
    """Create a bounded static bundle, refusing links before reading their targets."""
    directory = Path(directory).resolve()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        total, count = 0, 0
        for path in directory.rglob("*"):
            relative = path.relative_to(directory)
            if ".git" in relative.parts:
                continue
            if path.is_symlink():
                raise ValueError("Plugin sources cannot contain symbolic links")
            if not path.is_file():
                continue
            count += 1
            total += path.stat().st_size
            if count > 300 or total > 10_000_000:
                raise ValueError("Plugin source exceeds limits")
            archive.writestr(str(relative), path.read_bytes())
    return output.getvalue()


def select_plugin(root, name):
    if not name:
        return root
    manifest = root / ".claude-plugin" / "marketplace.json"
    entries = json.loads(manifest.read_text()).get("plugins", [])
    selected = next((item.get("source") for item in entries if item.get("name") == name), None)
    if not isinstance(selected, str) or not selected.startswith("./"):
        raise ValueError(
            "Select a local declarative entry; remote repositories need separate source approval"
        )
    destination = (root / selected).resolve()
    if not destination.is_relative_to(root.resolve()) or not destination.is_dir():
        raise ValueError("Marketplace plugin path must stay in its reviewed repository")
    return destination


def main():
    import argparse
    import os
    import subprocess
    import tempfile

    import httpx

    from .config import Config
    from .runtime import Runtime
    from .store import Store

    parser = argparse.ArgumentParser(
        description="Inspect/install static plugins from operator-reviewed sources"
    )
    parser.add_argument("source", help="Local directory/zip, HTTPS Git URL, or HTTPS marketplace JSON")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--plugin", help="Plugin name in a marketplace")
    parser.add_argument("--revision", help="Pinned full Git commit id")
    parser.add_argument(
        "--allow-source", action="store_true", help="Operator approval for this exact remote source"
    )
    parser.add_argument(
        "--install", action="store_true", help="Install after inspecting the displayed additions"
    )
    args = parser.parse_args()
    config = Config.load(args.config)
    runtime = Runtime(config, Store(config.data_dir))
    source = args.source
    if source.startswith("https://"):
        allowed = runtime.store.preference("plugin_sources", [])
        if source not in allowed and not args.allow_source:
            raise SystemExit("Remote plugin source needs operator --allow-source approval")
        if args.allow_source:
            runtime.store.set_preference("plugin_sources", sorted(set(allowed + [source])))
        if source.endswith(".json"):
            response = httpx.get(source, timeout=20, follow_redirects=False)
            response.raise_for_status()
            if len(response.content) > 1_000_000:
                raise SystemExit("Marketplace exceeds limit")
            entries = response.json().get("plugins", [])
            entry = next((entry for entry in entries if entry.get("name") == args.plugin), None)
            if not entry:
                print(
                    json.dumps(
                        [
                            {
                                key: value
                                for key, value in item.items()
                                if key in {"name", "description", "source"}
                            }
                            for item in entries
                        ],
                        indent=2,
                    )
                )
                return
            selected = entry["source"]
            if isinstance(selected, dict):
                source = selected.get("url") or "https://github.com/" + selected["repo"] + ".git"
            elif selected.startswith("./"):
                raise SystemExit(
                    "Local marketplace paths require downloading and reviewing the repository first"
                )
            else:
                source = selected
            # Marketplace approval is not approval of arbitrary additional repositories.
            if source not in runtime.store.preference("plugin_sources", []):
                raise SystemExit("Review the selected plugin source separately: " + source)
        if (
            not source.startswith("https://")
            or not args.revision
            or not re.fullmatch(r"[0-9a-f]{40}", args.revision)
        ):
            raise SystemExit(
                "Remote plugins require an HTTPS Git URL and a pinned --revision (40 hex characters)"
            )
        with tempfile.TemporaryDirectory() as temporary:
            environment = os.environ | {
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_TERMINAL_PROMPT": "0",
            }
            options = [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "protocol.ext.allow=never",
                "-c",
                "protocol.file.allow=never",
            ]
            destination = Path(temporary) / "plugin"
            subprocess.run(
                options + ["clone", "--no-checkout", "--", source, str(destination)],
                env=environment,
                check=True,
                capture_output=True,
                timeout=120,
            )
            subprocess.run(
                options + ["-C", str(destination), "checkout", "--detach", args.revision],
                env=environment,
                check=True,
                capture_output=True,
                timeout=30,
            )
            data = local_archive(select_plugin(destination, args.plugin))
    else:
        path = Path(source)
        data = local_archive(select_plugin(path, args.plugin)) if path.is_dir() else path.read_bytes()
    metadata = runtime.plugins.inspect(data)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    if args.install:
        runtime.plugins.install(data)
        print("Installed. Connector accounts remain disconnected; default check-ins require confirmation.")
