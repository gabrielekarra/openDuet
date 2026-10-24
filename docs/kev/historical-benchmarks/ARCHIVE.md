# Native benchmark archive

The original 1 October experiment measured the retired native application.
Its inputs, report and source paths are preserved unchanged in the immutable
0.4.0rc3 source commit, `8085f1f2335d92e5b1af01eb2f1d3e45fed1c895`:

- [Original fixed input corpus](https://github.com/gabrielekarra/openDuet/blob/8085f1f2335d92e5b1af01eb2f1d3e45fed1c895/docs/kev/historical-benchmarks/decision_benchmark_cases.json)
- [Original report](https://github.com/gabrielekarra/openDuet/blob/8085f1f2335d92e5b1af01eb2f1d3e45fed1c895/docs/kev/historical-benchmarks/decision-models-2026-10-01.md)
- [Original measurements](https://github.com/gabrielekarra/openDuet/blob/8085f1f2335d92e5b1af01eb2f1d3e45fed1c895/docs/kev/historical-benchmarks/decision-models-2026-10-01.json)
- [Last complete native runtime](https://github.com/gabrielekarra/openDuet/tree/15374dee3a26a80e02b494411bf43fe87c8931d3)

The corpus SHA-256 is:

```text
f7ad8d9b892df36e1360cb75ec711f6be319ec9b491e1ca90d185febce9e56b1
```

Download the raw file from that exact commit to verify the original bytes:

```sh
curl -fL 'https://raw.githubusercontent.com/gabrielekarra/openDuet/8085f1f2335d92e5b1af01eb2f1d3e45fed1c895/docs/kev/historical-benchmarks/decision_benchmark_cases.json' -o /tmp/native-decision-cases.json
shasum -a 256 /tmp/native-decision-cases.json
```

The corpus has been removed from the current tree rather than relabelling its
original product names, application context or expected answers. This cleanup
changes no frozen portable model-quality or regression references. Current
[portable benchmarks](../../benchmarks/README.md) use different questions and
workloads; the native figures are not current performance claims.
