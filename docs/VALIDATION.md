# Validation record — 24 October 2026

Verification for the OpenDuet **0.4.0rc3** release candidate. Disposable
Telegram/provider/issuer transports contain no user accounts or private data.
Real models, Chromium, LibreOffice, TLS mail transports and macOS launchd are
identified separately below. The [CI workflow](../.github/workflows/ci.yml)
repeats the runtime, Mac, Office, research, console and isolated-computer checks.
[All five jobs passed after the mail changes](https://github.com/gabrielekarra/openDuet/actions/runs/39945162320).
The distribution workflow records its source commit, isolated-installation check
and checksummed downloadable artifacts. GitHub Release publication currently
returns 403 for the connected integration; source-archive installation remains public.

| Check | Observed result |
| --- | --- |
| Runtime/policy/transport/integration tests | **211 passed** locally (current Unreleased connector work), including the optional Torch/Quanto contract; the basic CI install skips that numerical test |
| Separate specialist research package | **87 passed**, repeated in CI |
| Ruff E4/E7/E9/F/I/UP | Passed |
| Restart recovery | Actual SIGKILL → same database/session → automatic safe task completion → exactly one document to the original chat/topic |
| OAuth/account boundaries | PKCE, single-use/expired state, confidential post/basic clients, rotating refresh serialization, stale callback/discovery/revocation and replacement credentials |
| Event ingestion | Actual HTTP MCP provider-shaped Gmail/Calendar/Slack/Stripe pages; read state, calendar edits, dedup, terminal cursors, error preservation and disconnect race |
| Source provenance | Exact XLSX/CSV/DOCX/PPTX/PDF locators, SHA snapshots, task boundaries, repeated revisions, unknown-ID refusal; actual Office/PDF internal links and excerpts |
| File UI acceptance | Chromium uploads XLSX → read_attachment → cited DOCX → exact cell excerpt → actual document download; 1440/768/390 px screenshots |
| Connector contract runner | Explicit opt-in; actual HTTP MCP read-only contract; field failure, disconnected/consequential refusal and private report checks |
| Real local work LLM | Ollama 0.40.9 + Qwen3.5:4b, native and text tools; actual deliverable and exactly-once approved memory; [report](benchmarks/local-model-2026-10-23.json) |
| Private installation | Fresh wheel installed outside the repository; server, private token file, one-use browser login and service readiness passed |
| Actual macOS login service | GUI launchd install → terminate process → automatic restart → persistent session → uninstall; [report](benchmarks/mac-service-2026-10-23.json) |
| Direct email | Actual loopback TLS IMAP + implicit-TLS/STARTTLS SMTP, certificate/hostname verification; read-only dedup, exact approved send and disconnect passed; missing STARTTLS refused before AUTH |
| Chromium console | Pair bot → Telegram task → shared Make file → approval → confidential OAuth → real HTTP MCP discovery/tool task → mail/calendar → chat/UI brief preferences → disconnect |
| Responsive UI | Seven views at 375/1280 px, light/dark; 28 screenshots in CI artifact |
| Lighthouse 13.5.0 | Telegram **100**, Tasks **100**, no failing audits |
| Real Chromium prototype | Runnable JS; opaque storage; parent credentials, workspace API and network inaccessible |
| Real Docker Chromium computer | Public example.com; no workspace secrets/DB; private/metadata URL and injected POST denied |
| Real LibreOffice | 12-month formula forecast recalculates; PPTX renders into actual PNG previews |
| Real Kev seed | Torch INT8 **79.7%**, MLX **78.1%** typed accuracy; both quality gates passed |
| Real Kev additional corpus | 24 EN/IT cases, 128 answers: **89.8%** both backends; precision 100%, recall 50%, no hostile interruptions |
| Actual Torch/MLX parity | Qualified BF16/MLX seed reference **64/64**, delta **0.01935**; default INT8 seed **98.44%**, additional **100%**, deltas **0.02229 / 0.03192**; precision-specific results |
| Earlier complete Compose startup | Workspace, isolated computer, egress, prototype origin and CPU Kev service healthy; internal access passed |
| Python distribution | 0.4.0rc1 source distribution and wheel built; clean wheel installation and real foreground startup passed |

[Real benchmark details](benchmarks/README.md) include source runs, model digests,
corpus fingerprints, original failed results, memory, latency and statistical
limits. The fixed gates were not lowered to admit the model. The additional
corpus detected only **4/8** labelled urgent events as interruptions; passing
these small samples does not establish production calibration or personal utility.

Reproduce the central checks:

```sh
uv sync --locked --extra dev --extra browser
uv run --no-sync pytest tests/runtime -q
uv run --no-sync ruff check --select E4,E7,E9,F,I,UP openduet tests/runtime
uv run --no-sync openduet-kev-eval
uv run --no-sync python scripts/check_installation.py
uv build
(cd specialist && uv sync --frozen && uv run --no-sync pytest -q)
```

The default Kev evaluation uses synthetic logits: adapter/policy checks only.
Install `--extra kev` and run the [real benchmark](kev/README.md) to evaluate CPU
inference. On Apple silicon use `--extra mlx`. Model downloads are explicit.
The real local work-model check is a separate manual
[workflow](../.github/workflows/local-model.yml); it downloads and runs a real model.

Console checks need Chromium and the disposable server in
`tests/fixtures/openduet_preview.py`; CI gives the exact startup/environment.
`browser_smoke.py`, `prototype_smoke.py` and `scripts/check_accessibility.py`
exercise navigation, actual sandboxing and Lighthouse. `scripts/check_office.py`
requires LibreOffice/Poppler. `scripts/check_computer.py` requires Docker and an
image built with `OPENDUET_BROWSER=true`.

## Evidence boundaries

The earlier full Compose startup used separate core/all-extras validation images
to fit the development worker's Docker vfs storage. Commands, networks, health
checks and volumes came from the actual Compose file. Browser and Office checks
used their actual installed runtimes. The development worker has an 8 GiB memory
limit; pinned-model CPU/MLX inference ran on the identified GitHub runners.
CPU INT8 peaked at **14.48 GiB process RSS** and 41.3 s median per event. MLX was
4.75 s median; macOS process RSS excludes Metal memory. Allow room for the work
model and OS as well; no 8 GiB whole-product memory claim is made.

Mac CI imports the actual PyObjC frameworks and exercises launchd. Accessibility
and Screen Recording grants, installed-app interactions, sleep behavior and
screenshot delivery still require the user's own Mac. `doctor` reads readiness
from the running service, so it reports the service's permissions and interpreter;
when the service is stopped, the diagnostic explicitly reports that condition.
Use the [Mac quickstart](QUICKSTART-MAC.md) or [Italian guide](QUICKSTART-MAC.it.md).

Actual BotFather pairing, real provider accounts/OAuth scopes, eligible issuer
sandbox/webhook, password-manager accounts, Whisper audio quality and paid VPS
provisioning require those environments. Their fixtures do not certify live
acceptance. The [issue tracker](IMPLEMENTATION-TRACKER.md) records these boundaries.
No full behavioral equivalence to Claude Duet or live payment acceptance is asserted.

The latest real MLX hardware run exposed 7 GiB physical RAM and measured a 4.52 GiB Metal allocator peak. [Measurements and provenance](benchmarks/kev-mlx-acceptance-metal-2026-10-23.md) preserve the exact boundary; Metal bytes must not be added to process RSS.

The component update followed the existing app design and was inspected in real Chromium at 1440, 768 and 390 px. The optional design skill reference/scripts were not available through its package, so no skill-inspector score is claimed. Browser assertions, screenshots and interaction/download checks are the verification evidence.

## 24 October acceptance reconciliation

The qualified BF16/MLX fixed-record reference was rechecked directly from the
published backend JSON reports: matching corpus/questions, 12 cases, 64 answers,
zero label flips and maximum probability delta 0.019351358453341794. This was a
comparison of existing real inference outputs, not a new inference run. The
original successful [workflow](https://github.com/gabrielekarra/openDuet/actions/runs/39933339239)
and both source reports remain unchanged. INT8's seed flip and unmeasured target
hardware remain explicit in [Portable Kev](kev/README.md).

The naming cleanup preserves the original native corpus in an immutable source
archive with its [SHA-256 and download command](kev/historical-benchmarks/ARCHIVE.md).
All tracked UTF-8 source/config/document files were scanned, including SVG and
web manifest: the old product name is retained only in CHANGELOG history.
The upstream inference sources and all portable frozen reference JSON are unchanged.
The research action description was renamed; research checkpoints need retraining
before comparison because option bytes changed. No trained checkpoint is bundled.

The [17-service guide](LAUNCH-CONNECTORS.md) distinguishes hosted endpoints,
local bridges, OAuth requirements, scopes, account entitlements and unsupported
workflows. It documents Gusto's dedicated-profile/manual-all-calls requirements; the guide
does not certify live provider access.

The recovered connector work now passes **211 runtime tests** and Ruff. All 17
schema-derived service fixtures cross actual MCP discovery and HTTP/stdio
read/write transport, source capture, event ingestion/deduplication and exact
one-use review. The fixture names/records are illustrative and synthetic, not
captured private sessions or a vendor tool catalogue. Gusto's official endpoint
automatically enforces a fresh dedicated profile, all-call confirmation,
no background polling, no other-account tools and no shared/prior-task context;
reservation survives disconnect. TOML cannot mix it with another account/history.

Real Chromium console acceptance passed with 28 responsive/dark screenshots and
checks that operator bridges show setup links instead of blank Connect actions.
The current directory has 12 prefilled hosted endpoints and 5 operator bridges.
Published code is verified again by the full push-triggered CI workflow.

The existing Ubuntu/QEMU guest was resumed after the environment outage and
reached SSH. Cloud-init then failed: the nested VM could not reach the configured
outbound proxy for Ubuntu packages or GitHub clone, so Docker/workspace did not
start. Its disposable SSH user also lacks passwordless sudo for recovery probes.
The [failed acceptance record](benchmarks/cloud-vm-2026-10-24.json) preserves the
image/recipe fingerprints and exact boundary. No workspace-startup, restart or
provider-deployment pass is inferred from it. See [remaining steps](PENDING-ACCEPTANCE.md).
