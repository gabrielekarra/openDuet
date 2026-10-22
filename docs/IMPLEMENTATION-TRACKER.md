# Issue implementation and acceptance

Scope: the 39 open issues #4–#44, excluding the already closed #17 and #22.
This tracker describes the 0.3.0 implementation. **Delivered** means code and
repeatable checks exist; it does not certify untested third-party accounts or
hardware. The product remains a developer preview. Exact commands and results
are in [VALIDATION.md](VALIDATION.md).

The owner's later instruction overrides the removal of on-demand Mac access
in #21/#25: the legacy native application and continuous sensors are retired,
while the portable runtime can open installed Mac apps, inspect accessible
controls, execute approved interactions and send screenshots to its Telegram
owner. No screen-sharing service is required. The `bobb-mac-final` tag preserves
the native source before deletion.

| Issue | Implementation and evidence | Remaining acceptance boundary |
| --- | --- | --- |
| #4 | All workstreams below implemented; public research and differences in [capability matrix](CLAUDE-DUET-RESEARCH.md) | Full behavioral parity is not asserted; live/model checks below remain |
| #5 | Legacy retirement, preserved tag and [migration](MIGRATION.md) | Delivered, with the owner's Mac override |
| #6 | Local-time brief/report, DST/day claims, chat and UI preferences, separate work-model/Kev usage | Live usefulness depends on connected accounts |
| #7 | UI MCP directory, hot registry, OAuth PKCE/DCR, disconnect revalidation; connector/OAuth fixtures | Actual provider OAuth accounts not available here |
| #8 | Exact previews, immutable edits, deferred independent work, expiry and one-use execution | Fixture and browser checks passed |
| #9 | Per-task retrieval sources, invalid citation detection, text-tool support and artifact sources | Generated numerical claims still require human review |
| #10 | Versioned scheduled dashboards, PNG delivery and separate opaque prototype sandbox | Real Chromium parent/API/network isolation passed |
| #11 | Live XLSX formulas, DOCX/PDF/PPTX, notes, native previews and retained versions | Real LibreOffice recalculation/rendering passed |
| #12 | Separate computer API/container, enforcing public egress, artifact bridge, Compose and VPS cloud-init | Local Docker accepted; paid VPS provisioning not performed |
| #13 | Encrypted vault, rotation/recovery, scoped 1Password/Bitwarden injection, redaction | Fixture credentials only; real vault accounts not available |
| #14 | Read/destructive classification, forbidden actions, sensitive-data checks and hostile-page fixtures | Declared tool actions and tested data patterns; not a semantic guarantee for every GUI |
| #15 | 17-service directory contracts, permissions/setup links, five end-to-end business recipes | Four prefilled official MCP URLs; other entries need reviewed servers. Real-service contracts remain unverified |
| #16 | Agent Skills descriptions/on-demand bodies, reviewed local/Git/static Claude-layout plugins, suggestions | Executable hooks/scripts/binaries are intentionally unsupported |
| #18 | Off-by-default Stripe Issuing adapter, exact spend approval, merchant/amount/expiry/caps, private checkout and cancellation | Mock issuer fixture passed. A real eligible issuer sandbox/account and webhook must still be accepted; private Link/Shop Pay APIs unavailable |
| #19 | Telegram-first console, seven views, mobile/dark layouts, original glasses brand | 28 screenshots; Lighthouse Tasks/Telegram 100. GitHub social-preview file supplied, repository image not set |
| #20 | Removed continuous AX/OCR/screen sensors | On-demand Mac observation retained by owner instruction |
| #21 | Removed native hotkey/overlay/virtual-Mac/demonstration stack and VNC | Portable approved Mac bridge retained by owner instruction |
| #23 | Removed Apple-native Mail/Messages/Reminders/Contacts/Shortcuts and iMessage automation | Delivered |
| #24 | Removed native Qwen text engine and obsolete engine evaluations | Portable work-model adapters and Kev backends retained |
| #25 | Removed BobbApp and bobbd after portable port; preserved final native tag | Actual Mac permissions/app interaction still needs device acceptance |
| #26 | Removed license server, signing tooling and native checks | MIT runtime; third-party licenses retained |
| #27 | Removed free-form Routines UI; built-in brief/report and approved check-ins remain | Delivered |
| #28 | Removed spoken responses/TTS; bounded local voice input remains | Real Whisper model/audio quality not evaluated |
| #29 | Removed obsolete pitch/demo/video/docs; relocated relevant Kev history with explicit historical labels | Delivered |
| #30 | Typed Kev/event/policy/learning engine separate from selected work LLM | Real CPU seed evaluation failed the quality gate; semantic calibration/parity is not qualified |
| #31 | Owner-paired durable Telegram loop, shared tasks, artifacts, approvals, media and optional Mini App | Real BotFather account/network delivery still needs live acceptance |
| #32 | Separate Torch/MLX service, pinned checksums, explicit downloads, health and brief-only fallback | CPU service startup and real BF16 inference checked; quality gate failed, MLX/Torch parity remains pending |
| #33 | Durable normalized events/cursors/dedup/edits; Gmail/M365/calendar/Slack/finance contracts | Reviewed MCP polling tools and real account scopes required |
| #34 | Deterministic ignore/brief/prepare/silent/interrupt policy and stored readouts | Policy branches pass without a loaded model |
| #35 | Feedback floors, sender mute/undo, exact reply labels, held-out specialist gate and forget | Synthetic learning tests pass; personal utility requires user labels |
| #36 | Sourced commitments, working-day quiet follow-ups, calendar/travel conflicts, deduplicated/snoozable prep | Friday promise and call/flight fixtures pass; external moves stay approved |
| #37 | Stored-data explanations, /why, /quiet, decision feedback and task decision links | No explanation LLM call required |
| #38 | EN/IT typed benchmark, JSON/MD metrics, fake PR checks, real weekly/manual workflow and parity comparator | Fixture and failed real CPU reports committed; workflow and metrics verified. Approved passing baseline/MLX parity remain pending |
| #39 | BotFather guide, encrypted validation/pairing/rotation/disconnect, second-account denial | Browser fixture passes; two-minute live onboarding not measured |
| #40 | Durable inbox/offset/outbox, rate/backoff, escaping/splitting, topic routing and uncertain delivery review | Restart/429/owner boundary fixtures pass |
| #41 | Inline approval/edit/defer/expiry/receipt and quick replies; deferred Review buttons in /tasks/brief | Single-execution and deferred-review fixtures pass |
| #42 | Bounded voice/photos/files, local transcript before task, opt-in vision and document delivery/revisions | Disposable transports pass; actual voice/model quality unmeasured |
| #43 | Kev-controlled audible/silent/batched/brief delivery, cap and local-language reports | Policy/delivery fixtures pass |
| #44 | Optional HTTPS Mini App, fresh HMAC owner initData, scoped revocable session, Tasks/Make only | Tampered/stale/other-owner tests pass; real Telegram webview not available |

No issue requiring a real issuer, provider account, Mac device, model parity or
cloud provisioning should be marked accepted solely because its fixture passes.
