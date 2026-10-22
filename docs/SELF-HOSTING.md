# Self-hosting OpenDuet

For viewing and controlling the computer itself, see [remote desktop access](REMOTE-ACCESS.md).

## Models

Copy `openduet.toml.example` to `openduet.toml`. Restart after editing server
configuration. Select a named provider in the composer or routine form. Existing
tasks retain their chosen provider. Their active context consists of recent
channel messages, reviewed shared memory, enabled skill instructions and tool
results. Context is bounded but is not automatically summarized to fit every
model's token window. A rejected or failed model request is visible as a task
failure, never converted into a successful action.

The service ships no model weights. Ollama, LM Studio, llama.cpp, vLLM and MLX
servers must be installed and started separately. Use an OpenAI-compatible
Chat Completions endpoint, the native Ollama API or the Anthropic Messages API.
For Google/OpenRouter/other compatible services, use their documented compatible
base URL and model id. No server-specific endpoint is contacted until configured.
Not every proprietary API or raw weight format is supported directly.

`tools = false` adds a text tool protocol for models without native function
calling. It does not improve the model's reasoning or grant permission. Local
inference requires no API key. Remote providers receive the active task context;
use a local endpoint when this content must stay on your infrastructure.

## Run continuously

Run `uv run --locked openduet --config openduet.toml` under your normal process
supervisor, or use `docker compose up --build -d`. The container runs as UID 10001
and persists `/data` in a named volume. Its default example reaches a host model
at `host.docker.internal:11434`. On Linux, Ollama must listen on an interface the
container can reach; restrict that interface with your firewall, or replace the
URL with your model container's internal service name. Never expose an unauthenticated
model API to the public Internet.

Use **one instance / one worker per data directory**. The SQLite queue serializes
tasks in one process. Multi-user tenancy, distributed workers and replicated
browser sessions are not implemented. A dedicated VM gives the browser a separate
computer; a container alone does not provide that same isolation boundary.

Set `OPENDUET_TOKEN` to a private random string of at least 24 characters. The web
client signs in through an HttpOnly, SameSite cookie valid for 12 hours. APIs also
accept `Authorization: Bearer …`. Cookies are Secure on HTTPS. Keep Uvicorn's
trusted proxy settings restricted to your own proxy. Rotate the token to revoke
all current cookies. The service does not log access request bodies or URLs.

Remote use needs your own HTTPS reverse proxy or private network. Docker's
default published port binds to host loopback. A phone's home-screen installation
is a web app, not a native app. Authenticated pages and responses are never cached
by the service worker.

## Connect accounts

Configure a named stdio or Streamable HTTP MCP server. See the example TOML.
Only operator configuration can choose executable commands, URLs, credentials
and tools allowed without review. The model cannot add a connector or change
configuration. Each service needs your own account authorization.

- HTTP credentials are environment bindings such as `header_env = { Authorization = "MAIL_AUTH" }`.
  Set the environment value to the complete required header, including `Bearer`.
- Stdio children receive the named `env_names` plus the SDK's minimal process
  environment. Run only trusted servers: a child process has your OS user's access.
- Discovery supports up to ten pages / 200 tools. Server descriptions and tool
  output are untrusted. Schema/type validation happens before every invocation.
- All tools ask by default. Add genuinely read-only, reviewed names to `safe_tools`
  if needed. Remote read-only annotations do not grant this permission themselves.
- Exclude tools you do not want available, especially financial transfers and trading.
- Disconnect in Connections revokes future access immediately. Re-enable and refresh
  discovery to reconnect. Information already stored in conversation/memory remains
  until you delete it.
- The portable service supports environment-bound credentials, not an OAuth login
  wizard. A compatible token broker/MCP service can own OAuth. The native Mac client
  retains its existing PKCE, Keychain and native browser authorization implementation.
- HTTP redirects are rejected; no effectful call is automatically replayed.

An example business skill is in `skills/small-business/SKILL.md`. Copy its body
into Settings to enable those instructions. Skills are guidance, not executable
plugins or authority to approve actions. Third-party skill bundles must be reviewed
and adapted manually; automatic marketplace installation is not implemented.

## Browser and private login

```sh
uv sync --locked --extra browser
uv run playwright install chromium
```

Set `browser = true` and list exact HTTPS hosts in `browser_hosts`, including
identity providers and necessary resources. For Docker, build with
`docker compose build --build-arg OPENDUET_BROWSER=true` first. For container
voice support, add `--build-arg OPENDUET_VOICE=true` and mount your downloaded
voice model read-only at the path configured in `voice_model`.

Every request, redirect and popup is
checked against this list. HTTP, local-file access, embedded URL credentials,
service workers and WebSockets are blocked. Browser actions ask for approval.
An allowlisted site is still untrusted; use a VM with restricted network access
for stronger boundaries. Do not allow internal administrative hosts.

For a password prompt, pause the task at its approval boundary. In Connections,
check the current page and enter the target CSS selector and private value.
The authenticated endpoint fills the browser directly, without storing the value
in conversation or supplying it to a model. Resume by reviewing the next browser
action. This preview has no streamed browser view or interactive takeover. Never
put credentials or payment card numbers in a task message.

The persistent browser profile contains cookies and must be treated as private
credential material. The application does not encrypt its database/profile at
rest; protect the host, use disk encryption and restrict backups.

## Voice and notifications

`uv sync --locked --extra voice` enables local Whisper transcription. Configure
`voice_model` as a path to already downloaded faster-whisper weights. No implicit
weight downloads occur. Microphone access requires HTTPS or localhost and a
supported browser. Recording stops after 90 seconds; the audio is processed on
your server in a temporary file and deleted after transcription. Text is only
sent as a message when you press Send. The native Mac app keeps its original
on-device Apple speech recognition path.

Browser notifications work while the page is running. For alerts after closing
the client, configure a private `notify_url` (for example your own ntfy topic)
and optional `notify_token_env`. Relay payloads contain only an event category,
not private task text. Configure the corresponding relay client on your phone.

## Tasks, budgets and recovery

Tasks move through queued, running, awaiting approval, ready, and completed.
Only the user marks ready work completed. Failures, blocked budgets and
interrupted tasks need explicit review/resume. The loop checkpoints model output
before tool execution and stores each call's exact arguments separately.
Approval expires after 24 hours and cannot be submitted twice.

An action is marked executing before invoking a connector. If its result is
unknown because of a timeout, cancellation or restart, the task stops. Check the
actual service, use Verify result to record what happened, then resume. A failed
connection does not prove that an email was not sent. The service never claims
exactly-once delivery from external systems.

Each task is bounded by `max_turns`. Explicit Resume grants a fresh turn allowance;
the daily token budget remains in force. Reported token counts are used when
available; otherwise a conservative character estimate is recorded. One active
model call can cross the budget. There is no currency/cost estimator.

Routine start times are stored in UTC and repeat by elapsed interval. They do not
implement a time-zone-aware calendar recurrence engine. Adjust after daylight
saving changes. Identical unresolved assignments do not overlap. A scheduled task
can wait at approval while other queued work continues.

## Data and artifacts

Memory and conversation export is JSON. Import accepts reviewed memory text,
including summaries exported from other assistants. Search indexes are removed
when their owning channel is deleted. Stop active tasks before deleting context;
interrupted/failed checkpoints are cancelled when forgetting memory. Separate
reviewed memories are not removed merely by disconnecting their original app.

Generated HTML is always an attachment with a sandbox policy, never an authenticated
same-origin preview. Review it before opening it elsewhere. Office files contain
basic documents, data cells or slides; there is no arbitrary shell/code runner,
financial formula engine or embedded macro execution. Text edits create versions
and do not overwrite the original artifact.

The deterministic card/identification filters and bound-secret redaction are
limited checks, not an enterprise DLP system. Prompt instructions plus approvals
do not guarantee immunity to prompt injection or reasoning mistakes. Inspect
prepared actions, recipients and amounts before approving them.
