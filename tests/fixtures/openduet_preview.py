"""Disposable UI fixture. No real model, user data or external accounts are used."""

import json
import os
from pathlib import Path

from openduet.config import ComputerConfig, Config
from openduet.providers import Reply
from openduet.server import create_app
from tests.fixtures.rfb_server import FixtureDesktop


class PreviewProvider:
    def __init__(self, config):
        pass

    async def complete(self, messages, tools):
        if messages[-1]["role"] == "tool":
            return Reply(
                {"role": "assistant", "content": "The preview draft is ready. Review it in Make."}, 30, 20
            )
        request = messages[-1].get("content", "")
        if "remember" in request.lower():
            name, args = "remember", {"content": "I prefer morning meetings. UI test fixture."}
        else:
            name, args = (
                "create_artifact",
                {
                    "title": "A little space for the week",
                    "format": "md",
                    "content": "# Weekly brief\n\nA synthetic draft from the UI fixture.\n\n- Prepare the meeting brief.\n- Review next steps.\n\nSource: fixture, no connected accounts.",
                },
            )
        return Reply(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "preview-call",
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(args)},
                    }
                ],
            },
            40,
            30,
        )


desktop = FixtureDesktop().start()
config = Config(
    data_dir=Path(os.environ.get("OPENDUET_PREVIEW_DATA", "/tmp/openduet-ui-preview")),
    computers={"fixture": ComputerConfig(name="Synthetic desktop", port=desktop.server_address[1])},
)
app = create_app(config, provider_factory=PreviewProvider)
static_files = app.router.routes.pop()


@app.get("/api/fixture/desktop-events")
async def fixture_events():
    return desktop.events


app.router.routes.append(static_files)
