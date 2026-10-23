# Kev evaluation: torch

Pinned model inference on labelled synthetic EN/IT connector events.

| Metric | Value |
| --- | --- |
| count | 128 |
| accuracy | 0.8984375 |
| ece | 0.16547397883884704 |
| brier | 0.2302928168554801 |

Interrupt precision: 1.000; recall: 0.500. Hostile interrupts: 0.

Latency ms: {'median': 41324.67526600004, 'max': 48499.96896500011}. Gate: passed.

Source: [real workflow run](https://github.com/gabrielekarra/openDuet/actions/runs/39943044430), commit `9419e8f5b391064db8be78a9753abf7fbbcba8d3`.

Passing separate frozen 24-case acceptance regression reference. Quanto INT8 weights, FP32 activations, unmerged FP32 LoRA and trained pointer head. Linux ru_maxrss is KiB; peak includes loading/quantization. This is not personal-account utility evidence.
