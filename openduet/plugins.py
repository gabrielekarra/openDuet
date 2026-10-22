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
        "name": str(metadata.get("name", path.parent.name))[:100],
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
        for directory in (self.bundled, self.directory):
            for path in directory.glob("**/SKILL.md"):
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
                if not item.is_dir() and path.suffix.lower() not in allowed:
                    raise ValueError("Plugin bundles cannot contain executable code")
            candidates = [
                name for name in archive.namelist() if name in {"plugin.json", ".claude-plugin/plugin.json"}
            ]
            if not candidates:
                raise ValueError("A plugin.json or .claude-plugin/plugin.json manifest is required")
            metadata = json.loads(archive.read(candidates[0]))
            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", metadata.get("name", "")):
                raise ValueError("Invalid plugin name")
            if metadata.get("hooks") or metadata.get("commands"):
                raise ValueError("Executable plugin hooks and commands are not supported")
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
