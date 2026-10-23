import json

import pytest

from openduet.config import Config
from openduet.delivery import required_format
from openduet.providers import Reply
from openduet.runtime import Runtime
from openduet.store import Store


def test_file_obligation_only_applies_to_explicit_file_assignments():
    assert required_format("Create a Markdown artifact for the meeting") == "md"
    assert required_format("Crea un foglio di calcolo con queste ipotesi") == "xlsx"
    assert required_format("How do I create a PDF?") == ""
    assert required_format("Write an email about PDF exports") == ""


@pytest.mark.parametrize("cooperates", [True, False])
async def test_claimed_file_is_not_ready_until_a_real_artifact_exists(tmp_path, cooperates):
    turns = 0

    class Model:
        def __init__(self, config):
            pass

        async def complete(self, messages, tools):
            nonlocal turns
            turns += 1
            if cooperates and turns == 2:
                return Reply(
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "file",
                                "type": "function",
                                "function": {
                                    "name": "create_artifact",
                                    "arguments": json.dumps(
                                        {
                                            "title": "Real file",
                                            "format": "md",
                                            "content": "# Meeting checklist\n\n- Confirm the agenda.\n- Review next steps.",
                                        }
                                    ),
                                },
                            }
                        ],
                    }
                )
            return Reply(
                {"role": "assistant", "content": "The file is ready. Download it here: sandbox:/made-up.md"}
            )

    runtime = Runtime(Config(data_dir=tmp_path), Store(tmp_path), provider_factory=Model)
    task = runtime.store.new_task("main", "Create a Markdown artifact with a meeting checklist", "local")
    await runtime.run_task(task)
    state = runtime.store.task(task)
    assert state["status"] == ("ready" if cooperates else "blocked")
    assert bool(runtime.store.rows("SELECT * FROM artifacts WHERE task=?", (task,))) == cooperates
    if not cooperates:
        assert runtime.store.rows("SELECT * FROM messages WHERE task=? AND role='assistant'", (task,)) == []
    await runtime.close()
