# Connecting accounts

Open Connections, select a directory entry or add a reviewed MCP URL, then
Authorize with OAuth. No server restart or TOML edit is required for remote
servers. Register the exact callback URL shown in the authorization form with
your provider. Enter its client ID and, if issued, client secret. Leave the ID
blank only when the provider supports dynamic registration. The secret, PKCE
verifier and access/refresh tokens are encrypted in the vault and never included
in tool schemas, task context or the public state API.

Start with read-only scopes. Extra authorization options are restricted to
`access_type` and `prompt`; state, callback, PKCE and resource fields are set by
OpenDuet. Each authorization state expires after ten minutes and is single-use.
Changing or disconnecting a connection invalidates pending authorization and
prepared actions. Rotating refresh tokens are serialized per credential.

## Provider requirements

| Provider | Official MCP URL | Setup boundary |
| --- | --- | --- |
| Gmail | `https://gmailmcp.googleapis.com/mcp/v1` | Google Workspace Developer Preview, enabled project/APIs, client ID and secret |
| Google Calendar | `https://calendarmcp.googleapis.com/mcp/v1` | Same Google preview/project requirements |
| Google Drive | `https://drivemcp.googleapis.com/mcp/v1` | Same Google preview/project requirements |
| HubSpot | `https://mcp.hubspot.com` | Provider-issued client ID/secret, PKCE, eligible account permissions |

Google directory entries prefill only their read-only scope, `access_type=offline`
and `prompt=consent` so the provider can issue a refresh token. HubSpot uses
rotating refresh tokens. Provider account eligibility and preview availability
remain the operator's responsibility. These endpoints were checked against
[Google's setup guide](https://developers.google.com/workspace/guides/configure-mcp-servers)
and [HubSpot's setup guide](https://developers.hubspot.com/docs/apps/developer-platform/build-apps/integrate-with-the-remote-hubspot-mcp-server),
23 October 2026. This is not a claim that private provider accounts were tested.

The directory includes 12 prefilled hosted endpoints and 5 local/operator bridges.
The [17-service setup guide](LAUNCH-CONNECTORS.md) specifies actual authentication
and account/plan limits. Local bridges show a setup link rather than a blank
Connect action. An API documentation link alone does not create an integration.
Tools are discovered from the actual connected server. Only the operator may
configure stdio connectors that execute local programs.

## Event polling

Choose an actual discovered read-only tool, its event kind, JSON arguments and
cursor argument. Keep each response to at most 200 full records. Gmail message
list IDs alone do not contain message bodies: the chosen MCP tool must expand
messages for meaningful triage. Google `nextPageToken`, Slack
`response_metadata.next_cursor`, Stripe `has_more`/last ID and Graph `value` plus
`@odata.nextLink` are recognized; the cursor is sent only to the configured tool,
never fetched as an arbitrary URL. Empty/terminal cursors are omitted on the next
poll. MCP errors preserve the previous cursor and expose a retryable health error.

Fixture acceptance uses a real HTTP MCP process and SDK, synthetic provider-shaped
records and a browser-driven PKCE/token flow. It verifies pagination, edits,
read-state, deduplication and disconnect races without external accounts.

## Dedicated provider profiles

Gusto's official endpoint automatically requires an isolated installation and
manual confirmation of every tool call, including reads. Use a fresh profile
with separate ports and connect it before importing tasks, history or accounts.
The registry rejects mixed configurations or reuse of an existing account/profile.
Other connector/mail tools, background polling and shared/prior-task context are
unavailable; the reservation remains after disconnect. A separate chat thread
inside a mixed profile does not meet this requirement. Operator-configured
connectors can request the same behavior with `exclusive = true`;
`require_approval = true` alone requests manual review for all calls.
