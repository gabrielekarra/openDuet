# Kev evaluation: torch

Pinned model inference on labelled synthetic EN/IT connector events.

| Metric | Value |
| --- | --- |
| count | 64 |
| accuracy | 0.796875 |
| ece | 0.17929266293256513 |
| brier | 0.3028862238127819 |

Interrupt precision: 1.000; recall: 1.000. Hostile interrupts: 0.

Latency ms: {'median': 41113.72320750004, 'max': 51312.04431799998}. Gate: passed.

Source: [real workflow run](https://github.com/gabrielekarra/openDuet/actions/runs/39943044430), commit `9419e8f5b391064db8be78a9753abf7fbbcba8d3`.

Passing 12-case seed regression reference. Quanto INT8 weights, FP32 activations, unmerged FP32 LoRA and trained pointer head. Linux ru_maxrss is KiB; peak includes loading/quantization. This is not personal-account utility evidence.
