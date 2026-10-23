from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


@dataclass
class ProviderConfig:
    kind: str = "openai"
    model: str = "qwen3.5:4b"
    base_url: str = "http://127.0.0.1:11434/v1"
    api_key_env: str = ""
    tools: bool = True
    max_tokens: int = 4096
    vision: bool = False
    thinking: bool = False

    def __post_init__(self):
        url = urlsplit(self.base_url)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
            raise ValueError("Provider requires an HTTP(S) URL without embedded credentials")
        if self.kind not in {"openai", "anthropic", "ollama"}:
            raise ValueError("Provider kind must be openai, anthropic or ollama")


@dataclass
class ConnectorConfig:
    url: str = ""
    command: str = ""
    args: list[str] = field(default_factory=list)
    env_names: list[str] = field(default_factory=list)
    header_env: dict[str, str] = field(default_factory=dict)
    safe_tools: list[str] = field(default_factory=list)
    excluded_tools: list[str] = field(default_factory=list)
    credential_ref: str = ""
    poll_tool: str = ""
    poll_arguments: dict = field(default_factory=dict)
    event_kind: str = "mail.received"
    poll_seconds: int = 600
    cursor_argument: str = ""

    def __post_init__(self):
        if bool(self.url) == bool(self.command):
            raise ValueError("Connector requires exactly one of url or command")
        if self.url:
            url = urlsplit(self.url)
            if (
                (
                    url.scheme != "https"
                    and not (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"})
                )
                or url.username
                or url.password
            ):
                raise ValueError("MCP requires HTTPS or explicitly configured loopback HTTP")


@dataclass
class Config:
    data_dir: Path = field(default_factory=lambda: Path(".runtime/openduet"))
    token_file: str = ""
    host: str = "127.0.0.1"
    port: int = 8765
    default_provider: str = "local"
    providers: dict[str, ProviderConfig] = field(default_factory=lambda: {"local": ProviderConfig()})
    connectors: dict[str, ConnectorConfig] = field(default_factory=dict)
    skills_dir: str = "skills"
    browser: bool = False
    browser_hosts: list[str] = field(default_factory=list)
    voice_model: str = ""
    max_turns: int = 20
    daily_token_budget: int = 200000
    notify_url: str = ""
    notify_token_env: str = ""
    public_url: str = ""
    kev_url: str = ""
    computer_url: str = ""
    prototype_port: int = 8767
    prototype_url: str = "http://127.0.0.1:8767"
    wallet_allow_live: bool = False

    def __post_init__(self):
        for name in ("public_url", "prototype_url", "computer_url", "kev_url"):
            value = getattr(self, name)
            if not value:
                continue
            url = urlsplit(value)
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username
                or url.password
                or any(character.isspace() or character in "'\";" for character in value)
            ):
                raise ValueError(name + " requires an HTTP(S) origin without credentials")
            if name == "public_url" and (url.scheme != "https" or url.query or url.fragment):
                raise ValueError("public_url must be a public HTTPS URL for Telegram Mini Apps")

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        raw = tomllib.loads(path.read_text()) if path else {}
        providers = {n: ProviderConfig(**v) for n, v in raw.pop("providers", {}).items()}
        connectors = {n: ConnectorConfig(**v) for n, v in raw.pop("connectors", {}).items()}
        if raw.pop("computers", None) or raw.pop("remote_session_seconds", None):
            raise ValueError(
                "VNC was retired. Enable on-demand Mac access in Settings instead; see docs/REMOTE-ACCESS.md"
            )
        cfg = cls(
            **raw,
            **({"providers": providers} if providers else {}),
            connectors=connectors,
        )
        cfg.data_dir = Path(cfg.data_dir).expanduser().resolve()
        if cfg.default_provider not in cfg.providers:
            raise ValueError("default_provider does not name a configured provider")
        if cfg.max_turns < 1 or cfg.daily_token_budget < 1:
            raise ValueError("Turn and token budgets must be positive")
        return cfg

    def token(self) -> str:
        token = os.environ.get("OPENDUET_TOKEN", "")
        if not token and self.token_file:
            from .installation import read_private

            token = read_private(Path(self.token_file).expanduser()).strip()
        if len(token) < 24:
            raise ValueError("Set OPENDUET_TOKEN to a random secret of at least 24 characters")
        return token
