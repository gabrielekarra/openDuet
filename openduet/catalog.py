"""Curated capabilities and least-privilege setup links; never auto-connect accounts."""

SERVICES = [
    (
        "gmail",
        "Gmail",
        "mail",
        "https://developers.google.com/workspace/guides/configure-mcp-servers",
        ["gmail.readonly", "gmail.send"],
    ),
    (
        "google-calendar",
        "Google Calendar",
        "calendar",
        "https://developers.google.com/workspace/guides/configure-mcp-servers",
        ["calendar.readonly", "calendar.events"],
    ),
    (
        "google-drive",
        "Google Drive",
        "files",
        "https://developers.google.com/workspace/guides/configure-mcp-servers",
        ["drive.readonly", "drive.file"],
    ),
    (
        "slack",
        "Slack",
        "chat",
        "https://docs.slack.dev/ai/slack-mcp-server",
        ["search:read.public", "search:read.private", "chat:write"],
    ),
    ("stripe", "Stripe", "invoices", "https://docs.stripe.com/mcp", ["invoices:read", "customers:read"]),
    (
        "quickbooks",
        "QuickBooks",
        "invoices",
        "https://developer.intuit.com/app/developer/qbo/docs/get-started",
        ["com.intuit.quickbooks.accounting"],
    ),
    ("gusto", "Gusto", "payroll", "https://docs.gusto.com/", ["payrolls:read", "payrolls:write"]),
    (
        "hubspot",
        "HubSpot",
        "crm",
        "https://developers.hubspot.com/docs/apps/developer-platform/build-apps/integrate-with-the-remote-hubspot-mcp-server",
        ["crm.objects.contacts.read", "crm.objects.deals.read"],
    ),
    (
        "docusign",
        "Docusign",
        "signatures",
        "https://developers.docusign.com/docs/esign-rest-api/",
        ["signature"],
    ),
    ("calendly", "Calendly", "calendar", "https://developer.calendly.com/", ["scheduled_events:read"]),
    (
        "linkedin",
        "LinkedIn",
        "publishing",
        "https://learn.microsoft.com/en-us/linkedin/",
        ["w_member_social"],
    ),
    (
        "canva",
        "Canva",
        "design",
        "https://www.canva.dev/docs/connect/",
        ["design:content:read", "design:content:write"],
    ),
    (
        "shopify",
        "Shopify",
        "commerce",
        "https://shopify.dev/docs/apps/build/storefront-mcp",
        ["read_products", "write_products"],
    ),
    (
        "notion",
        "Notion",
        "files",
        "https://developers.notion.com/docs/mcp",
        ["read_content", "insert_content"],
    ),
    ("ramp", "Ramp", "finance", "https://docs.ramp.com/", ["transactions:read"]),
    (
        "microsoft-365",
        "Microsoft 365",
        "mail/calendar/files",
        "https://learn.microsoft.com/en-us/graph/permissions-reference",
        ["Mail.Read", "Mail.Send", "Calendars.Read", "Files.Read"],
    ),
    (
        "caldav",
        "CalDAV / Apple Calendar",
        "calendar",
        "https://github.com/cktr/calDAV-MCP",
        ["calendar-read", "calendar-write"],
    ),
]
OFFICIAL_MCP = {
    "gmail": "https://gmailmcp.googleapis.com/mcp/v1",
    "google-calendar": "https://calendarmcp.googleapis.com/mcp/v1",
    "google-drive": "https://drivemcp.googleapis.com/mcp/v1",
    "hubspot": "https://mcp.hubspot.com",
    "stripe": "https://mcp.stripe.com",
    "notion": "https://mcp.notion.com/mcp",
    "slack": "https://mcp.slack.com/mcp",
    "canva": "https://mcp.canva.com/mcp",
    "gusto": "https://mcp.api.gusto.com",
    "docusign": "https://mcp-d.docusign.com/mcp",
    "calendly": "https://mcp.calendly.com",
    "ramp": "https://mcp.ramp.com/mcp",
}
SETUP = {
    "gmail": (
        "https://developers.google.com/workspace/guides/configure-mcp-servers",
        "oauth-client",
        "Developer Preview; enable the project/API and use your own client ID/secret. Start with read-only access.",
    ),
    "google-calendar": (
        "https://developers.google.com/workspace/guides/configure-mcp-servers",
        "oauth-client",
        "Developer Preview; project/API enablement and your own OAuth client are required. Event changes require approval.",
    ),
    "google-drive": (
        "https://developers.google.com/workspace/guides/configure-mcp-servers",
        "oauth-client",
        "Developer Preview; grant only the Drive scope needed. File access follows your account permissions.",
    ),
    "slack": (
        "https://docs.slack.dev/ai/slack-mcp-server/",
        "oauth-client",
        "Slack does not support dynamic registration. Create a Slack app/client and obtain workspace-admin approval; scopes differ by tool.",
    ),
    "stripe": (
        "https://docs.stripe.com/mcp",
        "oauth-or-bearer",
        "Use a restricted key or approved OAuth connection; test and live modes are separate. The ordinary Stripe connector does not issue purchase cards.",
    ),
    "quickbooks": (
        "https://github.com/intuit/quickbooks-online-mcp-server",
        "operator-stdio",
        "Intuit's local server needs a developer app, realm ID and rotating refresh token. Start with its sandbox and write/update/delete restrictions; hosted MCP is invitation-only.",
    ),
    "gusto": (
        "https://gusto.com/product/integrations/gusto-mcp",
        "oauth-dcr-isolated",
        "Primary/full admin and dynamic registration required. Use a fresh dedicated OpenDuet profile; every tool read/write requires confirmation and background polling is disabled.",
    ),
    "hubspot": (
        "https://developers.hubspot.com/docs/apps/developer-platform/build-apps/integrate-with-the-remote-hubspot-mcp-server",
        "oauth-client",
        "Provider-issued client ID/secret and PKCE; refresh tokens rotate. Account/tool availability and permissions apply.",
    ),
    "docusign": (
        "https://developers.docusign.com/platform/mcp-server/anthropic-claude/claude-code/",
        "oauth-client",
        "The prefilled endpoint is Docusign demo. Create an integration key/secret and register OpenDuet's exact callback; production uses separate account/application settings.",
    ),
    "calendly": (
        "https://developer.calendly.com/docs/mcp/calendly-mcp-server",
        "oauth-dcr",
        "Hosted-only server with dynamic registration and PKCE. Leave client credentials blank; console-issued clients are not supported by this MCP service.",
    ),
    "linkedin": (
        "https://github.com/anubisalpha/linkedin-mcp",
        "operator-stdio",
        "Community server using the official LinkedIn API. Register a developer app and authorize its limited scopes. Publishing needs approval; this is not a scraping or job-board API entitlement.",
    ),
    "canva": (
        "https://www.canva.dev/docs/apps/mcp/",
        "oauth",
        "Hosted Canva account authorization. Design permissions and plan/export limits apply; publish/share actions remain approved.",
    ),
    "shopify": (
        "https://github.com/GeLi2001/shopify-mcp",
        "operator-stdio",
        "Use a reviewed Admin API bridge for merchant/store management with least-privilege store scopes. Storefront/customer/cart MCPs are different products and do not grant admin access.",
    ),
    "notion": (
        "https://developers.notion.com/guides/mcp/get-started-with-mcp",
        "oauth",
        "Authorize only the intended workspace/content. Enterprise client allowlists can require admin approval; tool discovery is authoritative.",
    ),
    "ramp": (
        "https://docs.ramp.com/developer-api/v1/guides/ramp-mcp-remote",
        "oauth-allowlist",
        "Ramp account and redirect-URI allowlisting for custom clients. demo-mcp.ramp.com/mcp serves sample data; it is not live financial acceptance.",
    ),
    "microsoft-365": (
        "https://github.com/Softeria/ms-365-mcp-server",
        "operator-stdio",
        "Community Microsoft Graph bridge, Node 20+. Start with --read-only and a narrow preset/allowed scopes; tenant admin consent can be required. Use JSON output for event polling.",
    ),
    "caldav": (
        "https://github.com/gelse/caldav-mcp",
        "operator-http",
        "Self-hosted CalDAV bridge with provider credentials held by that server. Configure one account in its environment and connect OpenDuet with its private MCP bearer token; use an iCloud app password where required.",
    ),
}
GOOGLE_SCOPES = {
    "gmail": "https://www.googleapis.com/auth/gmail.readonly",
    "google-calendar": "https://www.googleapis.com/auth/calendar.readonly",
    "google-drive": "https://www.googleapis.com/auth/drive.readonly",
}


def directory():
    return [
        {
            "id": key,
            "name": name,
            "capability": capability,
            "setup_url": SETUP[key][0],
            "auth_mode": SETUP[key][1],
            "guide_url": "https://github.com/gabrielekarra/openDuet/blob/main/docs/LAUNCH-CONNECTORS.md#"
            + key,
            "documentation_checked": "2026-10-24",
            "scopes": scopes,
            "url": OFFICIAL_MCP.get(key, ""),
            "oauth": {"scope": GOOGLE_SCOPES[key], "access_type": "offline", "prompt": "consent"}
            if key in GOOGLE_SCOPES
            else {},
            "limits": SETUP[key][2],
            "read_actions": ["list", "search", "get", "read"],
            "approval_actions": ["send", "create", "update", "pay", "sign", "delete", "publish"],
        }
        for key, name, capability, url, scopes in SERVICES
    ]


RECIPES = {
    "missed-messages": {
        "connectors": ["gmail", "slack"],
        "prompt": "Read recent unanswered messages, cite each source, and prepare reply drafts. Ask before sending.",
    },
    "unpaid-invoices": {
        "connectors": ["stripe", "quickbooks"],
        "prompt": "Find overdue invoices and prepare customer reminders with invoice references. Ask before sending.",
    },
    "meeting-scheduling": {
        "connectors": ["google-calendar", "calendly"],
        "prompt": "Read availability and propose a meeting without conflicts. Ask before inviting or moving events.",
    },
    "contract-preparation": {
        "connectors": ["docusign"],
        "prompt": "Prepare the requested agreement and flag every clause needing review. Ask before signature or delivery.",
    },
    "payroll-preparation": {
        "connectors": ["gusto"],
        "prompt": "Prepare payroll from verified records, show payees and totals with sources. Ask before running payroll.",
    },
}
