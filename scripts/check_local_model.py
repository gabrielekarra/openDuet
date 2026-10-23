"""Real local-model acceptance: no recorded model outputs or external accounts."""

import asyncio
import json
import os
import tempfile
from pathlib import Path

from openduet.config import Config, ProviderConfig
from openduet.diagnostics import model_probe
from openduet.runtime import Runtime
from openduet.store import Store


async def main():
    results = []
    with tempfile.TemporaryDirectory() as temporary:
        config = Config(
            data_dir=Path(temporary),
            providers={
                "local": ProviderConfig(
                    kind="ollama",
                    base_url=os.environ.get("OPENDUET_TEST_MODEL_URL", "http://127.0.0.1:11434"),
                    model=os.environ.get("OPENDUET_TEST_MODEL", "qwen3.5:4b"),
                    max_tokens=2048,
                    context_window=16384,
                    temperature=0.2,
                )
            },
            max_turns=8,
        )
        runtime = Runtime(config, Store(config.data_dir))
        try:
            probe = await model_probe(runtime, "local")
            assert probe["ok"] and probe["tools"], probe
            for native in (True, False):
                config.providers["local"].tools = native
                task = runtime.store.new_task(
                    "main",
                    "Create a Markdown artifact named Launch checklist containing exactly three checklist items: verify the model, pair Telegram, grant Mac permissions. Use create_artifact now, then tell me where it is.",
                    "local",
                )
                await runtime.run_task(task)
                assert runtime.store.task(task)["status"] == "ready", runtime.store.task(task)
                files = runtime.store.rows("SELECT * FROM artifacts WHERE task=?", (task,))
                assert len(files) == 1 and files[0]["format"] == "md", files
                path = config.data_dir / "artifacts" / files[0]["filename"]
                assert path.is_file() and len(path.read_text()) > 40
                text = path.read_text().lower()
                assert (
                    "model" in text
                    and "telegram" in text
                    and ("permission" in text or "accessibility" in text)
                ), text
                results.append(
                    {
                        "protocol": "native" if native else "text",
                        "task_status": "ready",
                        "artifact": files[0]["format"],
                    }
                )
            config.providers["local"].tools = True
            task = runtime.store.new_task(
                "main",
                "Remember this exact preference: I prefer meetings in the morning. Use the remember tool.",
                "local",
            )
            await runtime.run_task(task)
            assert runtime.store.task(task)["status"] == "awaiting_approval", runtime.store.task(task)
            call = runtime.store.rows("SELECT * FROM calls WHERE task=? AND status='pending'", (task,))[0]
            assert call["name"] == "remember"
            assert runtime.store.rows("SELECT * FROM memories") == []
            runtime.approvals.decide(call["id"], "approve")
            await runtime.run_task(task)
            assert runtime.store.task(task)["status"] == "ready"
            assert len(runtime.store.rows("SELECT * FROM memories")) == 1
            results.append({"approval": "exactly one memory after approval"})
        except Exception:
            output = Path(".runtime/local-model-failure.json")
            output.parent.mkdir(exist_ok=True)
            output.write_text(
                json.dumps(
                    {
                        "results": results,
                        "tasks": runtime.store.rows("SELECT id,request,status,history,error FROM tasks"),
                        "calls": runtime.store.rows("SELECT name,arguments,status,result FROM calls"),
                    },
                    indent=2,
                )
                + "\n"
            )
            raise
        finally:
            await runtime.close()
    output = Path(".runtime/local-model-acceptance.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(
        json.dumps({"model": config.providers["local"].model, "results": results, "passed": True}, indent=2)
        + "\n"
    )
    print(output.read_text())


if __name__ == "__main__":
    asyncio.run(main())
