"""
Start the MCP server (Phase 5+).

Usage:
    python scripts/start_mcp_server.py [--port 8080]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from mcp.server import start_server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    print(f"Starting MCP server on port {args.port}…")
    start_server(port=args.port)


if __name__ == "__main__":
    main()
