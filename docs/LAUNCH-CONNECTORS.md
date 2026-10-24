# Launch connector setup

Checked against the linked provider or maintainer documentation on **24 October
2026**. These are operator instructions for the 17 directory entries, not live
account certifications. Hosted services change tool names, schemas, plans and
scopes. Discover the actual tools before writing a polling or acceptance plan;
do not copy illustrative fixture tool names into a live plan.

## Before connecting

For hosted MCP, use Connections → Add connection. Paste the endpoint below;
entries without a prefilled endpoint need the manual form. Register the callback
URL displayed by OpenDuet with the provider, including its exact scheme, hostname,
port and path. Use a public HTTPS workspace origin where required. Supply a
client ID and private client secret only for providers requiring a pre-registered
app. Dynamic client registration (DCR) providers normally need neither field.
The console stores supplied secrets in the encrypted vault.

Start with read permissions. Inspect the discovered tool list and exclude tools
outside the intended workflow. OpenDuet reviews consequential calls, but a
provider's claimed read-only annotation is a trust boundary. A general-purpose
API, connector-directory listing or logo does not establish entitlement to every
advertised workflow. Follow [connection setup](CONNECTING-SERVICES.md) and
[credential/security guidance](SECURITY.md).

For a local stdio bridge, install a reviewed release and its dependencies on the
machine running the workspace. Configure its absolute command/entrypoint in
`openduet.toml`, then restart that workspace. The web form installs no software.
Pass credential **environment variable names**, never secret values in command
arguments. Ensure the service process actually receives those variables;
an interactive shell's exports do not automatically reach launchd or Docker.

```toml
# Template: replace both absolute paths with the reviewed installation.
[connectors.example]
command = "/absolute/path/to/node"
args = ["/absolute/path/to/reviewed-server-entrypoint.js"]
env_names = ["PROVIDER_CLIENT_ID", "PROVIDER_CLIENT_SECRET"]
excluded_tools = []
```

Some maintainers use a binary or Python entrypoint instead of Node; use that
server's documented executable. Keep credential files private and outside Git.
Use the [opt-in read-only checker](CONNECTOR-ACCEPTANCE.md) against a test account
after discovery. It records private counts/schema digests, not record bodies.

## Gmail

**Official MCP:** `https://gmailmcp.googleapis.com/mcp/v1`.
[Google setup](https://developers.google.com/workspace/guides/configure-mcp-servers).

Enable the relevant Workspace Developer Preview access/APIs in your Google
project and configure an OAuth consent screen and web client. Add OpenDuet's
displayed redirect URI and supply the client ID/secret in Connections. Begin with
`https://www.googleapis.com/auth/gmail.readonly`. The directory requests offline
access and consent for a refresh token; test-mode app/user and Workspace admin
restrictions still apply. Add Gmail send scope only when sending is intended.
Reading a message list may require a separate discovered get-message tool for
headers/body. Missed-message triage prepares replies; actual sends need review.

## Google Calendar

**Official MCP:** `https://calendarmcp.googleapis.com/mcp/v1`.
[Google setup](https://developers.google.com/workspace/guides/configure-mcp-servers).

Use the same project/client setup as Gmail, authorizing this connection
separately. Start with `https://www.googleapis.com/auth/calendar.readonly`;
request `calendar.events` only for intended calendar edits. Check the calendar
IDs and account timezone returned by discovery/read tools. Inviting attendees,
moving or cancelling an event changes external state and needs review. Shared
calendar access depends on the authenticated user's actual permissions.

## Google Drive

**Official MCP:** `https://drivemcp.googleapis.com/mcp/v1`.
[Google setup](https://developers.google.com/workspace/guides/configure-mcp-servers).

Configure the Google OAuth web client and exact OpenDuet callback. Start with
`https://www.googleapis.com/auth/drive.readonly`; `drive.file` has narrower
per-file behavior and is not equivalent to access to all existing Drive files.
Check shared-drive support and export MIME types in the discovered tool schema.
Cloud-document retrieval/export differs from ordinary file download. Uploads,
edits and permission changes require review.

## Slack

**Official MCP:** `https://mcp.slack.com/mcp`.
[Slack setup](https://docs.slack.dev/ai/slack-mcp-server/).

Create/configure the required Slack app and OAuth redirect for OpenDuet; Slack
does not provide DCR for this server. Supply the registered client ID/secret and
obtain workspace/admin approval where required. Choose the user scopes needed
for the intended surfaces, such as `search:read.public` and
`search:read.private`; IM/MPIM and file access require their corresponding
scopes. Add `chat:write` only for sending. Private-channel visibility follows
membership and approved scopes. Search/read is distinct from posting, replies,
reactions or edits; review every intended write.

## Stripe

**Official MCP:** `https://mcp.stripe.com`.
[Stripe setup](https://docs.stripe.com/mcp).

Use Stripe's documented account authorization flow in Connections, selecting a
test/sandbox account first and the least access the workflow needs. Inspect
available invoice/customer tools and which mode/account is actually authorized.
For invoice reminders, retrieve the invoice and customer record, preserve the
currency and provider's minor-unit amount, then prepare an approved message.
Write access is optional. This ordinary business connector does **not** connect
a payment wallet or grant Stripe Issuing eligibility; purchases remain #18.

## QuickBooks

**Official local stdio bridge:**
[Intuit quickbooks-online-mcp-server](https://github.com/intuit/quickbooks-online-mcp-server).

Create an Intuit OAuth app, select a QuickBooks sandbox company and follow the
repository's build/authentication instructions. Configure its built Node
entrypoint with private environment bindings `QUICKBOOKS_CLIENT_ID`,
`QUICKBOOKS_CLIENT_SECRET`, `QUICKBOOKS_REFRESH_TOKEN`,
`QUICKBOOKS_REALM_ID` and `QUICKBOOKS_ENVIRONMENT`. Use the maintainer's
`QUICKBOOKS_DISABLE_WRITE`, `QUICKBOOKS_DISABLE_UPDATE` and
`QUICKBOOKS_DISABLE_DELETE` controls for a read-only first connection. Arrange
refresh-token persistence/rotation as documented by Intuit. Accounting scope
does not bypass company permissions. Production OAuth callbacks require HTTPS.
The hosted [Intuit pilot](https://github.com/IntuitDeveloper/intuit-3p-ai-pilot)
has invitation/app/network requirements; it is not a generally available default.
Invoice `TotalAmt`/`Balance` are major currency units; do not apply Stripe's
minor-unit conversion to them.

## Gusto

**Official MCP:** `https://mcp.api.gusto.com`.
[Gusto account integration](https://gusto.com/product/integrations/gusto-mcp)
and [agent requirements](https://gusto.com/product/agents).

Gusto requires an eligible full/primary administrator account, an isolated
client environment/session and **manual confirmation for every tool call**.
The hosted server uses OAuth/DCR. An embedded-payroll documentation MCP endpoint
is documentation search, not an account/payroll connection.

The current main branch enforces a fresh, dedicated profile for this endpoint:
every read/write requires approval, other account tools and background polling
are unavailable, and prior conversation/shared memory is excluded. The profile
remains reserved after disconnect, so it cannot be rebound to another provider.
Use `openduet setup --directory /absolute/path/to/private-gusto-profile`; choose
unused listener/prototype ports in its generated `openduet.toml` before starting
it with `openduet --config /absolute/path/to/private-gusto-profile/openduet.toml`.
Connect Gusto before creating tasks or importing any history/accounts. The
immutable rc3 tag predates this enforcement: leave Gusto disabled on rc3.

Payroll preparation must show the actual employees/pay period/totals; running or
changing payroll needs explicit review and the provider's authorized account.
Passing the fixture policy checks does not certify a live payroll account.

## HubSpot

**Official MCP:** `https://mcp.hubspot.com`.
[HubSpot setup](https://developers.hubspot.com/docs/apps/developer-platform/build-apps/integrate-with-the-remote-hubspot-mcp-server).

Register the integration's client credentials and exact callback following the
current HubSpot guide. Use OpenDuet's confidential OAuth flow/PKCE where required;
retain rotating refresh tokens through the vault rather than copying them into
a static header. Begin with contacts/deals read scopes and check portal
permissions and supported objects. Draft follow-ups from referenced contact/deal
records. Updating the CRM or sending a follow-up requires review and additional
authorized scopes. API access and object availability vary by account plan.

## Docusign

**Official demo MCP:** `https://mcp-d.docusign.com/mcp`.
[Docusign developer setup](https://developers.docusign.com/platform/mcp-server/anthropic-claude/claude-code/).

Create a Docusign developer account and integration key/client credentials.
Register **OpenDuet's displayed callback**, rather than the Claude-specific
callback shown in the vendor's example. Start against the demo endpoint and
grant the documented signature/access scopes. Verify account ID, template access
and envelope status using discovered read tools. Preparing a contract is distinct
from sending an envelope, signing or voiding it; review each intended change.
Production requires separate provider approval/account configuration; the demo
endpoint and tests do not establish production entitlement.

## Calendly

**Official MCP:** `https://mcp.calendly.com`.
[Setup](https://developer.calendly.com/docs/mcp/calendly-mcp-server) and
[supported tools](https://developer.calendly.com/docs/mcp/supported-tools).

Use OAuth with DCR/PKCE; normally leave the manual client fields empty.
Personal access tokens are not supported by this MCP endpoint. Authorize the
intended user/organization, then inspect actual event-type and scheduled-event
read tools. Booking, routing and organization access depend on the Calendly
plan/role. Check invitee timezone and intended event type before an approved
booking, reschedule or cancellation. A list-events response alone does not
establish free/busy coverage for every connected calendar.

## LinkedIn

**Community local stdio bridge:**
[anubisalpha/linkedin-mcp](https://github.com/anubisalpha/linkedin-mcp).

Review/install the maintainer's release and configure its documented executable
and private auth environment/file bindings. Create an eligible LinkedIn developer
app and enable the official sign-in/Share on LinkedIn products required by that
bridge; authorize the intended member. `w_member_social` permits eligible
member publishing and is not blanket access to LinkedIn data.
This bridge uses official APIs rather than scraping. A member-profile/post
connection does **not** grant LinkedIn Jobs/Talent Solutions entitlement.
Job-board publication remains unavailable without a separately approved API
product; the agent can draft the listing. Review actual post publication.

## Canva

**Official MCP:** `https://mcp.canva.com/mcp`.
[Canva setup](https://www.canva.dev/docs/apps/mcp/) and
[access requirements](https://www.canva.dev/docs/apps/mcp/access/).

Follow Canva's current developer-portal setup for outside-Canva capabilities and
the client/app access settings required by its OAuth MCP flow. Use the exact
callback displayed by OpenDuet when registering your client. Authorize only
intended design/content access, then inspect available tools and owned/shared
designs. Brand templates, autofill and other premium actions depend on the plan
and app approval. Creating/updating designs or publishing a campaign needs
review; discovery is not a license to third-party assets.

## Shopify

**Community local stdio Admin bridge:**
[GeLi2001/shopify-mcp](https://github.com/GeLi2001/shopify-mcp).

Use the maintainer's `shopify-mcp` executable/entrypoint, Node 18+ and a reviewed
release. Configure the intended store's admin app and required
`read_products`/`write_products` or other explicit Admin API scopes. Bind
`SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET` and `MYSHOPIFY_DOMAIN` privately
for the documented 2026 client-credentials flow, or the documented legacy
`SHOPIFY_ACCESS_TOKEN` method where the store supports it. Never put secrets in
CLI flags even if an example offers them. Start read-only and check the store
domain/API version. Product/customer/order changes require review. Shopify's
Storefront/Cart MCP is a different surface and does not grant store-management
Admin access.

## Notion

**Official MCP:** `https://mcp.notion.com/mcp`.
[Notion setup](https://developers.notion.com/guides/mcp/get-started-with-mcp).

Connect using the official hosted OAuth flow and select only the intended
workspace/pages. Inspect discovered search/fetch tools and the content shared
with the connection. Enterprise allowlists and workspace settings can restrict
the available tools; do not assume every account exposes the same schema.
Creating/editing pages, databases or comments needs review and write access.
A search title is not the page body; fetch the actual source before citing its
contents.

## Ramp

**Official MCP:** `https://mcp.ramp.com/mcp`.
[Ramp setup](https://docs.ramp.com/developer-api/v1/guides/ramp-mcp-remote).

Follow Ramp's OAuth client and callback-allowlisting requirements for your
organization, supplying client credentials if required. Start with intended
finance read access and verify organization/role restrictions and discovered
transaction tools. `https://demo-mcp.ramp.com/mcp` returns sample data: it is
useful for exploration but is not acceptance of the owner's Ramp account.
Payments, approvals, card or other financial mutations require review and the
provider's actual entitlements.

## Microsoft 365

**Community local stdio bridge:**
[Softeria/ms-365-mcp-server](https://github.com/Softeria/ms-365-mcp-server).

Use Node 20+ and the reviewed `@softeria/ms-365-mcp-server` release. Start with
the maintainer's `--read-only --preset mail` options, or another narrowly scoped
preset for Calendar/OneDrive. Follow its MSAL tenant/client-ID configuration and
interactive/device authorization instructions. Limit allowed scopes; tenant admin
consent can be required. Mail.Read, Calendars.Read and Files.Read serve different
surfaces; enable Mail.Send only for an intended approved send. Use JSON output
for OpenDuet polling/contract checking, rather than TOON output. Shared mailboxes,
personal vs organizational tenants and admin policies affect actual access.

<a id="caldav"></a>

## CalDAV / Apple Calendar

**Community self-hosted HTTP bridge:**
[gelse/caldav-mcp](https://github.com/gelse/caldav-mcp).

Install the reviewed server and follow its HTTP deployment instructions. For its
single-account environment fallback, privately bind `CALDAV_URL`,
`CALDAV_USERNAME` and `CALDAV_PASSWORD`; configure the bridge's private MCP
bearer/API key. For iCloud use an app-specific password, not your Apple account
password. Add the resulting HTTPS endpoint in Connections with its private bearer
token, or explicitly configured loopback HTTP when both processes share a host.
The sample local port is not a remote hosted service; replace it with your
actual endpoint. Calendar visibility follows provider ACLs. Reading calendars
does not authorize creating/updating/deleting events or invitations.

## Acceptance boundary

The five business recipes are tested with disposable fixture transports.
The release's provider-shaped ingestion coverage and opt-in runner are recorded
in [validation](VALIDATION.md) and [account acceptance](CONNECTOR-ACCEPTANCE.md).
All 17 schema-derived service fixtures cross actual HTTP/stdio MCP transport,
source capture, event normalization/deduplication and exact one-use approval.
These synthetic fixtures and illustrative tool names are not captured private
provider sessions or vendor tool catalogues. No live account is certified by
this guide.
