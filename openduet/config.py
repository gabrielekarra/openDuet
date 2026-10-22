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
    host: str = "127.0.0.1"
    port: int = 8765
    default_provider: str = "local"
    providers: dict[str, ProviderConfig] = field(default_factory=lambda: {"local": ProviderConfig()})
    connectors: dict[str, ConnectorConfig] = field(default_factory=dict)
    browser: bool = False
    browser_hosts: list[str] = field(default_factory=list)
    voice_model: str = ""
    max_turns: int = 20
    daily_token_budget: int = 200000
    notify_url: str = ""
    notify_token_env: str = ""

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        raw = tomllib.loads(path.read_text()) if path else {}
        providers = {n: ProviderConfig(**v) for n, v in raw.pop("providers", {}).items()}
        connectors = {n: ConnectorConfig(**v) for n, v in raw.pop("connectors", {}).items()}
        cfg = cls(**raw, **({"providers": providers} if providers else {}), connectors=connectors)
        cfg.data_dir = Path(cfg.data_dir).expanduser().resolve()
        if cfg.default_provider not in cfg.providers:
            raise ValueError("default_provider does not name a configured provider")
        if cfg.max_turns < 1 or cfg.daily_token_budget < 1:
            raise ValueError("Turn and token budgets must be positive")
        return cfg

    def token(self) -> str:
        token = os.environ.get("OPENDUET_TOKEN", "")
        if len(token) < 24:
            raise ValueError("Set OPENDUET_TOKEN to a random secret of at least 24 characters")
        return token
