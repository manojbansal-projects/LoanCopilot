"""
Loan Copilot MCP Client.

Provides two integration modes:

1. **Subprocess client (stdio)** — spawns the MCP server as a child process and
   communicates over stdin/stdout.  Use this for external integrations, Claude
   Desktop, or cross-process scenarios.

2. **In-process helper** — calls the FastMCP server instance directly for the
   LangChain agent (`USE_MCP=true`).  No subprocess overhead; shares the same
   Python process.

Usage example (subprocess mode):
    async with LoanMCPClient() as client:
        tools = await client.list_tools()
        result = await client.call_tool("calculate_emi", {
            "principal": 3000000,
            "annual_rate_percent": 9.0,
            "tenure_months": 240,
        })
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# ── Subprocess (stdio) client ─────────────────────────────────────────────────

class LoanMCPClient:
    """
    Async context manager that connects to the MCP server via stdio subprocess.

    Attributes:
        _session: mcp.ClientSession — set on __aenter__, cleared on __aexit__
        _exit_stack: async context stack managing the transport

    Example:
        async with LoanMCPClient() as client:
            tools = await client.list_tools()
            result = await client.call_tool("calculate_emi", {...})
    """

    def __init__(self, server_script: str | None = None) -> None:
        """
        Args:
            server_script: Absolute path to the server entry-point.
                Defaults to `scripts/start_mcp_server.py` inside the project root.
        """
        if server_script is None:
            project_root = Path(__file__).resolve().parent.parent
            server_script = str(project_root / "scripts" / "start_mcp_server.py")
        self._server_script = server_script
        self._session = None
        self._exit_stack = None

    async def __aenter__(self) -> "LoanMCPClient":
        from contextlib import AsyncExitStack
        from mcp.client.stdio import StdioServerParameters, stdio_client
        from mcp.client.session import ClientSession

        params = StdioServerParameters(
            command=sys.executable,
            args=[self._server_script, "--transport", "stdio"],
            env={**os.environ, "PYTHONPATH": str(Path(self._server_script).parent.parent)},
        )

        self._exit_stack = AsyncExitStack()
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(params)
        )
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()
        self._session = session
        return self

    async def __aexit__(self, *args) -> None:
        if self._exit_stack:
            await self._exit_stack.aclose()
        self._session = None
        self._exit_stack = None

    async def list_tools(self) -> list[dict]:
        """
        Return tool descriptors (name, description, input_schema) from the server.
        """
        if self._session is None:
            raise RuntimeError("Client not connected — use 'async with LoanMCPClient()'")
        response = await self._session.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description or "",
                "input_schema": t.inputSchema,
            }
            for t in response.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """
        Call a tool by name and return the parsed result (dict or str).

        The MCP server serialises tool return values as JSON text; this method
        parses that back to a Python object.
        """
        if self._session is None:
            raise RuntimeError("Client not connected — use 'async with LoanMCPClient()'")
        response = await self._session.call_tool(name, arguments)
        content = response.content
        if not content:
            return None
        text = content[0].text if hasattr(content[0], "text") else str(content[0])
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text


# ── In-process helpers (no subprocess overhead) ───────────────────────────────

async def call_tool_async(name: str, arguments: dict[str, Any]) -> Any:
    """
    Call a tool on the in-process FastMCP server instance.

    Returns the parsed Python result (dict or str).  This is the fast path
    used by the LangChain agent when USE_MCP=true — it avoids subprocess
    overhead by calling the FastMCP server directly in the same process.
    """
    from loan_mcp.server import mcp

    contents = await mcp.call_tool(name, arguments)
    if not contents:
        return None
    text = contents[0].text if hasattr(contents[0], "text") else str(contents[0])
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def call_tool_sync(name: str, arguments: dict[str, Any]) -> Any:
    """
    Synchronous wrapper for ``call_tool_async``.

    Runs the coroutine in a background thread to avoid event-loop conflicts
    when called from synchronous LangChain tool functions that may be executing
    inside an already-running event loop (e.g., Streamlit async context).
    """
    async def _run():
        return await call_tool_async(name, arguments)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, _run()).result()


def list_tools_sync() -> list[dict]:
    """
    Return the list of tool descriptors from the in-process MCP server.
    """
    from loan_mcp.server import mcp
    tools = mcp._tool_manager.list_tools()
    return [
        {
            "name": t.name,
            "description": t.description or "",
            "parameters": t.parameters,
        }
        for t in tools
    ]
