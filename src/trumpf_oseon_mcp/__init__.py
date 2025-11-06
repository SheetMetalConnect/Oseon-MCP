"""
TRUMPF Oseon MCP Server

A Model Context Protocol (MCP) server that connects to TRUMPF Oseon's public API v2
for customer order management. This demonstration shows how to integrate MCP clients
(like Claude Desktop) with on-premise TRUMPF Oseon systems.

🤖 Vibecoded with Cursor & Claude 4 Sonnet Max
🏭 Tech Demo - TRUMPF Oseon is a trademark of TRUMPF Co. KG | No affiliation - Educational demonstration only
"""

__version__ = "2.0.0"
__author__ = "Luke van Enkhuizen"
__email__ = "luke@sheetmetalconnect.com"
__url__ = "https://github.com/sheetmetalconnect/trumpf-oseon-mcp"

from .api.client import OseonAPIClient
from .config import get_config
from .__main__ import mcp

# Initialize configuration
OSEON_CONFIG = get_config()

__all__ = ["OSEON_CONFIG", "get_config", "OseonAPIClient", "mcp"] 

# Export exceptions for easier access
from .exceptions import (
    OseonError,
    OseonAPIError,
    OseonConnectionError,
    OseonAuthenticationError,
    OseonNotFoundError,
    OseonRateLimitError,
    OseonServerError,
    OseonValidationError,
    OseonConfigurationError,
)

__all__.extend([
    'OseonError',
    'OseonAPIError',
    'OseonConnectionError',
    'OseonAuthenticationError',
    'OseonNotFoundError',
    'OseonRateLimitError',
    'OseonServerError',
    'OseonValidationError',
    'OseonConfigurationError',
])
