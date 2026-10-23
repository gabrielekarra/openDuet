import json
import os
import plistlib
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient

from openduet import installation
from openduet.config import ProviderConfig
from openduet.diagnostics import available_models, model_probe, readiness
from openduet.providers import Reply
from openduet.runtime import Runtime
from openduet.server import create_app
from openduet.store import Store


def installed(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENDUET_TOKEN", raising=False)
    return installation.setup(tmp_path / "installation with spaces")


def test_installation_is_idempotent_private_and_token_stays_out_of_command_lines(tmp_path, monkeypatch):
    path, config = installed(tmp_path, monkeypatch)
    token = config.token()
    assert installation.setup(config.data_dir)[1].token() == token
    assert path.stat().st_mode & 0o077 == 0
    assert os.stat(config.token_file).st_mode & 0o077 == 0
    assert token not in path.read_text()
    config_path = path
    monkeypatch.setattr(installation.sys, "platform", "darwin")
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0)

    result = installation.service(config_path, "install", launch_dir=tmp_path / "launch agents", run=run)
    assert result["running"]
    plist = plistlib.loads((tmp_path / "launch agents" / f"{installation.LABEL}.plist").read_bytes())
    assert plist["ProgramArguments"][-1] == str(config_path)
    assert token not in json.dumps(plist)
    assert all(token not in str(command) for command in calls)
    assert plist["KeepAlive"] and plist["RunAtLoad"]


def test_world_readable_or_symlink_token_is_refused(tmp_path, monkeypatch):
    _, config = installed(tmp_path, monkeypatch)
    path = installation.Path(config.token_file)
    path.chmod(0o644)
    with pytest.raises(ValueError, match="chmod 600"):
        config.token()
    path.chmod(0o600)
    link = tmp_path / "linked"
    link.symlink_to(path)
    config.token_file = str(link)
    with pytest.raises(ValueError):
        config.token()


def test_local_browser_link_is_atomic_one_use_and_does_not_reveal_workspace_token(tmp_path, monkeypatch):
    _, config = installed(tmp_path, monkeypatch)
    link = installation.local_login_url(config)
    code = parse_qs(urlsplit(link).fragment)["setup"][0]
    assert config.token() not in link
    assert code not in (config.data_dir / "local-login.json").read_text()
    assert not installation.consume_local_login(config, "invalid-code")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: installation.consume_local_login(config, code), range(8)))
    assert sum(results) == 1


def test_local_session_rejects_remote_and_replay_but_authenticates_local_console(tmp_path, monkeypatch):
    _, config = installed(tmp_path, monkeypatch)
    app = create_app(config, start_worker=False)
    code = parse_qs(urlsplit(installation.local_login_url(config)).fragment)["setup"][0]
    with TestClient(app, base_url="http://127.0.0.1", client=("198.51.100.1", 123)) as remote:
        assert remote.post("/api/local-session", json={"code": code}).status_code == 403
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 123)) as local:
        assert local.post("/api/local-session", json={"code": code}).status_code == 200
        assert local.get("/api/state").status_code == 200
        assert local.post("/api/local-session", json={"code": code}).status_code == 401
        assert config.token() not in local.get("/api/state").text


async def test_model_probe_checks_actual_tool_protocol_and_never_stores_echoed_secrets(tmp_path, monkeypatch):
    _, config = installed(tmp_path, monkeypatch)
    runtime = Runtime(config, Store(config.data_dir))

    class Good:
        def __init__(self, config):
            pass

        async def complete(self, messages, tools):
            return Reply(
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "openduet_connection_probe",
                                "arguments": '{"value":"connected"}',
                            }
                        }
                    ],
                }
            )

    runtime.provider_factory = Good
    assert (await model_probe(runtime, "local"))["tools"]
    runtime.telegram.save(paired=True, connected=True, owner_id=1, owner_chat=1)
    assert readiness(runtime)["ready"]
    assert runtime.redact(config.token()) == "[REDACTED]"

    class Bad(Good):
        async def complete(self, messages, tools):
            raise ValueError("private-provider-secret")

    runtime.provider_factory = Bad
    assert not (await model_probe(runtime, "local"))["ok"]
    assert "private-provider-secret" not in json.dumps(runtime.store.preference("provider_checks", {}))
    await runtime.close()


async def test_discover_models_uses_native_ollama_contract():
    def handler(request):
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "local:4b"}, {"name": "local:4b"}]})

    models = await available_models(
        ProviderConfig(kind="ollama", base_url="http://127.0.0.1:11434"),
        transport=httpx.MockTransport(handler),
    )
    assert models == ["local:4b"]


def test_model_edit_preserves_private_credential_and_names_do_not_collide(tmp_path, monkeypatch):
    _, config = installed(tmp_path, monkeypatch)
    app = create_app(config, start_worker=False)
    headers = {"Authorization": "Bearer " + config.token()}
    with TestClient(app) as client:
        for name, key in [("a-b", "fixture-first-key"), ("a_b", "fixture-second-key")]:
            result = client.post(
                "/api/models", headers=headers, json={"name": name, "model": "local", "api_key": key}
            )
            assert result.status_code == 200
        a, b = [config.providers[name].api_key_env for name in ("a-b", "a_b")]
        assert a != b
        assert os.environ[a] == "fixture-first-key" and os.environ[b] == "fixture-second-key"
        client.post("/api/models", headers=headers, json={"name": "a-b", "model": "new-local"})
        assert config.providers["a-b"].api_key_env == a
        state = client.get("/api/state", headers=headers).text
        assert "fixture-first-key" not in state and "fixture-second-key" not in state
