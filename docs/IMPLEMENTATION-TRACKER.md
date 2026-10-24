# Issue implementation and acceptance

Scope: the 39 originally open issues #4–#44, excluding the previously closed #17 and #22.
Review on 24 October 2026: **27 completed and closed; 12 remain open**.
This tracker describes the 0.4.0rc3 release candidate. **Delivered** means code and
repeatable checks exist; it does not certify untested third-party accounts or
hardware. The product is installable as a private Mac login service or self-hosted server. Exact commands and results
are in [VALIDATION.md](VALIDATION.md).

The owner's later instruction overrides the removal of on-demand Mac access
in #21/#25: the legacy native application and continuous sensors are retired,
while the portable runtime can open installed Mac apps, inspect accessible
controls, execute approved interactions and send screenshots to its Telegram
owner. No screen-sharing service is required. The `bobb-mac-final` tag preserves
the native source before deletion.

| Issue | State | Implementation and evidence | Remaining acceptance boundary |
| --- | --- | --- | --- |
| #4 | Open | All workstreams below implemented; public research and differences in [capability matrix](CLAUDE-DUET-RESEARCH.md) | Full behavioral parity is not asserted; live/model checks below remain |
| #5 | Open | Legacy retirement, preserved tag and [migration](MIGRATION.md) | Delivered, with the owner's Mac override |
| #6 | Closed | Local-time brief/report, DST/day claims, chat and UI preferences, separate work-model/Kev usage | Live usefulness depends on connected accounts |
| #7 | Closed | UI OAuth with confidential clients, PKCE/DCR, rotating refresh, atomic discovery and account-bound actions; real HTTP/browser acceptance | Actual provider OAuth accounts not available here |
| #8 | Closed | Exact previews, immutable edits, deferred independent work, expiry and one-use execution | Fixture and browser checks passed |
| #9 | Closed | Task/file/record sources, exact locators, validated numeric references, Office/PDF links, offline excerpts and source-preserving revisions | Actual file/browser/brief fixture criteria pass; citation identity does not certify a claim or calculation |
| #10 | Closed | Versioned scheduled dashboards, PNG delivery and separate opaque prototype sandbox | Real Chromium parent/API/network isolation passed |
| #11 | Closed | Live XLSX formulas, DOCX/PDF/PPTX, notes, native previews and retained versions | Real LibreOffice recalculation/rendering passed |
| #12 | Open | Separate computer API/container, enforcing public egress, artifact bridge, Compose and VPS cloud-init | Local Docker accepted; paid VPS provisioning not performed |
| #13 | Closed | Encrypted vault, rotation/recovery, scoped 1Password/Bitwarden injection, redaction | Fixture credentials only; real vault accounts not available |
| #14 | Closed | Read/destructive classification, forbidden actions, sensitive-data checks and hostile-page fixtures | Declared tool actions and tested data patterns; not a semantic guarantee for every GUI |
| #15 | Open | 17-service directory contracts, permissions/setup links, five end-to-end business recipes | Eight prefilled official MCP URLs; provider setup documented. Read-only live contract runner delivered; per-service setup/recorded contracts and real accounts still require acceptance |
| #16 | Closed | Agent Skills descriptions/on-demand bodies, reviewed local/Git/static Claude-layout plugins, suggestions | Executable hooks/scripts/binaries are intentionally unsupported |
| #18 | Open | Off-by-default Stripe Issuing adapter, exact spend approval, merchant/amount/expiry/caps, private checkout and cancellation | Mock issuer fixture passed. A real eligible issuer sandbox/account and webhook must still be accepted; private Link/Shop Pay APIs unavailable |
| #19 | Closed | Telegram-first console, seven views, mobile/dark layouts, original glasses brand | 28 screenshots; Lighthouse Tasks/Telegram 100. GitHub social-preview file supplied, repository image not set |
| #20 | Closed | Removed continuous AX/OCR/screen sensors | On-demand Mac observation retained by owner instruction |
| #21 | Closed | Removed native hotkey/overlay/virtual-Mac/demonstration stack and VNC | Portable approved Mac bridge retained by owner instruction |
| #23 | Closed | Removed Apple-native Mail/Messages/Reminders/Contacts/Shortcuts and iMessage automation | Delivered |
| #24 | Closed | Removed native Qwen text engine and obsolete engine evaluations | Portable work-model adapters and Kev backends retained |
| #25 | Closed | Removed BobbApp and bobbd after portable port; preserved final native tag | Actual Mac GUI launchd restart/session acceptance passes; owner Mac permissions/app interaction still needs device acceptance |
| #26 | Open | Removed license server, signing tooling and native checks | MIT runtime; third-party licenses retained |
| #27 | Closed | Removed free-form Routines UI; built-in brief/report and approved check-ins remain | Delivered |
| #28 | Closed | Removed spoken responses/TTS; bounded local voice input remains | Real Whisper model/audio quality not evaluated |
| #29 | Open | Removed obsolete pitch/demo/video/docs; relocated relevant Kev history with explicit historical labels | Delivered |
| #30 | Open | Typed Kev/event/policy/learning engine separate from selected work LLM | Real Torch INT8 and MLX pass seed/additional quality gates and real parity; personal-account utility still needs labels |
| #31 | Open | Owner-paired durable Telegram loop, shared tasks, artifacts, approvals, media and optional Mini App | Real BotFather account/network delivery still needs live acceptance |
| #32 | Open | Separate Torch/MLX service, pinned checksums, explicit downloads, health and brief-only fallback | BF16/MLX seed labels match; INT8 has one seed flip. Corrupt-head/overflow refused; CPU 14.48 GiB RSS, MLX 4.52 GiB Metal peak measured; consumer GPU unmeasured |
| #33 | Closed | Direct TLS IMAP/SMTP accounts, durable normalized events/cursors/dedup/edits; Gmail/M365/calendar/Slack/finance MCP contracts | Real HTTP MCP fixtures pass pagination/dedup/edits/disconnect; actual account scopes still operator-supplied |
| #34 | Closed | Deterministic ignore/brief/prepare/silent/interrupt policy and stored readouts | Policy branches pass without a loaded model |
| #35 | Closed | Feedback floors, sender mute/undo, exact reply labels, held-out specialist gate and forget | Synthetic learning tests pass; personal utility requires user labels |
| #36 | Closed | Sourced commitments, working-day quiet follow-ups, calendar/travel conflicts, deduplicated/snoozable prep | Friday promise and call/flight fixtures pass; external moves stay approved |
| #37 | Closed | Stored-data explanations, /why, /quiet, decision feedback and task decision links | No explanation LLM call required |
| #38 | Closed | EN/IT typed benchmark, JSON/MD metrics, fake PR checks, real weekly/manual workflow and parity comparator | Passing real seed/additional baselines and actual MLX/Torch parity committed; historical failures retained; small samples do not establish real-account calibration |
| #39 | Open | Guided setup/readiness, BotFather guide, encrypted validation/pairing/rotation/disconnect, second-account denial | Browser fixture passes; two-minute live onboarding not measured |
| #40 | Closed | Durable inbox/offset/outbox, rate/backoff, escaping/splitting, topic routing and uncertain delivery review | Actual SIGKILL acceptance resumes same task and delivers one document to original chat/topic; 429/owner fixtures pass |
| #41 | Closed | Inline approval/edit/defer/expiry/receipt and quick replies; deferred Review buttons in /tasks/brief | Single-execution and deferred-review fixtures pass |
| #42 | Closed | Bounded voice/photos/files, local transcript before task, opt-in vision and document delivery/revisions | Disposable transports pass; actual voice/model quality unmeasured |
| #43 | Closed | Kev-controlled audible/silent/batched/brief delivery, cap and local-language reports | Policy/delivery fixtures pass |
| #44 | Open | Optional HTTPS Mini App, fresh HMAC owner initData, scoped revocable session, Tasks/Make only | Tampered/stale/other-owner tests pass; real Telegram webview not available |

No issue requiring a real issuer, provider account, Mac device, model parity or
cloud provisioning should be marked accepted solely because its fixture passes.
