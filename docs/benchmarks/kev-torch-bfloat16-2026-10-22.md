# Kev evaluation: torch

Pinned model inference on labelled synthetic EN/IT connector events.

| Metric | Value |
| --- | --- |
| count | 52 |
| accuracy | 0.6538461538461539 |
| ece | 0.16393127557966808 |
| brier | 0.4701082771051781 |

Interrupt precision: 1.000; recall: 0.000. Hostile interrupts: 0.

Latency ms: {'median': 3282.447538499994, 'max': 3515.6790860000056}. Gate: failed.


## Interpretation and provenance

[Real CPU run](https://github.com/gabrielekarra/openDuet/actions/runs/39860552831),
commit `f403f4b770d98cd166f945dcfcdeb898f7f16882`, pinned official Torch
adapter/base, bfloat16, GitHub-hosted Ubuntu runner. Full model manifest/checksums
and source-run metadata are included in the JSON report.

This initial seed corpus has 12 synthetic cases and 52 typed answers. It is not
a representative estimate of real-account performance. Accuracy is **65.4%**,
below the fixed **75%** admission threshold. The model produced **zero
interruptions**, including **0/3** expected urgent interruptions. Precision 1.0
is the empty-prediction convention and is not evidence of successful urgency
detection. No hostile item interrupted.

Median per-case inference was 3282 ms; peak process RSS was 8,324,228 KiB
(about 7.94 GiB), excluding other services. These are measured for this run,
precision and runner only. Default float32 and MLX need separate measurements.

**Gate failed. This report is diagnostic evidence, not an approved regression
baseline.** The questions, corpus, calibration and conservative confidence policy
need further held-out evaluation before qualifying the attention model. No
threshold was lowered to make this run pass.
