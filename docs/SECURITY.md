# Security boundaries

OpenDuet is a single-owner application. Keep its access token private and expose
the console through HTTPS or an SSH tunnel. Telegram pairing is private,
hashed, single-use and expires after ten minutes. Every message, attachment and
callback is checked against the paired owner and chat. Disconnecting revokes the
bot token locally; rotate compromised bot credentials through BotFather.

The host, rather than model prose, enforces tool schemas, connector availability,
forbidden actions, sensitive identifier checks and consequential-action review.
An approval binds one exact payload and expires after 24 hours. Editing creates
a replacement preview; deferral lets independent work continue. Approved calls
are durably marked before execution. A timeout or service restart cannot prove
that an external effect did not happen: an uncertain result blocks automatic
replay until the owner records a verification receipt.

Tools that transfer between accounts, trade securities/crypto or access another
person's account are forbidden even when safe-listed. Explicit destructive MCP
metadata overrides read-only/safe annotations. Unknown effects need review.
Full cards, supported bank/government identifiers and credential-shaped fields
are blocked in normal tool payloads. Sharing health/financial records outside
the owner conversation requires an explicit user sharing request. These are
deterministic checks, not a comprehensive classifier for every possible
identifier, language, website or encoded secret.

Websites, connector records, mail, forwarded content, skill bodies, files and
prior conversations are untrusted data. They cannot grant permission. Public
browser reads cannot submit non-read HTTP requests; reviewed interaction windows
permit requests from that action. Server-side HTTP semantics remain imperfect:
a website can attach effects to GET or trigger other behavior during a click.
Use reviewed accounts/sites and inspect exact actions. Negative fixtures test
injected POST requests, private/metadata access, schema changes and approvals.

Secrets entered through the console are Fernet-encrypted in SQLite; the key is
stored separately with owner-only permissions or supplied by the operator.
OAuth PKCE verifiers and refresh tokens are encrypted too. Credentials resolve
only at connector, provider, private login or card checkout boundaries. Audits
record references/purpose/time, not values. Known credential values and nested
OAuth tokens are redacted from receipts; Telegram URL logging redacts bot tokens.
Rotate encryption keys in Settings and back up the database and key together.

Dedicated 1Password Connect / Bitwarden scopes bind an exact configured site,
vault item and form selectors. Private values bypass chat/model history and the
page must match the original HTTPS URL for every fill. Card purchases are
disabled by default. Stripe Issuing requires an eligible account, dedicated
cardholder, calendar day/month caps, merchant network IDs, optional issuer category limits, HTTPS authorization webhook and issuer
**decline-on-webhook-timeout** settings. Live keys require explicit operator
configuration. A signed authorization must match merchant, currency and amount;
a second authorization is denied and the card is cancelled after authorization
or expiry. Issuer timeouts reserve budget until verified. The server cannot
configure every external issuer account policy on your behalf.

Prototype files run on a separate origin with an opaque iframe sandbox and CSP
blocking network, forms and workspace APIs. The computer's isolated network and
proxy reject private/loopback/metadata destinations. It receives its own token
and profile only. Local Mac access is opt-in, on-demand and OS-permission bound;
it cannot unlock a locked/logged-out session. Actual permissions, third-party
accounts and issuer settings require target-environment acceptance.

Issuer availability is determined by the business account and region on [Stripe’s current Issuing availability page](https://docs.stripe.com/issuing/availability). No Privacy.com, Link or Shop Pay partner access is claimed.
