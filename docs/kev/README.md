# Portable Kev

Production code is in `openduet/kev/`; `vendor/kev` is the unmodified upstream
inference source, with Apache license and provenance. A trained pointer head
answers typed options; no generated-text parsing or work-LLM judge is involved.
MLX uses the pinned merged 8-bit Apple-silicon checkpoint. Torch uses the official
adapter, trained head and pinned Qwen base. Every downloaded file has a pinned
revision, size and SHA-256 in `manifest.json`.

```sh
uv sync --locked --extra kev
uv run --no-sync openduet-kev   # Separate CPU process, port 8768
```

Set `kev_url` in the workspace and explicitly download the model in Proactivity.
No model downloads automatically at startup. Mac setup creates this separate
service when the optional backend is installed. On Apple silicon install
`--extra mlx` and use `OPENDUET_KEV_BACKEND=mlx`.
`OPENDUET_KEV_MODELS` selects model storage; `OPENDUET_KEV_DEVICE` selects cpu/cuda.

The default CPU dtype is **INT8 weights with FP32 activations, LoRA and pointer
head**, loaded through Quanto. `OPENDUET_KEV_DTYPE=float32` or `bfloat16` explicitly
select other Torch paths; CUDA defaults to float32. Backend/precision changes
need evaluation. The Torch download is 9.48 GB, MLX 4.50 GB. CPU INT8 measured a
**14.48 GiB peak RSS**, including loading, on the real runner: allow at least
16 GiB available, plus memory for the work model, workspace and OS. MLX total
Metal memory still needs target-device measurement.

The service batches questions, caches shared prefixes and serializes inference
outside the workspace process. Health reports backend, actual precision/device,
revision, download progress and latency. Missing/invalid models leave the
workspace responsive in brief-only mode. Production never silently substitutes
the synthetic fixture backend.

## Real acceptance and regression

The [published reports](../benchmarks/README.md) record passing Torch INT8 and
MLX runs on the seed corpus and a separate frozen 24-case EN/IT corpus. Additional
answer accuracy was **89.8%** for both; interruption precision **100%**, recall
**50% (4/8)**, hostile interruptions **0**. Actual additional-corpus parity was
100% typed-label agreement, maximum probability delta 0.03192. These small,
labelled synthetic samples are not evidence of real-account utility.

Median per-event inference was **41.3 s CPU / 4.75 s MLX** on different GitHub
runners. CPU seed maximum was 51.3 s; MLX seed first-case maximum 63.9 s.
Consider event backlog as well as single-event latency when selecting hardware.
macOS `ru_maxrss` excludes Metal allocations and cannot certify total MLX RAM.

```sh
# Synthetic adapter/policy check, no model download:
uv run --no-sync openduet-kev-eval
# Actual pinned CPU inference:
uv run --no-sync openduet-kev-eval --backend torch --download --output /tmp/kev-torch
uv run --no-sync openduet-kev-eval --backend torch --cases openduet/kev/acceptance-cases.json --output /tmp/kev-torch-acceptance
# On Apple silicon with verified weights:
uv run --no-sync openduet-kev-eval --backend mlx --output /tmp/kev-mlx
uv run --no-sync openduet-kev-eval --backend torch --compare /tmp/kev-mlx.json
```

Reports include corpus/question fingerprints, readouts, accuracy, ECE/Brier,
interrupt precision/recall, coverage by confidence floor and latency. Admission
requires accuracy ≥.75, interrupt precision ≥.90, recall ≥.50 and no hostile
interruptions. The initial failed BF16 report is preserved; the
[report history](../benchmarks/README.md) explains the changed questions and
denominators without treating unlike metrics as a direct improvement.

Use `--baseline` with a passing real report of identical backend, precision,
corpus and questions. Accuracy/precision may regress at most .02 and ECE at
most .03; fixtures cannot qualify a model. Backend parity requires identical
nonempty cases and options, ≥.95 label agreement and maximum probability delta
≤.15. The weekly/manual `Real Kev benchmark` workflow checks both corpora against
committed passing `kev-<backend>-<precision>[-acceptance]-baseline.json` references;
MLX's filename precision is `8bit`. Failures remain failures.

Historical native design notes and `historical-benchmarks/` describe predecessor
experiments, not current setup or performance. The separate `specialist/`
byte-transformer research package is retained. The runtime personal specialist
uses the lower-data NumPy model and a held-out personal-label gate.
