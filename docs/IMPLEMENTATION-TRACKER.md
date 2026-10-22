# Issue implementation and acceptance

Scope: all open issues #4–#44, excluding the already closed #17 and #22.
The owner's subsequent instruction takes precedence over #21/#25: retire the
legacy native product while keeping on-demand Mac application control and
screenshots sent to the paired Telegram owner. Screen sharing is not required.

Implementation is tracked against the acceptance criteria, including negative
tests. Fixture coverage does not establish live provider, payment issuer,
macOS permission, model parity, performance or accessibility-audit results.
Those results are recorded only after running the corresponding check.

| Issues | Workstream | Status |
| --- | --- | --- |
| #13 #14 | Encrypted vault, credential injection, action and disclosure policy | In progress |
| #31 #39 #40 #41 #42 #43 #44 | Owner-paired Telegram, media, approvals, delivery and Mini App | In progress |
| #30 #32 #33 #34 #35 #36 #37 #38 | Portable Kev, event ingestion, policy, learning and evaluation | In progress |
| #6 #27 | Local-time briefs/reports and confirmed schedules | In progress |
| #7 #15 #16 | Connector directory, OAuth and declarative plugins | In progress |
| #8 #9 | Exact approvals, defer/edit and validated sources | In progress |
| #10 #11 | Versioned dashboards, prototypes and Office deliverables | Pending |
| #12 | Isolated computer and always-on deployment | Pending |
| #18 | Scoped purchases, issuer adapters and spending limits | Pending |
| #19 #28 | Console, branding, responsive/dark UI and input-only voice | Pending |
| #5 #20 #21 #23 #24 #25 #26 #29 | Legacy removal after port, with Mac bridge retained | Pending |
| #4 | Product acceptance across workstreams | Pending |

The `bobb-mac-final` tag preserves the last native application before removal.
