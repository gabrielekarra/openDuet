# Real-model acceptance — 23 October 2026

These reports contain actual pinned-model inference. The labelled events are
synthetic examples, not private accounts or a representative production sample.
`kev-fixture.*` uses recorded logits and only checks adapters and policy.

| Backend and corpus | Typed accuracy | Interrupt precision / recall | Median per event | Result |
| --- | --- | --- | --- | --- |
| Torch INT8, 12 seed cases / 64 answers | 79.7% | 100% / 100% (3/3 urgent) | 41.1 s | [Passed](kev-torch-int8-baseline.md) |
| MLX 8-bit, same seed | 78.1% | 100% / 66.7% (2/3 urgent) | 4.60 s | [Passed](kev-mlx-8bit-baseline.md) |
| Torch INT8, separate 24 EN/IT cases / 128 answers | 89.8% | 100% / 50% (4/8 urgent) | 41.3 s | [Passed](kev-torch-int8-acceptance-baseline.md) |
| MLX 8-bit, same additional cases | 89.8% | 100% / 50% (4/8 urgent) | 4.75 s | [Passed](kev-mlx-8bit-acceptance-baseline.md) |

All four reports have zero hostile interruptions. The fixed quality gates are
answer accuracy ≥75%, interruption precision ≥90%, recall ≥50% and no hostile
interruptions. The recall result means four urgent additional examples **did not
interrupt**: this is a conservative assistant, not an emergency notification system.
The ECE of about 0.165 on the additional corpus also leaves calibration work.
These small samples do not establish real-world false-positive rates.

[Actual INT8/MLX parity](kev-int8-mlx-parity-2026-10-23.json) passed on both
corpora: 98.44%/100% typed-label agreement; maximum probability difference
0.02229/0.03192. Admission requires ≥95% agreement and ≤0.15 probability delta.
Matching typed labels do not imply identical policy actions at a threshold.
The [source workflow](https://github.com/gabrielekarra/openDuet/actions/runs/39943044430)
ran both backends independently, including their real downloads and inference.
The source commit, model revisions/checksums, corpus/question fingerprints,
per-case readouts, latency and memory measurements are retained in each JSON.

## Hardware and precision

The GitHub Ubuntu CPU runner's INT8 process peaked at **14.48 GiB RSS** on the
additional corpus, including load/quantization. Median inference was 41.3 s,
maximum 48.5 s; the seed maximum was 51.3 s. Allow at least 16 GiB available for
this backend and additional memory for the work model, workspace and OS.
INT8 describes weights; activations, LoRA and the trained pointer head remain
FP32. A smaller serialized model does not guarantee a smaller loading peak.

MLX ran on a GitHub macOS Apple-silicon runner. Additional-corpus median was
4.75 s and maximum 18.61 s. Seed maximum was 63.90 s, including the first case.
macOS `ru_maxrss` is in bytes and excludes Metal allocations; it is **not a
measurement of total MLX memory**. Actual Mac memory and sustained event backlog
must be checked on the target device. CPU and MLX timing are not same-hardware
speed comparisons.

A [later real MLX hardware run](https://github.com/gabrielekarra/openDuet/actions/runs/39959394450)
passed both frozen quality/regression corpora unchanged. The runner exposed
7,516,192,768 bytes (**7 GiB**) physical RAM, arm64 and three CPUs. Its Metal
allocator peaked at **4,858,071,604 bytes (4.52 GiB)**; active allocations after
the additional corpus were 4,529,452,554 bytes and allocator cache zero. The
additional-corpus median was **4.53 s**, maximum **6.75 s**. Reports preserve
[seed measurements](kev-mlx-metal-2026-10-23.json) and
[additional measurements](kev-mlx-acceptance-metal-2026-10-23.json), versions and
source/artifact provenance. Do not add Metal bytes to process RSS as a unified
memory total. A 16 GiB personal Mac and a consumer GPU remain unmeasured.

## What changed after the failed first run

The [original 22 October BF16 report](kev-torch-bfloat16-2026-10-22.md) failed:
34/52 answers correct (65.4%) and 0/3 urgent interruptions. It remains diagnostic
evidence and is never used as a passing baseline.

The questions now have anchored rating rubrics, debiased choices and a direct
binary `time_critical` predicate. Policy no longer mistakes the probability of
one exact urgency rating for the probability that attention is needed now.
No admission threshold was lowered; the recall floor was added.

On the **same original 52 labels**, improved BF16 achieved **38/52 (73.1%)**.
The new 12 binary answers bring its v2 total to **50/64 (78.1%)**. These are
different denominators; 65.4% →78.1% is not an apples-to-apples accuracy gain.
The [BF16 report](kev-torch-bfloat16-baseline.md) and
[paired MLX report](kev-mlx-bf16-comparison-2026-10-23.md) passed the v2 seed gate;
[parity](kev-bfloat16-mlx-parity-2026-10-23.json) was 100% with maximum delta
0.01935. BF16 median was 19.64 s and peak RSS 8.34 GiB on that runner.

The separate 24-case EN/IT corpus was committed before its first real evaluation
and was not relabelled in response to results. It is now a regression corpus;
future model changes still need fresh acceptance data and real-account labels.
A later BF16 job stalled during inference for over 40 minutes and was cancelled.
An earlier in-memory INT8 attempt lost its runner during quantization. Neither
is counted as a passing run. The passing CPU path uses streamed Quanto loading.

## Other actual acceptance

- [Local work model](local-model-2026-10-23.json): Ollama 0.40.9, Qwen3.5 4.2B
  Q4_K_M, exact model digest and 16k/2048-token profile recorded. Native and text
  protocols both created a real Markdown file; one approved memory was written
  exactly once. This is a narrow tool/delivery check, not arbitrary-task success.
- [Mac login service](mac-service-2026-10-23.json): actual GUI launchd install,
  automatic process restart, persistent authenticated session and one-use login.
  This does not grant permissions or control the owner's personal Mac.

- [Actual Ubuntu VM](cloud-vm-acceptance-2026-10-24.json): owner access and
  separate public browser; Docker restart and changed-boot-ID reboot recovery,
  persistent data marker and owner auth after reboot. Reused images with exact
  deploy/health backport, managed trust/SSH overlays; no paid provider or model
  inference in the 4 GiB guest. Prior failures and inconclusive probe retained.

Passing `*-baseline.json` files are frozen regression references for their exact
backend, dtype, corpus and question fingerprints. The weekly/manual workflow
uses both seed and additional references; a mismatch or regression fails.
