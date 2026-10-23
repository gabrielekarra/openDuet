# Kev evaluation: mlx

Pinned model inference on labelled synthetic EN/IT connector events.

| Metric | Value |
| --- | --- |
| count | 64 |
| accuracy | 0.78125 |
| ece | 0.14929867091877982 |
| brier | 0.30375903432079054 |

Interrupt precision: 1.000; recall: 0.667. Hostile interrupts: 0.

Latency ms: {'median': 4422.586999999992, 'max': 9944.727415999978}. Gate: passed.

Source: [real MLX hardware run](https://github.com/gabrielekarra/openDuet/actions/runs/39959394450), source `f20075791f5c5df9ac6e6208c83827709fcddab9`, artifact `12504341539`.

Metal allocator and exposed physical RAM are recorded in the companion JSON. This is a 7 GiB GitHub runner, not a measured 16 GiB personal Mac. Metal allocations and process RSS overlap in unified memory; do not add them to claim total RAM.
