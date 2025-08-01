#!/usr/bin/env python3
"""
TRUMPF Oseon MCP Server - Entry Point

Entry point for running the TRUMPF Oseon MCP server.
This exposes the MCP server object for uv run mcp dev and Claude Desktop integration.
"""

from src.trumpf_oseon_mcp.__main__ import mcp, main

# Expose the server object for MCP CLI tools
server = mcp

if __name__ == "__main__":
    main()