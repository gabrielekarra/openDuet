# ADR-010: Separate local Kev decisions

Updated 23 October 2026 for OpenDuet. The old filename is retained for links;
the native menu-bar application is retired. Its original implementation remains
in the preserved `bobb-mac-final` Git tag.

The workspace and Kev run as separate processes. Kev makes bounded typed
decisions about normalized connector events; a separately chosen local or API
work model writes and executes tasks. No particular generation model is required.
The Mac login service, Linux service and Compose setup share this contract.

Model downloads begin only on an explicit user request in Proactivity. Missing,
unverified or unavailable models leave the workspace in brief-only mode. No
screen sensor or continuous screenshot capture feeds the attention loop.
On-demand Mac application control and screenshots are separate approved tools.

MLX uses the pinned merged 8-bit checkpoint on Apple silicon. Torch uses the
official adapter and trained pointer head on the pinned Qwen backbone. CPU
defaults to INT8 weights with FP32 activations, adapter and pointer head;
BF16/FP32 are explicit alternatives. Revisions, file sizes and SHA-256 values
are in `openduet/kev/manifest.json`. A changed head is rejected before loading,
and Torch uses `weights_only=True`. Upstream source, license and provenance
remain in `openduet/kev/vendor/`.

Shared state prefixes are cached. Inference is serialized outside the web
process. States exceeding 4,096 tokens and branches exceeding 8,192 are refused,
with strict admission rather than silent truncation. The selected typed label's
probability, including reversed-option averaging where requested, is the
confidence contract; it is not confidence relative to a uniform distribution.

Current [real measurements](../benchmarks/README.md) include 14.48 GiB peak
process RSS for CPU INT8, and 4.52 GiB peak Metal allocation for MLX on a runner
exposing 7 GiB physical RAM. These use different machines and boundaries. Metal
allocations overlap with process RSS on unified memory; adding them is invalid.
Neither certifies an entire product budget on a 16 GiB personal Mac. Consumer
GPU budgets remain unmeasured.

The frozen seed corpus has 100% BF16/MLX typed-label agreement. Default
INT8/MLX agreement is 98.44% on seed and 100% on the additional EN/IT corpus;
one quantization flip remains visible. The original failed evaluation and each
precision's passing report are retained. Replacing Kev requires fresh task and
policy evaluation, including abstention and hostile content.
