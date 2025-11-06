"""TRUMPF Oseon API v2 MCP Server

Modular MCP server for TRUMPF Oseon customer order and production management.
Educational demonstration - TRUMPF Oseon is a trademark of TRUMPF Co. KG

This refactored version follows best practices with a modular architecture:
- Separate API client for all Oseon communication
- Distinct modules for models, utilities, and tools
- Read-only operations with comprehensive pagination support
- Dashboard features as secondary/demo capabilities
"""

__version__ = "2.0.0"
__author__ = "Luke van Enkhuizen (Sheet Metal Connect e.U.)"
__license__ = "MIT"

import logging
from typing import Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .api.client import OseonAPIClient
from .config import get_config
from .tools import customer_orders, dashboards, production_orders

# Load environment variables from .env file if it exists
# This allows users to configure API credentials without modifying code
load_dotenv()

# Configure logging to stderr (required for MCP servers)
# MCP clients like Claude Desktop read logs from stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Ensure stderr logging
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server with a unique identifier
# This name appears in MCP client configurations
mcp = FastMCP("trumpf-oseon")

# Load configuration from environment variables or defaults
# See config.py for available configuration options
OSEON_CONFIG = get_config()

# Initialize API client
api_client = OseonAPIClient(OSEON_CONFIG)

# Demo mode settings - set to True for demo videos to sanitize customer data
# Set to False for production use with real customer data
DEMO_MODE = False


# ================================================================================================
# CUSTOMER ORDER TOOLS (Primary Focus - Read-Only with Pagination)
# ================================================================================================


@mcp.tool()
async def get_customer_orders(
    size: int = 50,
    page: int = 1,
    status: Optional[str] = None,
    customer_no: Optional[str] = None,
    since_date: Optional[str] = None,
    search_term: Optional[str] = None,
    item_no: Optional[str] = None,
    auto_filter_recent: bool = True,
    auto_paginate: bool = True,
    include_all_data: bool = False,
    filter_quality: bool = True
) -> str:
    """Get customer orders with unified filtering and pagination.

    🔄 UNIFIED SYSTEM: Returns recent, relevant data by default (last 12 months).
    📊 QUALITY FILTERING: Automatically excludes template and test orders.
    🆕 CONSISTENT SORTING: Always sorted by modification date (newest first).

    This is the primary tool for fetching customer orders with comprehensive
    filtering and pagination support. Read-only operation.

    Args:
        size: Number of orders per page (default: 50, API max)
        page: Page number (1-based, default: 1)
        status: Filter by order status (e.g., 'COMPLETED', 'INVOICED', 'INCOMPLETE')
        customer_no: Filter by exact customer number
        since_date: Optional ISO 8601 date filter (overrides auto_filter_recent if provided)
        search_term: Search in order numbers and external references (supports wildcards with %)
        item_no: Filter orders containing this item number
        auto_filter_recent: If True, applies 12-month recent filter automatically (default: True)
        auto_paginate: If True, automatically fetches up to 200 records (default: True)
        include_all_data: If True, disables recent filtering to get all historical data (default: False)
        filter_quality: If True, filters out template/test orders (default: True)

    Returns:
        Formatted list of recent, quality customer orders with enhanced status interpretation
    """
    return await customer_orders.get_customer_orders(
        client=api_client,
        size=size,
        page=page,
        status=status,
        customer_no=customer_no,
        since_date=since_date,
        search_term=search_term,
        item_no=item_no,
        auto_filter_recent=auto_filter_recent,
        auto_paginate=auto_paginate,
        include_all_data=include_all_data,
        filter_quality=filter_quality,
        demo_mode=DEMO_MODE
    )


@mcp.tool()
async def get_customer_order_details(order_no: str) -> str:
    """Get detailed information for a specific customer order.

    Read-only operation to fetch comprehensive details about a single customer order.

    Args:
        order_no: Customer order number

    Returns:
        Formatted detailed customer order information including positions and totals
    """
    return await customer_orders.get_customer_order_details(
        client=api_client,
        order_no=order_no,
        demo_mode=DEMO_MODE
    )


@mcp.tool()
async def search_customer_orders(
    search_term: str,
    size: int = 50,
    page: int = 1,
    status: Optional[str] = None,
    since_date: Optional[str] = None,
    filter_quality: bool = True
) -> str:
    """Search customer orders by term (order numbers, external references, etc.).

    Read-only search operation with pagination support.

    Args:
        search_term: Search term (supports wildcards with %)
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        status: Optional status filter
        since_date: Optional date filter
        filter_quality: If True, filters out template/test orders (default: True)

    Returns:
        Formatted search results with pagination info
    """
    return await customer_orders.search_customer_orders(
        client=api_client,
        search_term=search_term,
        size=size,
        page=page,
        status=status,
        since_date=since_date,
        filter_quality=filter_quality,
        demo_mode=DEMO_MODE
    )


@mcp.tool()
async def get_customer_orders_by_status(
    status: str,
    size: int = 50,
    page: int = 1,
    customer_no: Optional[str] = None,
    since_date: Optional[str] = None,
    filter_quality: bool = True
) -> str:
    """Get customer orders filtered by status.

    Read-only operation to fetch orders with a specific status.

    Args:
        status: Order status (e.g., 'COMPLETED', 'INVOICED', 'INCOMPLETE')
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        customer_no: Optional customer number filter
        since_date: Optional date filter
        filter_quality: If True, filters out template/test orders (default: True)

    Returns:
        Formatted list of customer orders with specified status
    """
    return await customer_orders.get_customer_orders_by_status(
        client=api_client,
        status=status,
        size=size,
        page=page,
        customer_no=customer_no,
        since_date=since_date,
        filter_quality=filter_quality,
        demo_mode=DEMO_MODE
    )


@mcp.tool()
async def get_orders_for_customer(
    customer_no: str,
    size: int = 50,
    page: int = 1,
    status: Optional[str] = None,
    since_date: Optional[str] = None,
    filter_quality: bool = True
) -> str:
    """Get all orders for a specific customer.

    Read-only operation to fetch all orders belonging to a customer.

    Args:
        customer_no: Customer number
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        status: Optional status filter
        since_date: Optional date filter
        filter_quality: If True, filters out template/test orders (default: True)

    Returns:
        Formatted list of customer orders for the specified customer
    """
    return await customer_orders.get_orders_for_customer(
        client=api_client,
        customer_no=customer_no,
        size=size,
        page=page,
        status=status,
        since_date=since_date,
        filter_quality=filter_quality,
        demo_mode=DEMO_MODE
    )


# ================================================================================================
# PRODUCTION ORDER TOOLS (Primary Focus - Read-Only with Pagination)
# ================================================================================================


@mcp.tool()
async def get_production_orders(
    size: int = 50,
    page: int = 1,
    status: Optional[int] = None,
    search_term: Optional[str] = None,
    since_date: Optional[str] = None,
    auto_filter_recent: bool = True,
    include_all_data: bool = False,
    filter_quality: bool = True
) -> str:
    """Get production orders with filtering and pagination.

    🔄 UNIFIED SYSTEM: Returns recent, relevant data by default (last 12 months).
    📊 QUALITY FILTERING: Automatically excludes template and test orders.

    This is the primary tool for fetching production orders with comprehensive
    filtering and pagination support. Read-only operation.

    Args:
        size: Number of orders per page (default: 50, API max)
        page: Page number (1-based, default: 1)
        status: Optional status filter (integer code: 0=INVALID, 10=VALID, 20=PENDING, 30=RELEASED, 40=STARTED, 90=FINISHED, 95=COMPLETED)
        search_term: Search term for order numbers, items, etc.
        since_date: Optional ISO 8601 date filter
        auto_filter_recent: If True, applies 12-month recent filter (default: True)
        include_all_data: If True, disables recent filtering (default: False)
        filter_quality: If True, filters out template/test orders (default: True)

    Returns:
        Formatted list of production orders
    """
    return await production_orders.get_production_orders(
        client=api_client,
        size=size,
        page=page,
        status=status,
        search_term=search_term,
        since_date=since_date,
        auto_filter_recent=auto_filter_recent,
        include_all_data=include_all_data,
        filter_quality=filter_quality,
        demo_mode=DEMO_MODE
    )


@mcp.tool()
async def search_production_orders(
    search_term: str,
    size: int = 50,
    page: int = 1,
    status: Optional[int] = None,
    since_date: Optional[str] = None,
    filter_quality: bool = True
) -> str:
    """Search production orders by term.

    Read-only search operation with pagination support.

    Args:
        search_term: Search term (order numbers, item numbers, etc.)
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        status: Optional status filter
        since_date: Optional date filter
        filter_quality: If True, filters out template/test orders (default: True)

    Returns:
        Formatted search results
    """
    return await production_orders.search_production_orders(
        client=api_client,
        search_term=search_term,
        size=size,
        page=page,
        status=status,
        since_date=since_date,
        filter_quality=filter_quality,
        demo_mode=DEMO_MODE
    )


@mcp.tool()
async def get_in_progress_production_orders(
    size: int = 50,
    page: int = 1,
    filter_quality: bool = True
) -> str:
    """Get production orders that are currently in progress (status: STARTED/40).

    Read-only operation to fetch active production orders.

    Args:
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        filter_quality: If True, filters out template/test orders (default: True)

    Returns:
        Formatted list of in-progress production orders
    """
    return await production_orders.get_in_progress_production_orders(
        client=api_client,
        size=size,
        page=page,
        filter_quality=filter_quality,
        demo_mode=DEMO_MODE
    )


@mcp.tool()
async def get_released_production_orders(
    size: int = 50,
    page: int = 1,
    filter_quality: bool = True
) -> str:
    """Get production orders that have been released (status: RELEASED/30).

    Read-only operation to fetch released production orders.

    Args:
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        filter_quality: If True, filters out template/test orders (default: True)

    Returns:
        Formatted list of released production orders
    """
    return await production_orders.get_released_production_orders(
        client=api_client,
        size=size,
        page=page,
        filter_quality=filter_quality,
        demo_mode=DEMO_MODE
    )


@mcp.tool()
async def get_finished_production_orders(
    size: int = 50,
    page: int = 1,
    filter_quality: bool = True
) -> str:
    """Get production orders that are finished (status: FINISHED/90).

    Read-only operation to fetch finished production orders.

    Args:
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        filter_quality: If True, filters out template/test orders (default: True)

    Returns:
        Formatted list of finished production orders
    """
    return await production_orders.get_finished_production_orders(
        client=api_client,
        size=size,
        page=page,
        filter_quality=filter_quality,
        demo_mode=DEMO_MODE
    )


@mcp.tool()
async def get_overdue_production_orders(
    size: int = 50,
    page: int = 1,
    filter_quality: bool = True
) -> str:
    """Get production orders that are overdue.

    Read-only operation to identify overdue production orders.

    Args:
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        filter_quality: If True, filters out template/test orders (default: True)

    Returns:
        Formatted list of overdue production orders
    """
    return await production_orders.get_overdue_production_orders(
        client=api_client,
        size=size,
        page=page,
        filter_quality=filter_quality,
        demo_mode=DEMO_MODE
    )


# ================================================================================================
# DASHBOARD TOOLS (Secondary/Demo Feature)
# ================================================================================================


@mcp.tool()
async def get_production_summary(days_back: int = 7) -> str:
    """Get a quick production summary dashboard (DEMO FEATURE).

    This is a secondary/demo feature to demonstrate quick production analysis.
    For detailed data, use the specific production order tools with pagination.

    Args:
        days_back: Number of days to look back (default: 7)

    Returns:
        Formatted production summary dashboard with status breakdown
    """
    return await dashboards.get_production_summary(
        client=api_client,
        days_back=days_back,
        demo_mode=DEMO_MODE
    )


@mcp.tool()
async def get_orders_summary(days_back: int = 7) -> str:
    """Get a quick customer orders summary dashboard (DEMO FEATURE).

    This is a secondary/demo feature to demonstrate quick analysis of customer orders.
    For detailed data, use the specific customer order tools with pagination.

    Args:
        days_back: Number of days to look back (default: 7)

    Returns:
        Formatted customer orders summary dashboard with status breakdown
    """
    return await dashboards.get_orders_summary(
        client=api_client,
        days_back=days_back,
        demo_mode=DEMO_MODE
    )


# ================================================================================================
# SERVER ENTRY POINT
# ================================================================================================


def main():
    """Main entry point for the MCP server."""
    logger.info("Starting TRUMPF Oseon MCP Server v2.0 (Modular Architecture)")
    logger.info(f"API Base URL: {OSEON_CONFIG['base_url']}")
    logger.info("Server features: Read-only operations, Pagination support, Quality filtering")
    mcp.run(transport="stdio")  # Run over stdio for Claude Desktop


if __name__ == "__main__":
    main()


# ================================================================================================
# UTILITY TOOLS
# ================================================================================================


@mcp.tool()
async def health_check() -> str:
    """Check MCP server and Oseon API connectivity.

    Tests connection to the Oseon API and validates authentication.
    Useful for troubleshooting and monitoring.

    Returns:
        Health status message
    """
    try:
        is_healthy = await api_client.health_check()
        if is_healthy:
            return f"✅ Healthy\n\nMCP Server: Running\nOseon API: {OSEON_CONFIG['base_url']}\nAuthentication: Valid\nConnection: OK"
        else:
            return "❌ Unhealthy - Unknown error"

    except Exception as e:
        error_type = type(e).__name__
        return f"❌ Unhealthy\n\nError: {error_type}\nMessage: {str(e)}\n\nCheck your configuration and network connection."
