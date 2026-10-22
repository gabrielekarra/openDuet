# OpenDuet

**Your work, moving forward. Your models, your server, your call.**

OpenDuet (formerly Bobb) is an independent, MIT-licensed proactive assistant.
Message it, give it a task, or schedule a morning brief. It prepares work,
uses the tools you connect, and asks you to review external actions. Choose a
local model or a remote provider for each task.

This is a **developer preview**, inspired by the publicly documented Claude
Duet workflows. It is not affiliated with Anthropic and is not a complete
replacement for its proprietary services. The [research and capability matrix](docs/CLAUDE-DUET-RESEARCH.md)
records the sources, implemented paths and remaining gaps without claiming
unverified parity.

## Two ways to use OpenDuet

| | Self-hosted workspace | Native Mac app |
| --- | --- | --- |
| Interface | Responsive web app; add to your phone's home screen | macOS menu bar, hotkeys and native panels |
| Models | OpenAI-compatible servers, Ollama native API, Anthropic API; optional text tool protocol | On-device MLX generation and Kev decisions |
| Tools | Your stdio / Streamable HTTP MCP servers; optional dedicated Chromium | Apple Mail, Calendar, Reminders, Contacts, Messages, files, Shortcuts, browser and MCP |
| Background work | Runs while the server is on, independently of the client | Mac must remain awake and signed in |
| Data | SQLite and browser profile on your server; selected remote providers receive task context | Local memory and inference; engine network isolation retained |

The two runtimes currently have separate data stores. The Swift modules
`BobbApp` / `BobbCore`, the `bobbd` daemon, bundle id and existing Mac data paths
retain their names to preserve compatibility. The shipped app is **OpenDuet.app**.

## Start the workspace

Python 3.12+ and [uv](https://docs.astral.sh/uv/) are required. Start your model
server separately. The default configuration points at Ollama on this machine;
pull a model you want to use before sending a task.

```sh
git clone https://github.com/gabrielekarra/openDuet.git openduet
cd openduet
uv sync --locked
cp openduet.toml.example openduet.toml
# Generate and keep a private access token, then set OPENDUET_TOKEN in your shell:
python -c 'import secrets; print(secrets.token_urlsafe(32))'
export OPENDUET_TOKEN='replace-with-your-generated-token'
uv run --locked openduet --config openduet.toml
```

Open **http://127.0.0.1:8765** and sign in with that token. Configure a model in
`openduet.toml` before sending a message. No paid AI account is needed for a
local model. The token protects the workspace even on localhost.

| Model server | `kind` | `base_url` |
| --- | --- | --- |
| Ollama compatibility API | `openai` | `http://127.0.0.1:11434/v1` |
| Ollama native API | `ollama` | `http://127.0.0.1:11434` |
| LM Studio | `openai` | `http://127.0.0.1:1234/v1` |
| llama.cpp | `openai` | `http://127.0.0.1:8080/v1` |
| vLLM, MLX server, hosted compatible APIs | `openai` | Your server's compatible base URL |
| Anthropic | `anthropic` | `https://api.anthropic.com/v1` |

Use the exact model id advertised by your server. Set `api_key_env` only for
services that require a credential. `tools = false` uses a validated JSON text
protocol for models without native function calling. Protocol compatibility
does not establish a model's ability to perform a task: small models, context
windows and provider-specific restrictions still matter.

## What is implemented

- **Home & channels:** durable conversations, named channels, per-task model
  selection, chat search, shared reviewed memory, memory import/export and deletion.
- **Tasks & approvals:** persistent queue, checked tool arguments, exact action
  review, one-use approvals, cancellation, explicit recovery and user-only completion.
  Read/preparation calls in a batch continue while another call awaits approval.
- **Routines:** scheduled briefs, connected-account check-ins, meeting preparation
  and follow-ups; no overlapping copies of the same pending assignment. Accounts
  must be connected, and the service must remain running.
- **Make:** real DOCX documents, XLSX data workbooks and PPTX decks, plus Markdown,
  CSV, text and downloadable HTML dashboards. Text artifacts can be edited as new
  versions. Generated HTML is downloaded rather than run in the signed-in app.
- **Connections:** MCP discovery and tools over stdio and Streamable HTTP. Configure
  Gmail, Calendar, Drive, Slack, Stripe or any other compatible server you authorize.
  Disconnect takes effect before the next call. No accounts are preconnected.
- **Skills:** reusable instructions in Settings. Instructions do not grant powers.
  The [small business skill](skills/small-business/SKILL.md) covers invoice reminders,
  payroll preparation, contract drafts and meeting briefs using your connected data.
- **Browser:** optional dedicated Chromium profile, exact HTTPS host allowlist,
  reviewed interactions and a separate private login form. Deploy on your own VM
  for a separate computer; OpenDuet does not provision cloud VMs for you.
- **Voice & notifications:** optional local Whisper transcription, local browser
  speech voices where available, in-app/browser notifications and an optional
  notification relay for alerts after the client closes.
- **Usage:** turn and daily token limits, provider token counts or documented
  estimates, and a ledger that includes background tasks.

See [setup, deployment and boundaries](docs/SELF-HOSTING.md).

## Run on a server

```sh
# First set a private OPENDUET_TOKEN in your environment.
# Edit openduet.docker.toml for your model endpoint.
docker compose up --build -d
```

Docker publishes only on the host's loopback interface. For phone/remote access,
use your own authenticated private network or an HTTPS reverse proxy. Keep one
service instance per data directory. Back up the named volume, which contains
private conversations, memory and browser sessions. A local model on a laptop
cannot respond while that laptop is off; run the model on the server as well if
you need continuous local inference.

## Native Mac app

The existing Apple silicon app remains available with its original automation,
local memory, proactive screen context and offline voice features. See the
[native Mac guide](docs/NATIVE-MAC.md) for requirements, model downloads, permissions,
workflow evidence and packaging.

```sh
scripts/run.sh
# Self-contained macOS app/DMG:
scripts/package.sh
```

## Development

```sh
uv sync --locked --extra dev
uv run pytest tests/runtime -q
uv run ruff check --select E4,E7,E9,F,I,UP openduet tests/runtime
# Existing native components:
(cd BobbApp && swift test -j 1)
(cd bobbd && uv sync --frozen && uv run pytest -q -m 'not slow')
```

[Contributions](CONTRIBUTING.md) are welcome. Native execution still requires
macOS acceptance tests; protocol fixtures do not prove real delivery or task
quality. No paid provider, real inbox or payment was used to validate this preview.

## License

[MIT](LICENSE), copyright Gabriele Karra and contributors. Third-party code,
models and speech components retain their [own licenses](THIRD_PARTY_NOTICES.md).
Historical versions remain under the terms distributed with those versions.
