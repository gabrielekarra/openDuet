# Portable Kev

Production code is in `openduet/kev/`; `vendor/kev` is the unmodified upstream
inference source with its Apache license and provenance. It uses a trained
pointer head over typed options, not generation token parsing or an LLM judge.
MLX serves the merged 8-bit Apple-silicon checkpoint; Torch serves the official
adapter/head and pinned Qwen base on CPU/CUDA. Every file has a pinned revision,
size and SHA-256 in `manifest.json`. Weights are never auto-downloaded at startup.

```sh
uv sync --locked --extra kev   # Torch; Linux lock uses CPU wheels
uv run openduet-kev            # Separate process, port 8768
```

Set `kev_url` in the workspace. Explicitly start the model download in
Proactivity. For MLX install `--extra mlx` on Apple silicon and set
`OPENDUET_KEV_BACKEND=mlx`. `OPENDUET_KEV_MODELS` selects model storage;
`OPENDUET_KEV_DEVICE` selects cpu/cuda. Default Torch precision is float32;
`OPENDUET_KEV_DTYPE=bfloat16` is an explicit serving option. Precision/backend
changes require re-evaluation. The pinned Torch files declare 9.48 GB and the MLX files 4.50 GB of disk
content. RAM/throughput budgets remain unmeasured and must be checked on the
target machine; serialized weight size is not an inference RAM measurement.

The service batches typed questions, caches shared prefixes and serializes
inference outside the workspace process. Health reports model/revision, backend,
device, precision, download progress and latency. Missing/invalid models leave
the workspace responsive in brief-only mode. The fixture backend is explicit;
production never silently chooses synthetic decisions.

## Evaluation

```sh
uv run openduet-kev-eval
uv run openduet-kev-eval --backend torch --download --output docs/benchmarks/kev-torch
# On a Mac with verified MLX weights:
uv run openduet-kev-eval --backend mlx --output docs/benchmarks/kev-mlx
uv run openduet-kev-eval --backend torch --compare docs/benchmarks/kev-mlx.json
```

The default command produces JSON/Markdown from recorded synthetic logits. It
checks typed readout and policy contracts, **not semantic model accuracy**.
The labelled corpus includes EN/IT mail, chat, calendar and finance cases across
small businesses, brokers, consultants and restaurants, including hostile text.
Real runs report question accuracy, ECE, Brier, interruption precision/recall,
coverage/accuracy by floor and backend latency. They must have no hostile
interruptions, at least .75 answer accuracy and .90 interrupt precision.

Use `--baseline` with an approved **real** report: accuracy/precision may regress
at most .02 and ECE at most .03. A fixture cannot serve as a model baseline.
Model swaps require real MLX/Torch reports with at least .95 label agreement and
maximum probability difference .15. Record exact precision and hardware when
reviewing those tolerances. The weekly/manual `Real Kev benchmark` workflow
publishes its JSON/Markdown artifacts; failed gates remain failures.

Real MLX/Torch parity, RAM and latency are not established by fixture results.
The current managed development environment has an 8 GB memory limit, below
the pinned base's unquantized footprint, so its local validation uses adapter
fixtures. Run the real job on a sufficiently provisioned runner/Mac before
accepting a model swap.

Historical design notes and `historical-benchmarks/` are preserved from the
native predecessor. Names and native paths in them describe those experiments;
they are not instructions for the current product or current performance claims.
The separate `specialist/` byte-transformer research package is retained; the
runtime personal specialist uses the lower-data NumPy model with a held-out gate.
