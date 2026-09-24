"""`uv run python -m api.mcp`: el servidor MCP por stdio, para Claude Desktop, Claude Code o el
MCP Inspector. Lee los workspaces de `NOVELAS_DIR`, como la API."""

from api.mcp.servidor import servidor

servidor.run(show_banner=False)
