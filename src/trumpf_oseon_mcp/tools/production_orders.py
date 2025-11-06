"""Production order tools for TRUMPF Oseon MCP Server.

This module provides MCP tools for fetching and searching production orders.
All operations are read-only with pagination support.
"""

from typing import Optional

from ..api.client import OseonAPIClient
from ..utils.filters import filter_quality_orders, is_order_overdue
from ..utils.formatters import format_production_order
from ..utils.pagination import get_standard_production_order_params, get_unified_api_params


async def get_production_orders(
    client: OseonAPIClient,
    size: int = 50,
    page: int = 1,
    status: Optional[int] = None,
    search_term: Optional[str] = None,
    since_date: Optional[str] = None,
    auto_filter_recent: bool = True,
    include_all_data: bool = False,
    filter_quality: bool = True,
    demo_mode: bool = False
) -> str:
    """Get production orders with filtering and pagination.

    🔄 UNIFIED SYSTEM: Returns recent, relevant data by default (last 12 months).
    📊 QUALITY FILTERING: Automatically excludes template and test orders.

    Args:
        client: OseonAPIClient instance
        size: Number of orders per page (default: 50, API max)
        page: Page number (1-based, default: 1)
        status: Optional status filter (integer code)
        search_term: Search term for order numbers, items, etc.
        since_date: Optional ISO 8601 date filter
        auto_filter_recent: If True, applies 12-month recent filter (default: True)
        include_all_data: If True, disables recent filtering (default: False)
        filter_quality: If True, filters out template/test orders (default: True)
        demo_mode: If True, sanitizes customer data for demos (default: False)

    Returns:
        Formatted list of production orders
    """
    # Use unified API parameters
    params = get_unified_api_params(
        size=size,
        page=page,
        auto_filter_recent=auto_filter_recent,
        since_date=since_date,
        include_all_data=include_all_data,
        search_term=search_term
    )

    # Add status if provided (production orders use integer status codes)
    if status is not None:
        params["status"] = status

    try:
        result = await client.get_production_orders(params)

        if not result.get("collection"):
            return "No production orders found matching the criteria."

        orders = result["collection"]

        # Apply quality filtering if enabled
        if filter_quality:
            orders = filter_quality_orders(orders)

        if not orders:
            return "No production orders found matching the criteria (after quality filtering)."

        # Build response
        total_records = result.get("records", 0)
        total_pages = result.get("pages", 0)

        filter_info = []
        if not include_all_data and auto_filter_recent:
            filter_info.append("Recent (12 months)")
        if since_date:
            filter_info.append(f"Since: {since_date}")
        if status is not None:
            filter_info.append(f"Status: {status}")
        if search_term:
            filter_info.append(f"Search: '{search_term}'")
        if filter_quality:
            filter_info.append("Quality filtered")

        filter_desc = " | ".join(filter_info) if filter_info else "No filters"

        response = f"🏭 PRODUCTION ORDERS ({filter_desc}):\n"
        response += f"📊 Page {page}/{total_pages}, {len(orders)} quality records of {total_records} total\n"
        response += "=" * 100 + "\n"

        for order in orders:
            response += format_production_order(order, show_details=True, demo_mode=demo_mode)
            response += "-" * 100 + "\n"

        # Add pagination guidance
        if total_pages > page:
            response += "\n" + "=" * 100 + "\n"
            response += f"📄 PAGINATION: More pages available\n"
            response += f"💡 NEXT: Use page={page + 1} to continue\n"

        return response

    except Exception as e:
        return f"Error retrieving production orders: {str(e)}"


async def get_production_orders_by_status(
    client: OseonAPIClient,
    status: int,
    size: int = 50,
    page: int = 1,
    since_date: Optional[str] = None,
    filter_quality: bool = True,
    demo_mode: bool = False
) -> str:
    """Get production orders filtered by status.

    Common status codes:
    - 0: INVALID
    - 10: VALID
    - 20: PENDING
    - 30: RELEASED
    - 40: STARTED
    - 90: FINISHED
    - 95: COMPLETED

    Args:
        client: OseonAPIClient instance
        status: Production order status code (integer)
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        since_date: Optional date filter
        filter_quality: If True, filters out template/test orders (default: True)
        demo_mode: If True, sanitizes customer data for demos (default: False)

    Returns:
        Formatted list of production orders with specified status
    """
    return await get_production_orders(
        client=client,
        size=size,
        page=page,
        status=status,
        since_date=since_date,
        filter_quality=filter_quality,
        demo_mode=demo_mode
    )


async def search_production_orders(
    client: OseonAPIClient,
    search_term: str,
    size: int = 50,
    page: int = 1,
    status: Optional[int] = None,
    since_date: Optional[str] = None,
    filter_quality: bool = True,
    demo_mode: bool = False
) -> str:
    """Search production orders by term.

    Args:
        client: OseonAPIClient instance
        search_term: Search term (order numbers, item numbers, etc.)
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        status: Optional status filter
        since_date: Optional date filter
        filter_quality: If True, filters out template/test orders (default: True)
        demo_mode: If True, sanitizes customer data for demos (default: False)

    Returns:
        Formatted search results
    """
    return await get_production_orders(
        client=client,
        size=size,
        page=page,
        status=status,
        search_term=search_term,
        since_date=since_date,
        filter_quality=filter_quality,
        demo_mode=demo_mode
    )


async def get_in_progress_production_orders(
    client: OseonAPIClient,
    size: int = 50,
    page: int = 1,
    filter_quality: bool = True,
    demo_mode: bool = False
) -> str:
    """Get production orders that are currently in progress (status: STARTED/40).

    Args:
        client: OseonAPIClient instance
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        filter_quality: If True, filters out template/test orders (default: True)
        demo_mode: If True, sanitizes customer data for demos (default: False)

    Returns:
        Formatted list of in-progress production orders
    """
    return await get_production_orders_by_status(
        client=client,
        status=40,  # STARTED
        size=size,
        page=page,
        filter_quality=filter_quality,
        demo_mode=demo_mode
    )


async def get_released_production_orders(
    client: OseonAPIClient,
    size: int = 50,
    page: int = 1,
    filter_quality: bool = True,
    demo_mode: bool = False
) -> str:
    """Get production orders that have been released (status: RELEASED/30).

    Args:
        client: OseonAPIClient instance
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        filter_quality: If True, filters out template/test orders (default: True)
        demo_mode: If True, sanitizes customer data for demos (default: False)

    Returns:
        Formatted list of released production orders
    """
    return await get_production_orders_by_status(
        client=client,
        status=30,  # RELEASED
        size=size,
        page=page,
        filter_quality=filter_quality,
        demo_mode=demo_mode
    )


async def get_finished_production_orders(
    client: OseonAPIClient,
    size: int = 50,
    page: int = 1,
    filter_quality: bool = True,
    demo_mode: bool = False
) -> str:
    """Get production orders that are finished (status: FINISHED/90).

    Args:
        client: OseonAPIClient instance
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        filter_quality: If True, filters out template/test orders (default: True)
        demo_mode: If True, sanitizes customer data for demos (default: False)

    Returns:
        Formatted list of finished production orders
    """
    return await get_production_orders_by_status(
        client=client,
        status=90,  # FINISHED
        size=size,
        page=page,
        filter_quality=filter_quality,
        demo_mode=demo_mode
    )


async def get_overdue_production_orders(
    client: OseonAPIClient,
    size: int = 50,
    page: int = 1,
    filter_quality: bool = True,
    demo_mode: bool = False
) -> str:
    """Get production orders that are overdue.

    Args:
        client: OseonAPIClient instance
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        filter_quality: If True, filters out template/test orders (default: True)
        demo_mode: If True, sanitizes customer data for demos (default: False)

    Returns:
        Formatted list of overdue production orders
    """
    # Get all active production orders (not completed)
    result = await get_production_orders(
        client=client,
        size=size,
        page=page,
        filter_quality=filter_quality,
        demo_mode=demo_mode
    )

    # Parse result and filter for overdue orders
    # This is a simplified approach - in production you might want to parse the formatted string
    # or modify get_production_orders to return structured data

    try:
        params = get_unified_api_params(size=size, page=page, auto_filter_recent=True)
        api_result = await client.get_production_orders(params)

        if not api_result.get("collection"):
            return "No overdue production orders found."

        orders = api_result["collection"]

        if filter_quality:
            orders = filter_quality_orders(orders)

        # Filter for overdue orders
        overdue_orders = [
            order for order in orders
            if is_order_overdue(order.get("dueDate", ""), order.get("status"))
        ]

        if not overdue_orders:
            return "No overdue production orders found."

        response = f"🏭 OVERDUE PRODUCTION ORDERS:\n"
        response += f"📊 Found {len(overdue_orders)} overdue orders\n"
        response += "=" * 100 + "\n"

        for order in overdue_orders:
            response += format_production_order(order, show_details=True, demo_mode=demo_mode)
            response += "-" * 100 + "\n"

        return response

    except Exception as e:
        return f"Error retrieving overdue production orders: {str(e)}"
