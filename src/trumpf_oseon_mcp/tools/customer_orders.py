"""Customer order tools for TRUMPF Oseon MCP Server.

This module provides MCP tools for fetching and searching customer orders.
All operations are read-only with pagination support.
"""

from typing import Optional

from mcp.server.fastmcp import Context

from ..api.client import OseonAPIClient
from ..utils.filters import filter_quality_orders
from ..utils.formatters import format_customer_order
from ..utils.pagination import get_unified_api_params


async def get_customer_orders(
    client: OseonAPIClient,
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
    filter_quality: bool = True,
    demo_mode: bool = False
) -> str:
    """Get customer orders with unified filtering and consistent behavior.

    🔄 UNIFIED SYSTEM: Always returns recent, relevant data by default (last 12 months).
    📊 QUALITY FILTERING: Automatically excludes template and test orders.
    🆕 CONSISTENT SORTING: Always sorted by modification date (newest first).

    Args:
        client: OseonAPIClient instance
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
        demo_mode: If True, sanitizes customer data for demos (default: False)

    Returns:
        Formatted list of recent, quality customer orders with enhanced status interpretation
    """
    # Auto-paginate up to 200 records (4 pages) if enabled
    all_orders = []
    max_auto_pages = 4 if auto_paginate and page == 1 else 1
    total_records = 0
    total_pages = 0

    for page_num in range(page, page + max_auto_pages):
        # Use unified API parameters with consistent defaults
        params = get_unified_api_params(
            size=size,
            page=page_num,
            auto_filter_recent=auto_filter_recent,
            since_date=since_date,
            status=status,
            search_term=search_term,
            customer_no=customer_no,
            item_no=item_no,
            include_all_data=include_all_data
        )

        try:
            result = await client.get_customer_orders(params)

            if not result.get("collection"):
                break  # No more data

            orders = result["collection"]

            # Apply quality filtering if enabled
            if filter_quality:
                orders = filter_quality_orders(orders)

            all_orders.extend(orders)

            # Store metadata from first successful request
            if page_num == page:
                total_records = result.get("records", 0)
                total_pages = result.get("pages", 0)

            # If we got less than requested size, we've reached the end
            if len(orders) < size:
                break

        except Exception as e:
            if page_num == page:  # First page error
                return f"Error retrieving customer orders: {str(e)}"
            break  # Subsequent page error, stop here

    if not all_orders:
        return "No customer orders found matching the criteria."

    # Build response with unified system info
    filter_info = []
    if not include_all_data and auto_filter_recent:
        filter_info.append("Recent (12 months)")
    if since_date and not auto_filter_recent:
        filter_info.append(f"Since: {since_date}")
    if status:
        filter_info.append(f"Status: {status}")
    if customer_no:
        filter_info.append(f"Customer: {customer_no}")
    if search_term:
        filter_info.append(f"Search: '{search_term}'")
    if item_no:
        filter_info.append(f"Item: {item_no}")
    if filter_quality:
        filter_info.append("Quality filtered")

    filter_desc = " | ".join(filter_info) if filter_info else "No filters"

    # Calculate display info
    pages_fetched = min(max_auto_pages, total_pages - page + 1) if auto_paginate else 1
    end_page = page + pages_fetched - 1

    if auto_paginate and pages_fetched > 1:
        response = f"🔄 CUSTOMER ORDERS (Unified System - {filter_desc}):\n"
        response += f"📊 Auto-paginated: Pages {page}-{end_page}, {len(all_orders)} quality records of {total_records} total\n"
    else:
        response = f"🔄 CUSTOMER ORDERS (Unified System - {filter_desc}):\n"
        response += f"📊 Page {page}, {len(all_orders)} quality records of {total_records} total\n"

    response += "=" * 100 + "\n"

    for order in all_orders:
        response += format_customer_order(order, show_positions=False, demo_mode=demo_mode)
        response += "-" * 100 + "\n"

    # Add pagination guidance
    if total_pages > end_page:
        response += "\n" + "=" * 100 + "\n"
        response += f"📄 PAGINATION: Showing {len(all_orders)} quality records from {pages_fetched} pages\n"
        response += f"💡 NEXT: Use page={end_page + 1} to continue\n"
        response += f"🗂️ ALL DATA: Use include_all_data=True to access historical data beyond 12 months\n"
    elif len(all_orders) >= 200:
        response += "\n" + "=" * 100 + "\n"
        response += f"📊 BULK DATA: Fetched {len(all_orders)} quality records\n"

    return response


async def get_customer_order_details(
    client: OseonAPIClient,
    order_no: str,
    demo_mode: bool = False
) -> str:
    """Get detailed information for a specific customer order.

    Args:
        client: OseonAPIClient instance
        order_no: Customer order number
        demo_mode: If True, sanitizes customer data for demos (default: False)

    Returns:
        Formatted detailed customer order information
    """
    try:
        result = await client.get_customer_order_details(order_no)

        if not result:
            return f"No customer order found with number: {order_no}"

        return format_customer_order(result, show_positions=True, demo_mode=demo_mode)

    except Exception as e:
        return f"Error retrieving customer order details: {str(e)}"


async def search_customer_orders(
    client: OseonAPIClient,
    search_term: str,
    size: int = 50,
    page: int = 1,
    status: Optional[str] = None,
    since_date: Optional[str] = None,
    filter_quality: bool = True,
    demo_mode: bool = False
) -> str:
    """Search customer orders by term (order numbers, external references, etc.).

    Args:
        client: OseonAPIClient instance
        search_term: Search term (supports wildcards with %)
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        status: Optional status filter
        since_date: Optional date filter
        filter_quality: If True, filters out template/test orders (default: True)
        demo_mode: If True, sanitizes customer data for demos (default: False)

    Returns:
        Formatted search results
    """
    return await get_customer_orders(
        client=client,
        size=size,
        page=page,
        status=status,
        search_term=search_term,
        since_date=since_date,
        filter_quality=filter_quality,
        auto_paginate=False,
        demo_mode=demo_mode
    )


async def get_customer_orders_by_status(
    client: OseonAPIClient,
    status: str,
    size: int = 50,
    page: int = 1,
    customer_no: Optional[str] = None,
    since_date: Optional[str] = None,
    filter_quality: bool = True,
    demo_mode: bool = False
) -> str:
    """Get customer orders filtered by status.

    Args:
        client: OseonAPIClient instance
        status: Order status (e.g., 'COMPLETED', 'INVOICED', 'INCOMPLETE')
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        customer_no: Optional customer number filter
        since_date: Optional date filter
        filter_quality: If True, filters out template/test orders (default: True)
        demo_mode: If True, sanitizes customer data for demos (default: False)

    Returns:
        Formatted list of customer orders with specified status
    """
    return await get_customer_orders(
        client=client,
        size=size,
        page=page,
        status=status,
        customer_no=customer_no,
        since_date=since_date,
        filter_quality=filter_quality,
        auto_paginate=True,
        demo_mode=demo_mode
    )


async def get_orders_for_customer(
    client: OseonAPIClient,
    customer_no: str,
    size: int = 50,
    page: int = 1,
    status: Optional[str] = None,
    since_date: Optional[str] = None,
    filter_quality: bool = True,
    demo_mode: bool = False
) -> str:
    """Get all orders for a specific customer.

    Args:
        client: OseonAPIClient instance
        customer_no: Customer number
        size: Number of orders per page (default: 50)
        page: Page number (1-based, default: 1)
        status: Optional status filter
        since_date: Optional date filter
        filter_quality: If True, filters out template/test orders (default: True)
        demo_mode: If True, sanitizes customer data for demos (default: False)

    Returns:
        Formatted list of customer orders for the specified customer
    """
    return await get_customer_orders(
        client=client,
        size=size,
        page=page,
        customer_no=customer_no,
        status=status,
        since_date=since_date,
        filter_quality=filter_quality,
        auto_paginate=True,
        demo_mode=demo_mode
    )
