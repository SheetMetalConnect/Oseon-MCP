"""
TRUMPF Oseon MCP Server

A Model Context Protocol (MCP) server that connects to TRUMPF Oseon's public API v2
for customer order management. This demonstration shows how to integrate MCP clients
(like Claude Desktop) with on-premise TRUMPF Oseon systems.

🤖 Vibecoded with Cursor & Claude 4 Sonnet Max
🏭 Tech Demo - TRUMPF Oseon is a trademark of TRUMPF Co. KG | No affiliation - Educational demonstration only
"""

__version__ = "1.0.0"
__author__ = "Luke van Enkhuizen"
__email__ = "luke@sheetmetalconnect.com"
__url__ = "https://github.com/sheetmetalconnect/trumpf-oseon-mcp"

from .config import get_config
from .__main__ import mcp, make_oseon_request

# Initialize configuration
OSEON_CONFIG = get_config()

__all__ = ["OSEON_CONFIG", "get_config", "make_oseon_request", "mcp"] 