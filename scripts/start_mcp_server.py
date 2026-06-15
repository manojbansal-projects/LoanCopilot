"""
Start the Loan Copilot MCP server.

Usage:
    python scripts/start_mcp_server.py                      # stdio (for Claude Desktop)
    python scripts/start_mcp_server.py --transport http     # HTTP on port 8080
    python scripts/start_mcp_server.py --transport http --port 9000
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from loan_mcp.server import start_server


def main():
    parser = argparse.ArgumentParser(description="Loan Copilot MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport: 'stdio' for Claude Desktop (default), 'http' for network access",
    )
    parser.add_argument("--port", type=int, default=8080, help="Port for HTTP transport")
    args = parser.parse_args()

    if args.transport == "http":
        print(f"Starting Loan Copilot MCP server — HTTP on port {args.port} …")
    else:
        print("Starting Loan Copilot MCP server — stdio transport …", file=sys.stderr)

    start_server(transport=args.transport, port=args.port)


if __name__ == "__main__":
    main()
