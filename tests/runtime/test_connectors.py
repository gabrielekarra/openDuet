import sys

from openduet import connectors
from openduet.config import ConnectorConfig


async def test_real_stdio_discovery_and_call_with_exclusions(tmp_path):
    server = tmp_path / "fixture.py"
    server.write_text("""from mcp.server.fastmcp import FastMCP
mcp = FastMCP("fixture")
@mcp.tool()
def echo(text: str) -> str:
    return "Verified: " + text
@mcp.tool()
def forbidden() -> str:
    return "never"
if __name__ == "__main__":
    mcp.run(transport="stdio")
""")
    config = ConnectorConfig(command=sys.executable, args=[str(server)], excluded_tools=["forbidden"])
    tools = await connectors.discover(config)
    assert [t.name for t in tools] == ["echo"]
    result = await connectors.call(config, "echo", {"text": "round trip"})
    assert result["content"][0]["text"] == "Verified: round trip"
