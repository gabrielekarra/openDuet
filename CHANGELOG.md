# Changes

## 0.4.0rc3

- Read uploaded files with exact page, paragraph, slide and sheet-cell locators,
  durable SHA-256 snapshots, bounded pagination and current-task access controls.
  Uploaded spreadsheet formulas remain inert and report saved cached values.
- Export clickable sources in DOCX, PPTX, PDF and XLSX, with local excerpts in
  offline appendices. Revisions retain their source snapshots and input access;
  unknown/foreign references remain rejected.
- Send uploaded-file IDs separately from web chat text, so long extracted files
  do not overflow the message field. Make previews show the cited locator and
  excerpt at desktop, tablet and phone widths.
- Add an explicitly opt-in read-only connector contract runner. Its report saves
  schema checks and counts, without provider records or credentials.

## 0.4.0rc2

- Resume safe interrupted tasks automatically after a process restart. Bind
  prepared actions to the reviewed tool schema, policy, endpoint and account;
  changed or legacy unbound actions need a fresh review.
- Connect confidential OAuth clients from the console, including private client
  secrets, offline consent options and serialized rotating refresh tokens.
  Replacing/disconnecting an account invalidates pending authorization and
  prevents stale discovery or callbacks from restoring it.
- Normalize paginated Gmail, Calendar, Slack, Stripe and Graph results. Preserve
  cursors on MCP errors and prevent in-flight polls from restoring disconnected
  data. Stripe invoice values retain their original currency units.
- Give retrieved list records individual source references, reject unknown or
  foreign-task export citations, and link sourced XLSX cells with comments.
- Record actual MLX Metal allocator peaks, exposed hardware and library versions.
  Preserve precision-specific parity results and failed benchmark evidence.
- Verify console OAuth through actual HTTP MCP discovery and task execution;
  expand crash, token, pagination, source and model-admission checks.

## 0.4.0rc1

- Private Mac installation with `setup`, automatic login services, restart
  recovery, one-use browser sign-in and `doctor` diagnostics.
- Guided Telegram pairing, Mac permissions and real model/tool-call checks.
  On-demand Mac app control and screenshots remain available through Telegram.
- Verified local Qwen/Ollama work in native and text tool protocols. The host
  checks that requested deliverable files actually exist before marking work ready.
- Direct email accounts with encrypted app passwords, read-only IMAP polling,
  Sent-folder discovery, configurable cadence and optional approved SMTP sends.
  Both implicit TLS and mandatory STARTTLS are supported.
- Anchored, debiased Kev questions and a binary time-critical readout. Real
  model evaluation includes a separate frozen 24-case English/Italian corpus,
  interruption recall, fingerprints and Torch/MLX parity checks.
- CPU INT8 weight loading through Quanto, retaining the trained pointer head
  and LoRA adapter; MLX retains its pinned Apple-silicon checkpoint.
- Model editing preserves credentials, separates colliding profile names and
  exposes context/output limits. Connector bearer tokens stay in the vault.

See [validation](docs/VALIDATION.md) for measured results and live-device/account
acceptance still requiring the owner's environment.

## 0.3.0 — 2026-10-22

- Make Telegram the primary owner-paired interface, sharing durable tasks,
  messages, approvals, media and deliverables with the portable console.
- Add on-demand Mac app control and screenshot delivery without screen sharing.
- Port Kev decisions, connector events, deterministic attention policy, learning,
  local-time briefs, commitments and evaluation into the portable runtime.
- Add encrypted credentials, OAuth/PKCE, dynamic MCP connections, declarative
  plugins, password-manager injection and optional scoped issuer purchases.
- Add live financial formulas, native Office validation, versioned dashboards,
  isolated web prototypes and a separate browser computer with egress controls.
- Replace the native app, continuous sensors, generation daemon, TTS, licensing,
  VNC and native release pipeline. Preserve native history at `bobb-mac-final`.
- Add responsive/dark console modules, original glasses assets, runtime/browser
  regression fixtures and real Chromium/LibreOffice acceptance checks.
- Record the first real Kev CPU/bfloat16 benchmark without treating its failed
  quality gate as a passing model baseline; preserve explicit live acceptance gaps.
