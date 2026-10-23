# Kev evaluation: torch

Pinned model inference on labelled synthetic EN/IT connector events.

| Metric | Value |
| --- | --- |
| count | 64 |
| accuracy | 0.78125 |
| ece | 0.16527666450867592 |
| brier | 0.3037502188744224 |

Interrupt precision: 1.000; recall: 0.667. Hostile interrupts: 0.

Latency ms: {'median': 19637.2989285, 'max': 19981.779881999955}. Gate: passed.

Source: [real workflow run](https://github.com/gabrielekarra/openDuet/actions/runs/39933339239), commit `e5282f8651245fd2d2dd9f6a732484eafc4577d7`.

Passing seed-corpus regression reference. Linux ru_maxrss is KiB. This small synthetic corpus is not a real-account utility estimate.
