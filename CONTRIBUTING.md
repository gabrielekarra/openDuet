# Contributing to OpenDuet

OpenDuet welcomes fixes, evaluations, accessibility improvements, translations
and real workflow reports under the [MIT License](LICENSE). Contributions use
the same license. Submit only work you are authorized to license; identify
third-party material and preserve its notices.

The portable service lives in `openduet/`. Run `uv sync --extra dev` and
`uv run pytest tests/runtime`. The Mac app and isolated local daemon retain
their existing directories and internal identifiers for compatibility.

Read [README](README.md), [the capability guide](docs/BOBB.md) and
[the product review](docs/PRODUCT-REVIEW-2026-10-01.md). Use a branch and pull
request with the problem, resulting behavior and relevant validation. Keep app
exclusions and action boundaries ahead of side effects. Keep daemon network
isolation tests. Add meaningful regression tests for behavior changes.

For proactive suggestions, test both useful interventions and deliberate
silence. Include completed work, ambiguous requests, adversarial screen text,
pausing observation, revoked access, deleted sources and restart recovery.
Model confidence is not evidence of correctness; record actual outputs and
limits. Use synthetic or explicitly consented examples, never client data.

Do not commit accounts, API keys, SSH identities, model weights, macOS images,
personal data or runtime databases. Run relevant checks from
[CI](.github/workflows/ci.yml). New UI uses shared Liquid Glass components and
respects reduced transparency. Report app/version, expected outcome and the
observed failure when reporting an automation problem.
