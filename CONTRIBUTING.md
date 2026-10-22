# Contributing

OpenDuet's original code uses the MIT license. Preserve licenses and provenance
for third-party materials. Use synthetic or explicitly consented test data;
never commit accounts, keys, model weights, private documents or runtime state.

Read the [architecture](docs/ARCHITECTURE.md), [security boundaries](docs/SECURITY.md)
and [issue acceptance tracker](docs/IMPLEMENTATION-TRACKER.md). The portable
runtime is in `openduet/`; the personal-specialist research package is separate.
Native predecessor history is under `bobb-mac-final`.

```sh
uv sync --locked --extra dev --extra browser
uv run --no-sync pytest tests/runtime -q
uv run --no-sync ruff check --select E4,E7,E9,F,I,UP openduet tests/runtime scripts
uv run --no-sync openduet-kev-eval
```

Run the disposable browser fixture and `tests/runtime/browser_smoke.py` for UI
changes. It exercises bot pairing, tasks, Make and approvals and captures 28
light/dark, desktop/mobile screenshots. `scripts/check_office.py` requires real
LibreOffice and Poppler. Model changes need real benchmark and backend parity
reports, not the synthetic fixture score.

Keep approvals exact and one-use, silence deliberate and explainable, and
credentials outside prompts/logs. Verify revoked access, hostile retrieved text,
restarts, expired reviews and uncertain outcomes when changing execution paths.
UI changes should retain the existing glasses mark, keyboard focus, 44px targets,
responsive layouts, reduced-motion support and clear English/Italian copy.
