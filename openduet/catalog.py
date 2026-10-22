"""Curated capabilities and least-privilege setup links; never auto-connect accounts."""

SERVICES = [
    (
        "gmail",
        "Gmail",
        "mail",
        "https://developers.google.com/gmail/api/auth/scopes",
        ["gmail.readonly", "gmail.send"],
    ),
    (
        "google-calendar",
        "Google Calendar",
        "calendar",
        "https://developers.google.com/calendar/api/auth",
        ["calendar.readonly", "calendar.events"],
    ),
    (
        "google-drive",
        "Google Drive",
        "files",
        "https://developers.google.com/drive/api/guides/api-specific-auth",
        ["drive.readonly", "drive.file"],
    ),
    ("slack", "Slack", "chat", "https://docs.slack.dev/ai/slack-mcp-server", ["search:read", "chat:write"]),
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
        "https://developers.hubspot.com/mcp",
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
    "stripe": "https://mcp.stripe.com",
    "notion": "https://mcp.notion.com/mcp",
    "slack": "https://mcp.slack.com/mcp",
    "canva": "https://mcp.canva.com/mcp",
}


def directory():
    return [
        {
            "id": key,
            "name": name,
            "capability": capability,
            "setup_url": url,
            "scopes": scopes,
            "url": OFFICIAL_MCP.get(key, ""),
            "limits": "Use an operator-reviewed MCP server; provider account, scopes and regional availability apply.",
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
