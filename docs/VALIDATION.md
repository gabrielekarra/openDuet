# Validation record — 22 October 2026

Local verification for OpenDuet 0.3.0, before publication. Disposable transports
contain no user accounts, real bot tokens, issuer credentials or private data.
GitHub's [CI workflow](../.github/workflows/ci.yml) repeats the runtime, Mac import,
Office, specialist research, console/accessibility and isolated-computer checks.
Its `workspace-evidence` artifact contains all 28 console screenshots and the
sanitized accessibility report.

| Check | Observed result |
| --- | --- |
| Runtime/policy/transport/integration tests | **136 passed** in 42.17 s |
| Separate specialist research package | **87 passed** in 13.43 s |
| Ruff E4/E7/E9/F/I/UP | Passed |
| Chromium console path | Pair bot → Telegram task → shared Make file → approval passed |
| Responsive UI | All seven views captured at 375/1280 px, light/dark; 28 screenshots |
| Lighthouse 13.5.0 | Telegram **100**, Tasks **100**, no failing audits |
| Real Chromium prototype | Runnable JS; opaque storage; parent credentials, workspace API and network inaccessible |
| Real Docker Chromium computer | Arbitrary public example.com; no workspace secrets/DB; private/metadata URL and injected POST denied |
| Real LibreOffice | 12-month formula forecast recalculates after assumption changes; PPTX renders into actual PNG previews |
| Synthetic Kev benchmark | Adapter/policy gate passed; report in [benchmarks](benchmarks/kev-fixture.md) |
| Python distribution | 0.3.0 source distribution and wheel built successfully |

Reproduce the central checks:

```sh
uv sync --locked --extra dev --extra browser
uv run --no-sync pytest tests/runtime -q
uv run --no-sync ruff check --select E4,E7,E9,F,I,UP openduet tests/runtime
uv run --no-sync openduet-kev-eval
uv build
(cd specialist && uv sync --frozen && uv run --no-sync pytest -q)
```

Console checks need Chromium and the disposable server from
`tests/fixtures/openduet_preview.py`; see CI for the exact startup/environment.
`tests/runtime/browser_smoke.py` saves screenshots, `prototype_smoke.py` exercises
the real opaque origin and `scripts/check_accessibility.py` runs Lighthouse.
`scripts/check_office.py` requires LibreOffice Calc/Impress and Poppler.
`scripts/check_computer.py` requires Docker and an image built with
`OPENDUET_BROWSER=true`; select it with `OPENDUET_TEST_IMAGE`.

## Limits of this evidence

The local worker is Linux with an 8 GiB memory limit. It did not load the pinned
9.48 GB Torch model or run MLX. The fixture report uses synthetic logits and
must never be represented as model accuracy, calibration, parity or throughput.
The [real benchmark workflow](../.github/workflows/kev-benchmark.yml) explicitly
downloads verified weights and publishes failures as well as successes. Model
swaps require real comparison reports and an approved baseline.

Mac bridge contracts are exercised with mocked OS objects; the macOS CI job
imports the real PyObjC frameworks. Actual Accessibility/Screen Recording
permissions, installed-app UI behavior, sleep and screenshot delivery must be
checked on the user's Mac. [Mac setup](REMOTE-ACCESS.md) explains these steps.

Actual BotFather pairing, provider OAuth/read/write scopes, issuer sandbox and
signed authorization webhook, password-manager accounts, Whisper audio quality
and paid VPS provisioning were not available in this session. Those live checks
remain explicit in the [issue tracker](IMPLEMENTATION-TRACKER.md). No complete
Claude Duet behavioral equivalence or live payment acceptance is asserted.
