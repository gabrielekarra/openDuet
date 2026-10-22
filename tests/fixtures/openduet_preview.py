"""Disposable UI fixture. No real model, user data or external accounts are used."""
import json
import os
from pathlib import Path

from openduet.config import Config
from openduet.providers import Reply
from openduet.server import create_app


class PreviewProvider:
    def __init__(self, config):
        pass

    async def complete(self, messages, tools):
        if messages[-1]["role"] == "tool":
            return Reply({"role": "assistant", "content": "The preview draft is ready. Review it in Make."}, 30, 20)
        request = messages[-1].get("content", "")
        if "remember" in request.lower():
            name, args = "remember", {"content": "I prefer morning meetings. UI test fixture."}
        else:
            name, args = "create_artifact", {"title": "A little space for the week", "format": "md",
                                             "content": "# Weekly brief\n\nA synthetic draft from the UI fixture.\n\n- Prepare the meeting brief.\n- Review next steps.\n\nSource: fixture, no connected accounts."}
        return Reply({"role": "assistant", "content": "", "tool_calls": [
            {"id": "preview-call", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}, 40, 30)


app = create_app(Config(data_dir=Path(os.environ.get("OPENDUET_PREVIEW_DATA", "/tmp/openduet-ui-preview"))),
                 provider_factory=PreviewProvider)
