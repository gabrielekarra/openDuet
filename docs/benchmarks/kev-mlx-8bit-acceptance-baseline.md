# Kev evaluation: mlx

Pinned model inference on labelled synthetic EN/IT connector events.

| Metric | Value |
| --- | --- |
| count | 128 |
| accuracy | 0.8984375 |
| ece | 0.16487807973550722 |
| brier | 0.23042804586376886 |

Interrupt precision: 1.000; recall: 0.500. Hostile interrupts: 0.

Latency ms: {'median': 4748.474770999963, 'max': 18607.421584000007}. Gate: passed.

Source: [real workflow run](https://github.com/gabrielekarra/openDuet/actions/runs/39943044430), commit `9419e8f5b391064db8be78a9753abf7fbbcba8d3`.

Passing separate frozen 24-case acceptance regression reference. macOS ru_maxrss is bytes and excludes Metal allocations. This benchmark does not measure personal-account usefulness.
