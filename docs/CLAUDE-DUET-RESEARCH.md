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

## Capability-by-capability implementation

**Implemented** means there is an executable path, not a claim that every model
or third-party service has passed real-world acceptance tests. **Configured**
means it needs the user's own model, MCP service, accounts or infrastructure.

| Capability | OpenDuet path | Status / practical boundary |
| --- | --- | --- |
| Main conversation | Home, persisted messages and task history | Implemented |
| Topic channels | Named channels with shared reviewed memory | Implemented |
| Choose any model | Per-task provider selection; local/hosted compatibility adapters | Implemented; model capability varies |
| Models without tool calling | JSON text tool protocol, validated before execution | Implemented; requires a model able to follow the format |
| Morning brief | Scheduled inbox/calendar assignment | Configured MCP data required |
| Periodic proactive check-ins | Durable routines; NO_UPDATE suppresses quiet notifications | Implemented; judgment depends on selected model |
| Follow-ups and meeting preparation | Recurring instructions + connected sources | Configured; not hardcoded email-provider access |
| Long-running delegated work | Server-side bounded agent loop | Implemented; server/model must remain online |
| Separate computer | Deploy service/browser on a user-owned VM | Configured; no automatic VM provisioning |
| Remote access to your computer | Computers tab, authenticated noVNC relay, native Mac service lifecycle and screen handoff | Implemented extension; user configures screen sharing and private connectivity |
| Task progress and user decisions | Task states, errors, pending calls and review events | Implemented |
| User-only completion | Ready-for-review vs completed | Implemented |
| Generated documents | Markdown/text/DOCX | Implemented |
| Spreadsheets/financial work | CSV/XLSX data workbooks | Implemented; formula execution/modeling is not verified |
| Slides | PPTX title/body deck generation | Implemented; basic layouts |
| Dashboards/prototypes | Downloadable HTML artifacts | Implemented; no arbitrary code execution or hosted publishing |
| Make gallery | Downloads and versioned text editing | Implemented |
| Search prior chats | SQLite FTS, opt-out, channel deletion removes index | Implemented; last 100 messages per page |
| Shared memories | Review/edit-by-replacement, forget, JSON export, text import | Implemented within workspace; separate from native Mac memory |
| Reusable skills | Reviewed instructions in Settings, small business example | Implemented; no automatic installation of third-party code |
| Connector/plugin discovery | MCP tool discovery and named configuration | Implemented; no promise of 6,000 bundled/tested connectors |
| Gmail/Calendar/Drive/Slack | User-configured compatible MCP servers | Configured; service authorization required |
| QuickBooks/HubSpot/DocuSign/Calendly | Same MCP extension interface | Configured; no bundled bespoke adapters |
| Stripe unpaid invoices | MCP + small business skill + reviewed drafts | Configured; no real account used in tests |
| Payroll and contracts | Draft artifacts from configured source data | Configured; no automatic payroll submission/legal validation |
| Link wallet | Proprietary partner connection/card issuance | **Not implemented**; no equivalent service agreement/credentials |
| Shop Pay wallet | Proprietary partner connection/card issuance | **Not implemented**; no equivalent service agreement/credentials |
| Browser without connector | Optional Playwright persistent Chromium profile | Implemented; allowlisted sites and approvals required |
| Private browser login | Separate authenticated form, no model/chat credential entry | Implemented; no visual browser takeover |
| Sensitive action review | Exact stored call payload, one-use review, expiry | Implemented; every connector call asks unless operator marks tool safe |
| Restart/retry safety | Checkpoints, uncertain-effect stop, explicit verified resolution | Implemented; external services cannot guarantee exactly-once delivery |
| Credential separation | Environment bindings; private login values; receipt redaction | Implemented; operator is trusted and owns the server |
| Prompt injection defenses | Untrusted-content prompt, schemas, tool boundaries, host approvals | Implemented layers; no claim of Anthropic classifier parity |
| Sensitive information filtering | Card checksum/US identification checks + bound-secret redaction | Basic deterministic checks; **not** a comprehensive DLP classifier |
| Financial restrictions | Exclude forbidden tools; review all other calls | Operator policy; no securities/transfer workflows supplied |
| Voice messages | Optional local Whisper; existing on-device Mac dictation | Implemented; download local model separately |
| Spoken responses | Local system voices on Mac / supported browsers | Implemented where available |
| iOS / Android | Responsive installable web app | Implemented web access; **not native App Store apps** |
| Notifications | Event feed, browser notifications and optional relay | Relay required when web app is closed |
| Usage limits | Per-day token ledger and per-task turn limits | Implemented; omitted provider counts are estimated |
| Claude account memory/apps | No access to Anthropic private account internals | **Not implemented**; manual memory import and independent connections |

## Validation and remaining work

Automated runtime tests cover three provider wire formats, no-key local access,
text tool calls, real MCP stdio discovery/calls, schema denial, approval replay,
revocation, cancellation, uncertain effects, budgets, schedules, deletion,
authentication and real Office file parsing. Model calls use fixtures; these
tests establish runtime behavior, not the selected LLM's reasoning quality.

Production acceptance still needs actual accounts and each intended model:
inbox selection, calendar time zones, real OAuth servers, live delivery receipts,
browser sign-ins, prompt-injection evaluation, data-leak evaluation, long-running
reliability, accessibility and native/mobile distribution. Wallet parity needs
an independently available payment provider integration. Full Claude Duet parity
is therefore **not claimed** by this preview.
