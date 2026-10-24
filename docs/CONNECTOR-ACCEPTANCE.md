# Opt-in checks of connected accounts

The portable contract runner tests a service already connected to your running
OpenDuet instance. It makes only the calls explicitly named in your plan, refuses
tools not classified read-only, validates their input schema and checks the
returned record path/fields. It never runs the work LLM or retries a read after a
transport failure. Discovery metadata and operator configuration remain the
trust boundary for a server's claimed read-only behavior.

See the [17-service setup guide](LAUNCH-CONNECTORS.md) for endpoints, OAuth/local
bridge requirements and known account limits. On current main, Gusto requires
a fresh dedicated profile and manual confirmation for every call; the rc3 tag
predates this enforcement and must leave Gusto disabled.

First inspect the actual discovered tools with the authenticated endpoint
`GET /api/connectors/<id>/tools`. Provider tool names and output envelopes vary;
use those names and that provider's documentation. `record_path` is relative to
MCP `structuredContent`, or the first JSON text block when no structured result
exists. A result may be one record or a list. Default minimum is one record;
set zero only for an intentionally empty test account.

Create a private JSON plan, replacing the explicit placeholder below:

```json
{
  "services": [
    {
      "connector": "gmail",
      "tool": "COPY_A_DISCOVERED_READ_TOOL",
      "arguments": {},
      "record_path": ["messages"],
      "required_fields": ["id"],
      "minimum_records": 1
    }
  ]
}
```

Run from an installed environment, supplying your workspace credential privately:

```sh
read -rsp 'Workspace token: ' OPENDUET_TOKEN
export OPENDUET_TOKEN
openduet-check-connectors --live --plan ./private-service-plan.json \
  --url http://127.0.0.1:8765 --output .runtime/connector-live-acceptance.json
unset OPENDUET_TOKEN
```

HTTPS is required outside loopback. Omitting `--live` exits before reading the
plan or contacting an account. The result is a private file containing pass/fail,
counts, checked field names, timestamp and tool-schema digest. Provider record
bodies, error bodies, credentials and argument values are not written to it.

Automated tests exercise this runner against a real loopback HTTP MCP server and
synthetic Gmail records, including missing fields, non-read tools, disconnect
and explicit opt-in. They do **not** certify a live Google, Stripe or Docusign
account. The 17-service schema-derived fixtures in `tests/fixtures/service_contracts.json`
and `test_launch_contracts.py` exercise actual HTTP/stdio discovery/read/write,
source capture, event ingestion/deduplication and exact one-use review. Tool
names are illustrative fixture names; records are synthetic, not captured
private-account sessions. See [service setup](LAUNCH-CONNECTORS.md).
