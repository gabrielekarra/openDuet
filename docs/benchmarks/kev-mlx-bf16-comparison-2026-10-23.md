# Kev evaluation: mlx

Pinned model inference on labelled synthetic EN/IT connector events.

| Metric | Value |
| --- | --- |
| count | 64 |
| accuracy | 0.78125 |
| ece | 0.14929867091877982 |
| brier | 0.30375903432079054 |

Interrupt precision: 1.000; recall: 0.667. Hostile interrupts: 0.

Latency ms: {'median': 4507.412583500013, 'max': 23446.591292000023}. Gate: passed.

Source: [real workflow run](https://github.com/gabrielekarra/openDuet/actions/runs/39933339239), commit `e5282f8651245fd2d2dd9f6a732484eafc4577d7`.

Companion MLX report for the BF16 parity comparison. macOS ru_maxrss is bytes and excludes Metal allocations.
