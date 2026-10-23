# Connections and business workflows

## Email without an MCP server

In Connections, expand **Add email account**, select a provider preset and enter
the account name and a provider-issued app password. The password is verified
over TLS and stored in the encrypted vault. Normal account passwords and OAuth
access tokens are not interchangeable with app passwords. Some managed accounts
disable this method; use an authorized MCP/OAuth connection instead.

| Preset | Read access | Optional approved sends |
| --- | --- | --- |
| Gmail | `imap.gmail.com:993`, TLS | `smtp.gmail.com:465`, TLS |
| iCloud | `imap.mail.me.com:993`, TLS | `smtp.mail.me.com:587`, mandatory STARTTLS |
| Yahoo | `imap.mail.yahoo.com:993`, TLS | `smtp.mail.yahoo.com:465`, TLS |

See [Apple's settings](https://support.apple.com/en-us/102525) and
[Google app passwords](https://support.google.com/accounts/answer/185833).
Other providers can supply their own hosts, ports and SMTP encryption mode.
Certificate and hostname verification stay enabled. STARTTLS must complete
before authentication; a server without it is refused.

Sending starts disabled. Enable **approved sends** only if you want the agent
to send mail; every recipient, subject and body still needs a one-use approval.
Connecting or testing an account never sends a message. A successful SMTP
receipt means the server accepted the message, not that the recipient read it.

Inbox reads do not mark messages as read. The initial scan uses the newest 50
messages per selected folder, then durable UID cursors collect new mail in
bounded batches. The special-use Sent folder is discovered automatically; you
can also enter its exact name. The agent reads bounded message text, excluding
attachments and quoted history. Account checks use the cadence in Proactivity.
Disconnect immediately removes local access and associated events and learning.

## MCP connections

Use Connections to browse the curated directory, add a reviewed remote MCP
server and authorize the desired account. The directory lists service setup
links, capabilities, suggested scopes and actions that need review. Suggested
scopes are a starting point; actual scopes depend on the chosen server/provider.

Entries cover Gmail, Google Calendar/Drive, Slack, Stripe, QuickBooks, Gusto,
HubSpot, Docusign, Calendly, LinkedIn, Canva, Shopify, Notion, Ramp,
Microsoft 365 and CalDAV. Where a published MCP endpoint is known it is
pre-filled. Other entries require a compatible operator-reviewed server URL;
a catalogue entry does not establish an official integration or live account
verification. Runtime MCP discovery determines the tools actually available.

The SQLite registry reloads without restarting. OAuth discovers protected-resource
and authorization metadata, uses PKCE S256, and supports dynamic client
registration or an operator-provided client ID. Tokens/refresh credentials stay
in the encrypted vault. Disconnect revokes local access immediately, attempts
remote revocation, removes event/learning data and refreshes available tools.
A previously prepared call is revalidated after approval and before execution.

Only remote HTTPS servers (or loopback HTTP for local services) can be added in
the browser. Executable stdio servers require operator TOML configuration with
an explicit command/arguments and named environment bindings. The browser cannot
install an executable MCP server. Do not put tokens in URLs or pasted skill text.

For proactivity, configure a read-only polling tool and event kind, for example:

```toml
[connectors.business]
url = "https://your-reviewed-server.example/mcp"
poll_tool = "list_recent_messages"
event_kind = "mail.received"
poll_seconds = 600
cursor_argument = "cursor"
poll_arguments = {}
```

A generic polling result can return `items` plus `next_cursor`; records require
an `id` and may supply `kind`, `occurred_at`, `actors`, `subject`, `text`, `links`
and `payload`. Returned content remains untrusted. The poll tool's metadata or
operator-reviewed safe configuration must declare it read-only; destructive
annotations override that declaration. Cursors advance with accepted records.

Five recipe buttons prepare missed-message replies, unpaid-invoice reminders,
meeting proposals, contracts and payroll. They use real connected records and
source IDs; they cannot invent records when a connector is missing. Sends,
signatures, payroll submission, payments, deletions and publishing still require
an exact-action approval. A Stripe invoice connector does not grant access to a
purchase wallet. Account availability, regional restrictions and real provider
OAuth behavior are recorded separately from fixture contract tests.
