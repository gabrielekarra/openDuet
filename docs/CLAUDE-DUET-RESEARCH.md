# Claude Duet research and OpenDuet capability matrix

Researched **22 October 2026**, against the public research preview announced on
21 October. This is a public-documentation comparison, not access to Anthropic's
implementation, a private beta account, its model or its production infrastructure.
OpenDuet is an independent implementation, using its own UI and code.

## Primary sources

1. [Introducing Claude Duet](https://claude.com/resources/articles/claude-duet)
   — launch, proactive work, background computer, safeguards and availability.
2. [Claude Duet product page](https://claude.com/product/claude-duet)
   — main product promises, apps, connector ecosystem and preview limits.
3. [Get started with Claude Duet](https://support.claude.com/en/articles/17631495-get-started-with-claude-duet)
   — channels, Tasks, Make, memory, supported accounts and specific limitations.
4. [Link by Stripe](https://support.claude.com/en/articles/17666484-how-to-use-link-by-stripe-with-claude-duet)
   — separate wallet connection, external spend approval and scoped payment cards.
5. [Shop Pay](https://support.claude.com/en/articles/17666489-how-to-use-shop-pay-with-claude-duet)
   — wallet approval and purchase limitations.
6. [Ollama compatibility](https://docs.ollama.com/api/openai-compatibility),
   [LM Studio compatibility](https://lmstudio.ai/docs/developer/openai-compat),
   [MCP transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
   — implementation protocols for independent model and tool access.

## Findings

Claude Duet is a proactive agent for professionals and small businesses. Its
launch combines attention management with delegated work: periodic account
checks, a daily brief and work continuing on a separate cloud computer. Its
public product page advertises a large connector/plugin ecosystem. It is a
research preview, with Pro/Max US waitlist access rather than a generally
available open source product. [1, 2]

The documented interface includes a main conversation, channels sharing memory,
a task list, generated files and approvals. The help page identifies work with
inbox/calendar and business accounts, and separates ordinary Stripe account
access from purchasing wallets. It also documents limits: model selection,
browser observation/takeover, some connector capabilities and certain financial
actions are unavailable. [3]

The payment integrations depend on service-specific authorization. Link and
Shop Pay provide purchase-scoped credentials after approval. A generic Stripe
MCP connector does not supply those wallet capabilities. [4, 5]

## Current capability matrix

This matrix describes executable code paths. Live account, hardware and model
acceptance are recorded separately in [the tracker](IMPLEMENTATION-TRACKER.md).

| Public workflow | OpenDuet implementation | Boundary |
| --- | --- | --- |
| Main conversation and channels | Telegram plus shared web Chat, memory/search and tasks | One paired owner; native mobile apps are replaced by Telegram |
| Tasks, approvals and prepared work | Exact payload previews, edit/defer/expiry, progress and receipts | Owner completes tasks; uncertain effects require verification |
| Morning brief and evening report | Local timezone/DST scheduler and selected cited work | Requires connected sources; no duplicate new urgent items |
| Proactive attention | Separate Kev Bool/Score/Choice readouts, deterministic host policy, reversible personal learning | Missing Kev means brief-only; real backend parity passes, personal usefulness needs account labels |
| Follow-ups and preparation | Sent-message commitments, waiting-thread drafts, calendar/travel facts and prep tasks | External sends/moves remain approval-gated |
| Connections | Direct TLS mail plus curated 17-service directory, dynamic MCP registry, OAuth PKCE/DCR and encrypted refresh tokens | Account/provider scopes and server capabilities apply; listings are not all official endpoints |
| Plugins and skills | On-demand Agent Skills, static Claude-layout bundles, approved pinned Git/local sources | Executable hooks rejected; accounts/schedules are not auto-authorized |
| Make and financial work | Versioned DOCX/PDF/XLSX/PPTX, live formulas, native Office checks and notes/previews | Results require review; no accounting/legal certification |
| Dashboards and prototypes | Declarative local-time refreshed dashboards with PNG delivery; separate opaque sandbox origin for webapps | Static prototypes cannot access workspace APIs/credentials or the network |
| Background computer | Separate Chromium container and enforcing egress proxy | Public reads; consequential interactions reviewed; no live takeover required |
| Secret management | Encrypted vault, private password-manager injection, key rotation and use audit | Operator owns deployment and scoped accounts |
| Scoped purchases | Optional eligible Stripe Issuing adapter, caps, exact merchant/amount authorization and private checkout | This is independent issuing integration, not Anthropic's private Link/Shop Pay partner API |
| User Mac access | On-demand installed-app opening, fresh accessible controls, approved actions and Telegram screenshots | Mac must run OpenDuet, be awake/signed in and have OS permissions |
| Voice and photos | Local Whisper input and opt-in images to compatible vision models | No spoken output; model capability varies |
| Model choice | OpenAI-compatible, native Ollama and Anthropic protocols, plus text tool protocol | Supports local and hosted models; cannot make every model equally capable |
| Always-on hosting | Compose with health/restart policies and an Ubuntu VPS cloud-init recipe | Requires the user's server, model and account configuration |

## Validation

Tests use disposable model, Telegram, OAuth and issuer transports for repeatable
boundary checks. Real Chromium verifies the console and isolated browser's
request restrictions; real LibreOffice verifies recalculated financial totals
and rendered slides. The console is tested in light/dark at 375 and 1280 pixels.
Lighthouse accessibility audits and exact validation commands are linked in the
acceptance tracker.

Synthetic Kev fixtures prove adapter/policy contracts, not semantic accuracy.
Actual Torch INT8 and MLX runs pass both labelled corpora and backend parity;
[reports](benchmarks/README.md) record measured RAM/latency and conservative recall.
Real local Qwen tools and Mac launchd restart have separate acceptance reports.
Actual owner Mac app controls/permissions, live Telegram and real issuer/provider
accounts still require their own acceptance evidence.
OpenDuet does not claim access to Anthropic's private implementation or accounts,
its proprietary payment partner APIs, or unverified full behavioral equivalence.
