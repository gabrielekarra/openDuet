# Self-hosting

## Compose services

Copy `.env.example` to `.env`; replace both placeholders with independent
`openssl rand -hex 32` values. Keep `.env` private. `docker compose up -d --build`
starts workspace (8765), computer, egress, prototypes (8767) and Kev. Public bindings
are loopback by default. Health checks and restart policies keep services up.
The browser's internal Docker network has no direct Internet route.

Persistent volumes are separate: `openduet-data` (database, encrypted vault key,
attachments and artifacts), `computer-data` (browser cookies), `prototype-data`
(publicly addressable opaque prototype files), Kev weights and optional Ollama model volumes.
The computer mounts only its own profile. Never mount Docker's socket, the host
home directory, workspace secrets or database into it.

Run `docker compose --profile ollama up -d` to include Ollama. Pull the desired
model explicitly, then set its URL to `http://ollama:11434/v1` in Settings. The
default Docker configuration instead points at the host's Ollama gateway.
For another private model container, add it to the workspace outbound network.

Compose includes a separate Kev CPU service. Its weights are
not downloaded at startup: start the verified download explicitly from
Proactivity. CPU defaults to qualified INT8 weights with FP32 activations,
LoRA and pointer head. The real CPU runner peaked at 14.48 GiB RSS, including
loading/quantization, and 41.3 s median per event. Allow at least 16 GiB available
for Kev, plus your work model, workspace and OS. `OPENDUET_KEV_DTYPE` can explicitly
select a different precision; that needs its own evaluation. The MLX backend is
for Apple silicon outside Linux Docker and measured 4.75 s median on its runner;
total Metal memory still needs target-device measurement. See [Kev](kev/README.md).
Without Kev, OpenDuet stays in brief-only mode.

## Access and HTTPS

For private console access, forward `ssh -L 8765:127.0.0.1:8765 user@server`.
Telegram long polling works without a public domain. For OAuth callbacks, the
Mini App or issuer webhooks, terminate TLS with your reverse proxy, set
`public_url` to the workspace's HTTPS origin, and forward to port 8765. Preserve
the original Host and scheme. Never expose the computer, proxy or Kev tool ports
publicly. Use a **different HTTPS hostname** for `prototype_url`, proxying 8767.
Its container receives only the prototype volume, without workspace cookies or
APIs. CSP and opaque iframe sandboxing also prevent workspace-origin access.

Supply only intended provider/connector variables to the workspace. In managed
or corporate environments preserve their proxy and CA trust configuration;
Docker builds accept `--secret id=build_ca,src=/path/to/combined-ca.pem`.
For a configured upstream forward proxy, that trusted proxy must also reject
private/metadata destinations: OpenDuet validates DNS before forwarding, but an
upstream HTTP proxy resolves names itself. Without an upstream proxy, OpenDuet
pins the validated public IP. TLS verification remains enabled.

## Always-on VPS

`deploy/cloud-init.yaml` provisions Ubuntu with Docker, clones the public repo,
generates private random tokens and enables an OpenDuet systemd service. Select
that cloud-init file when creating your VPS and configure your SSH key through
your provider. Retrieve the generated workspace token over SSH from
`/opt/openduet/.env`; do not publish that file. Configure a model and accounts
after first login. The template binds the console to loopback.

The cloud-init recipe is supplied for deployment; no paid VM or DNS changes are
created by this repository. Local Compose acceptance is tracked separately from
an actual provider provisioning run.

## Voice, backup and upgrades

For local voice input, install the `voice` extra (Docker build arg
`OPENDUET_VOICE=true`) and download a faster-whisper model separately. Select
its existing directory in Settings. Transcription uses local files only; audio
is bounded to 20 MB and three minutes. There is no speech output/TTS.

Stop the workspace before backing up its volume, or use SQLite's backup API.
Back up the encrypted database and vault key together, plus artifacts and browser
profile as needed. Prefer encrypted backups. Vault rotation re-encrypts all
secrets; an interrupted key-file replacement is recoverable from `.previous`.
An environment-owned encryption key must be rotated in that deployment system.

For upgrades: back up, pull, then `docker compose up -d --build`. Run one workspace
worker only. Database leases/checkpoints and the durable outbox handle restarts;
uncertain external effects and lost Telegram receipts require review before a
retry. See [migration](MIGRATION.md) when moving from the native predecessor.
