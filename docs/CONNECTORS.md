# Connections and business workflows

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
