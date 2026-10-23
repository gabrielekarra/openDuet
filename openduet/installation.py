"""Private local installation, one-use browser sign-in and per-user macOS services."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import plistlib
import secrets
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import httpx

from .config import Config

LABEL = "org.openduet.workspace"


def default_directory():
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/OpenDuet"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "openduet"


def private_write(path, value, *, exclusive=False):
    path = Path(path)
    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as output:
        os.fchmod(output.fileno(), 0o600)
        output.write(value if isinstance(value, bytes) else value.encode())


def read_private(path):
    path = Path(path)
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise ValueError("Private credential files must be owned by you and readable only by you (chmod 600)")
    if hasattr(os, "getuid") and path.stat().st_uid != os.getuid():
        raise ValueError("Private credential file belongs to another user")
    if path.stat().st_size > 2048:
        raise ValueError("Private credential file is too large")
    return path.read_text()


def setup(directory=None):
    root = Path(directory or default_directory()).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    config_path = root / "openduet.toml"
    token_path = root / "workspace.token"
    if not token_path.exists():
        private_write(token_path, secrets.token_hex(32), exclusive=True)
    if not config_path.exists():
        text = f'data_dir = {json.dumps(str(root))}\ntoken_file = {json.dumps(str(token_path))}\nhost = "127.0.0.1"\nport = 8765\nkev_url = "http://127.0.0.1:8768"\n[providers.local]\nkind = "ollama"\nbase_url = "http://127.0.0.1:11434"\nmodel = "qwen3.5:4b"\ncontext_window = 16384\nmax_tokens = 2048\ntemperature = 0.2\n'
        private_write(config_path, text, exclusive=True)
    config = Config.load(config_path)
    if not config.token_file:
        raise ValueError(
            "This existing configuration uses an environment token; choose a new installation directory or configure token_file explicitly"
        )
    config.token()
    return config_path, config


def local_login_url(config):
    if not config.token_file:
        raise ValueError("One-use local sign-in is available for private token_file installations")
    code = secrets.token_urlsafe(32)
    temporary = config.data_dir / ("local-login-" + secrets.token_hex(8))
    private_write(
        temporary,
        json.dumps({"sha256": hashlib.sha256(code.encode()).hexdigest(), "expires": time.time() + 120}),
        exclusive=True,
    )
    temporary.replace(config.data_dir / "local-login.json")
    return f"http://127.0.0.1:{config.port}/#setup={code}"


def consume_local_login(config, code):
    path = config.data_dir / "local-login.json"
    claimed = config.data_dir / ("local-login-claimed-" + secrets.token_hex(8))

    def matches(value):
        return value.get("expires", 0) > time.time() and hmac.compare_digest(
            value.get("sha256", ""), hashlib.sha256(code.encode()).hexdigest()
        )

    try:
        if not matches(json.loads(read_private(path))):
            return False
        path.rename(claimed)  # exactly one concurrent request can claim this file
        try:
            return matches(json.loads(read_private(claimed)))
        finally:
            claimed.unlink(missing_ok=True)
    except (OSError, ValueError, TypeError):
        return False


def service(config_path, action, *, launch_dir=None, run=subprocess.run):
    if sys.platform != "darwin":
        raise ValueError(
            "Background login services are available on macOS. Use Docker Compose for an always-on Linux server."
        )
    config_path = Path(config_path).resolve()
    config = Config.load(config_path)
    root = Path(launch_dir or Path.home() / "Library/LaunchAgents")
    root.mkdir(parents=True, exist_ok=True)
    domain = "gui/" + str(os.getuid())
    logs = config.data_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True, mode=0o700)
    targets = [(LABEL, [sys.executable, "-m", "openduet", "--config", str(config_path)], {})]
    # Both services are separate processes. No model download or inference is
    # triggered by installation; Proactivity has an explicit download action.
    if config.kev_url:
        import importlib.util

        backend = "mlx" if platform.machine() == "arm64" and importlib.util.find_spec("mlx") else "torch"
        if importlib.util.find_spec("torch"):
            targets.append(
                (
                    "org.openduet.kev",
                    [sys.executable, "-c", "from openduet.kev.service import main; main()"],
                    {
                        "OPENDUET_KEV_BACKEND": backend,
                        "OPENDUET_KEV_MODELS": str(config.data_dir / "kev-models"),
                    },
                )
            )
    outcomes = {}
    for label, arguments, environment in targets:
        plist = root / (label + ".plist")
        if action == "install":
            for kind in ("stdout", "stderr"):
                log = logs / (label + "." + kind + ".log")
                if not log.exists():
                    private_write(log, "", exclusive=True)
            values = {
                "Label": label,
                "ProgramArguments": arguments,
                "WorkingDirectory": str(config.data_dir),
                "RunAtLoad": True,
                "KeepAlive": True,
                "ThrottleInterval": 10,
                "EnvironmentVariables": environment,
                "StandardOutPath": str(logs / (label + ".stdout.log")),
                "StandardErrorPath": str(logs / (label + ".stderr.log")),
            }
            private_write(plist, plistlib.dumps(values))
            run(["/bin/launchctl", "bootout", domain + "/" + label], capture_output=True, check=False)
            result = run(
                ["/bin/launchctl", "bootstrap", domain, str(plist)], capture_output=True, check=False
            )
        elif action == "start":
            result = run(
                ["/bin/launchctl", "bootstrap", domain, str(plist)], capture_output=True, check=False
            )
        elif action in {"stop", "uninstall"}:
            result = run(
                ["/bin/launchctl", "bootout", domain + "/" + label], capture_output=True, check=False
            )
            if action == "uninstall":
                plist.unlink(missing_ok=True)
        else:
            result = run(["/bin/launchctl", "print", domain + "/" + label], capture_output=True, check=False)
        outcomes[label] = result.returncode == 0
        if action in {"install", "start"} and result.returncode:
            raise ValueError(
                "macOS did not start the login service. Run this command as the signed-in desktop user; inspect the private logs in "
                + str(logs)
            )
    return {"service": LABEL, "action": action, "running": all(outcomes.values()), "services": outcomes}


def open_console(config, *, browser=True):
    with httpx.Client(trust_env=False, timeout=1) as client:
        for _ in range(60):
            try:
                if client.get(f"http://127.0.0.1:{config.port}/health").status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        else:
            raise ValueError(
                "OpenDuet is not running. Start the service or run openduet --config with your configuration path."
            )
    url = local_login_url(config)
    if browser:
        webbrowser.open(url)
    return url
