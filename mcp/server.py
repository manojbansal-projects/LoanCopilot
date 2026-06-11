"""
MCP (Model Context Protocol) server — exposes loan tools as MCP resources.
Allows external Claude Desktop / Claude Code clients to call agent tools directly.
"""
from __future__ import annotations
# TODO (Phase 5+): implement MCP server using the `mcp` SDK
# Reference: https://modelcontextprotocol.io/quickstart/server

def start_server(port: int = 8080) -> None:
    """Start the MCP server and block until interrupted."""
    raise NotImplementedError("MCP server not yet implemented (Phase 5+)")
