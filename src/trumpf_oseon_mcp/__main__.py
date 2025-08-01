"""TRUMPF Oseon API v2 MCP Server

MCP server for TRUMPF Oseon customer order management.
Educational demonstration - TRUMPF Oseon is a trademark of TRUMPF Co. KG
"""

__version__ = "1.0.0"
__author__ = "Luke van Enkhuizen (Sheet Metal Connect e.U.)"
__license__ = "MIT"

import asyncio
import base64
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .config import get_config

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

# Demo mode settings - set to True for demo videos to sanitize customer data
# Set to False for production use with real customer data
DEMO_MODE = False

# ================================================================================================
# UNIFIED SYSTEM UTILITIES - CONSISTENT DATA FILTERING AND BEHAVIOR
# ================================================================================================

def get_default_since_date(months_back: int = 12) -> str:
    """
    Get dynamic default since_date for filtering recent records.
    Returns current time minus specified months (default: 12 months).
    
    Args:
        months_back: Number of months to go back from current date (default: 12)
        
    Returns:
        ISO formatted date string (e.g., "2024-01-01T00:00:00")
    """
    current_date = datetime.now()
    # Calculate months back by subtracting years and months
    year = current_date.year
    month = current_date.month - months_back
    
    # Handle year rollover
    while month <= 0:
        month += 12
        year -= 1
    
    # Create date at beginning of that month
    since_date = datetime(year, month, 1)
    return since_date.strftime("%Y-%m-%dT00:00:00")

def is_quality_production_data(order: Dict[str, Any]) -> bool:
    """
    Check if order represents real production data (not template/test).
    
    Args:
        order: Order dictionary from API
        
    Returns:
        bool: True if order is quality production data
    """
    # Filter out template orders with impossible future dates
    due_date_str = order.get("dueDate", "")
    if due_date_str:
        try:
            # Check for year 5000+ dates (template orders)
            if "5000" in due_date_str or any(year in due_date_str for year in ["5001", "5999", "9999"]):
                return False
            
            # Parse date and check if unreasonably far in future (>5 years)
            for date_format in ["%d.%m.%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    due_date = datetime.strptime(due_date_str, date_format)
                    years_ahead = (due_date - datetime.now()).days / 365
                    if years_ahead > 5:
                        return False
                    break
                except ValueError:
                    continue
        except (ValueError, TypeError):
            pass
    
    # Filter out test orders by order number and description patterns
    order_no = order.get("orderNo", "").lower()
    description = order.get("description", "").lower()
    
    test_patterns = ["test", "template", "demo", "example", "sandbox"]
    
    for pattern in test_patterns:
        if pattern in order_no or pattern in description:
            return False
    
    # Filter out orders with "None" customer names (often test data)
    customer_name = order.get("customerName", "")
    if customer_name in ["None", "", "N/A", "TEST", "TEMPLATE"]:
        return False
    
    return True

def get_unified_api_params(
    size: int = 50,
    page: int = 1,
    auto_filter_recent: bool = True,
    since_date: Optional[str] = None,
    status: Optional[str] = None,
    search_term: Optional[str] = None,
    customer_no: Optional[str] = None,
    item_no: Optional[str] = None,
    include_all_data: bool = False
) -> dict:
    """
    Get unified API parameters with consistent defaults across all commands.
    
    Args:
        size: Number of records per page (max 50)
        page: Page number (1-based, converted to 0-based)
        auto_filter_recent: If True, apply 12-month default filter (default: True)
        since_date: Optional specific date filter (overrides auto_filter_recent)
        status: Optional status filter
        search_term: Optional search term
        customer_no: Optional customer number filter
        item_no: Optional item number filter
        include_all_data: If True, disable recent filtering (default: False)
        
    Returns:
        Dictionary of unified API parameters
    """
    params = {
        "size": min(size, 50),
        "page": max(0, page - 1),  # Convert to 0-based
        "sortBy": "modificationDate",
        "sortOrder": "desc"  # Always newest first
    }
    
    # Apply recent data filtering by default
    if not include_all_data:
        if since_date:
            params["since"] = since_date
        elif auto_filter_recent:
            params["since"] = get_default_since_date()
    
    # Add optional filters
    if status:
        params["status"] = str(status).upper()
    if search_term:
        params["searchBy"] = search_term
    if customer_no:
        params["customerNo"] = customer_no
    if item_no:
        params["itemNo"] = item_no
        
    return params

def filter_quality_orders(orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter orders to include only quality production data.
    
    Args:
        orders: List of order dictionaries
        
    Returns:
        Filtered list containing only quality production orders
    """
    return [order for order in orders if is_quality_production_data(order)]

def sanitize_for_demo(data):
    """
    Sanitize customer data for demo purposes.
    Replaces real customer information with demo-safe values.
    """
    if not DEMO_MODE or not isinstance(data, dict):
        return data
    
    # Create a copy to avoid modifying original data
    sanitized = data.copy()
    
    # Replace customer information
    if 'customerName' in sanitized:
        sanitized['customerName'] = "Sheet Metal Connect"
    if 'customerNo' in sanitized:
        sanitized['customerNo'] = "C1"
    
    # Also sanitize nested positions if they exist
    if 'positions' in sanitized and isinstance(sanitized['positions'], list):
        sanitized['positions'] = [sanitize_for_demo(pos) for pos in sanitized['positions']]
    
    return sanitized

def get_auth_header() -> str:
    """Generate Basic Auth header for TRUMPF Oseon API."""
    credentials = f"{OSEON_CONFIG['username']}:{OSEON_CONFIG['password']}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded_credentials}"

async def make_oseon_request(endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Make an authenticated request to the TRUMPF Oseon API."""
    url = f"{OSEON_CONFIG['base_url']}{endpoint}"
    headers = OSEON_CONFIG['default_headers'].copy()
    headers["Authorization"] = get_auth_header()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"Making request to: {url}")
            if params:
                logger.info(f"Query parameters: {params}")
                
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Request successful. Records returned: {result.get('records', 'N/A')}")
            return result
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
        raise Exception(f"API request failed with status {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        raise Exception(f"Failed to connect to TRUMPF Oseon API: {str(e)}")


def calculate_recent_page_params(total_pages: int, total_records: int, page_size: int, target_records: int = 150) -> dict:
    """Calculate pagination parameters to get recent records from the end of the dataset.
    
    Args:
        total_pages: Total number of pages available
        total_records: Total number of records available  
        page_size: Number of records per page
        target_records: Target number of recent records to fetch (default: 150)
        
    Returns:
        dict with 'page' (0-based) and 'size' for API request
    """
    if total_pages <= 1:
        return {"page": 0, "size": min(page_size, 50)}
    
    # Calculate how many records we actually want (limited by what's available)
    records_to_fetch = min(target_records, total_records)
    
    # Calculate how many pages we need for those records
    pages_needed = max(1, (records_to_fetch + page_size - 1) // page_size)  # Ceiling division
    
    # Start from this many pages back from the end
    start_page = max(0, total_pages - pages_needed)
    
    return {"page": start_page, "size": min(page_size, 50)}


async def get_recent_customer_orders_params(base_params: dict, target_records: int = 150) -> dict:
    """Get pagination parameters for recent customer orders.
    
    Args:
        base_params: Base API parameters (filters, etc.)
        target_records: Number of recent records to target
        
    Returns:
        Updated parameters with proper pagination for recent records
    """
    try:
        # Get total pages/records with same page size as target request
        target_size = base_params.get("size", 25)
        initial_params = base_params.copy()
        initial_params.update({"size": target_size, "page": 0})
        
        result = await make_oseon_request("/api/v2/sales/customerOrders", initial_params)
        total_pages = result.get("pages", 1)
        total_records = result.get("records", 0)
        
        # Calculate proper pagination
        page_params = calculate_recent_page_params(total_pages, total_records, target_size, target_records)
        
        # Update base params with calculated pagination
        updated_params = base_params.copy()
        updated_params.update(page_params)
        
        return updated_params
        
    except Exception:
        # Fallback to first page if calculation fails
        fallback_params = base_params.copy()
        fallback_params.update({"page": 0, "size": min(base_params.get("size", 25), 50)})
        return fallback_params


async def get_recent_production_orders_params(base_params: dict, target_records: int = 150) -> dict:
    """Get pagination parameters for recent production orders.
    
    Args:
        base_params: Base API parameters (filters, etc.)
        target_records: Number of recent records to target
        
    Returns:
        Updated parameters with proper pagination for recent records
    """
    try:
        # Get total pages/records with same page size as target request
        target_size = base_params.get("size", 25)
        initial_params = base_params.copy()
        initial_params.update({"size": target_size, "page": 0})
        
        result = await make_oseon_request("/api/v2/pps/productionOrders/full/search", initial_params)
        total_pages = result.get("pages", 1)
        total_records = result.get("records", 0)
        
        # Calculate proper pagination
        page_params = calculate_recent_page_params(total_pages, total_records, target_size, target_records)
        
        # Update base params with calculated pagination
        updated_params = base_params.copy()
        updated_params.update(page_params)
        
        return updated_params
        
    except Exception:
        # Fallback to first page if calculation fails
        fallback_params = base_params.copy()
        fallback_params.update({"page": 0, "size": min(base_params.get("size", 25), 50)})
        return fallback_params


def get_standard_customer_order_params(size: int, page: int, status: Optional[str] = None, 
                                      customer_no: Optional[str] = None, since_date: Optional[str] = None,
                                      search_term: Optional[str] = None, item_no: Optional[str] = None) -> dict:
    """Get standard parameters for customer order API calls with consistent sorting.
    
    Args:
        size: Number of records per page
        page: Page number (1-based, will be converted to 0-based)
        status: Optional status filter
        customer_no: Optional customer number filter
        since_date: Optional date filter
        search_term: Optional search term
        item_no: Optional item number filter
        
    Returns:
        Dictionary of API parameters
    """
    params = {
        "size": min(size, 50),
        "page": max(0, page - 1),  # Convert to 0-based
        "sortBy": "modificationDate",
        "sortOrder": "desc"  # Always newest first
    }
    
    if status:
        params["status"] = status.upper()
    if customer_no:
        params["customerNo"] = customer_no
    if since_date:
        params["since"] = since_date
    if search_term:
        params["searchBy"] = search_term
    if item_no:
        params["itemNo"] = item_no
        
    return params


def get_standard_production_order_params(size: int, page: int, status: Optional[int] = None,
                                        search_term: Optional[str] = None, since_date: Optional[str] = None) -> dict:
    """Get standard parameters for production order API calls.
    
    Args:
        size: Number of records per page
        page: Page number (1-based, will be converted to 0-based)
        status: Optional status filter
        search_term: Optional search term
        since_date: Optional date filter
        
    Returns:
        Dictionary of API parameters
    """
    params = {
        "size": min(size, 50),
        "page": max(0, page - 1)  # Convert to 0-based
    }
    
    if status is not None:
        params["status"] = status
    if search_term:
        params["searchBy"] = search_term
    if since_date:
        params["since"] = since_date
        
    return params


def is_order_overdue(due_date_str: str, status: Any) -> bool:
    """Check if a production order is overdue.
    
    Args:
        due_date_str: Due date string in format "14.08.2017 16:00:00" or ISO format
        status: Order status
        
    Returns:
        bool: True if order is overdue and meaningful
    """
    # Don't consider completed/canceled orders as overdue
    if str(status) in ["95", "100", "COMPLETED", "CANCELED", "FINISHED", "DELIVERED", "INVOICED"]:
        return False
    
    try:
        # Try multiple date formats
        due_date = None
        
        # Try German format first ("14.08.2017 16:00:00")
        try:
            due_date = datetime.strptime(due_date_str, "%d.%m.%Y %H:%M:%S")
        except ValueError:
            # Try ISO format as fallback
            try:
                due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                # Convert to naive datetime for consistency
                if due_date.tzinfo is not None:
                    due_date = due_date.replace(tzinfo=None)
            except (ValueError, TypeError):
                return False
        
        if due_date is None:
            return False
            
        now = datetime.now()
        
        # Don't consider very old orders as meaningfully "overdue" (pre-2018)
        if due_date.year < 2018:
            return False
            
        # Only consider overdue if it's past due date and not too ancient
        days_overdue = (now - due_date).days
        return now > due_date and days_overdue < 730  # Max 2 years overdue to be meaningful
    except (ValueError, AttributeError, TypeError):
        return False


def get_order_status_category(status: str) -> str:
    """Categorize order status for business logic and user understanding.
    
    This function groups various TRUMPF Oseon order statuses into logical business
    categories that are easier for users to understand and filter by.
    
    Business Logic:
    - NEWEST: Orders in pre-production (validation, planning phase)
    - RELEASED: Orders actively being manufactured 
    - COMPLETED: Orders that have been delivered and/or invoiced
    - OTHER: Any status not matching the above categories
    
    Args:
        status: Raw order status from the API
        
    Returns:
        str: Business category ("NEWEST", "RELEASED", "COMPLETED", or "OTHER")
    """
    status = status.upper() if status else ""
    
    # Newest orders - likely in early stages (invalid/valid, not released yet)
    if status in ["INCOMPLETE", "VALID", "INVALID", "PENDING", "CREATED", "PLANNED"]:
        return "NEWEST"
    
    # Released for production - in manufacturing phase
    elif status in ["RELEASED", "SCHEDULED", "IN_PRODUCTION", "MANUFACTURING", "STARTED", "IN_MANUFACTURING", "ACTIVE"]:
        return "RELEASED"
    
    # Completed orders - delivered and invoiced
    elif status in ["COMPLETED", "DELIVERED", "INVOICED", "FINISHED", "CLOSED"]:
        return "COMPLETED"
    
    # Default category for unknown statuses
    else:
        return "OTHER"

def format_customer_order(order: Dict[str, Any], show_positions: bool = True) -> str:
    """Format a customer order for display with enhanced status interpretation.
    
    This function takes raw order data from the TRUMPF Oseon API and formats it
    into a human-readable string with business context and calculated values.
    
    Args:
        order: Raw order data from the API
        show_positions: Whether to include detailed position information and calculations
        
    Returns:
        str: Formatted order information ready for display to users
    """
    # Sanitize customer data for demo if needed
    sanitized_order = sanitize_for_demo(order)
    
    status = sanitized_order.get('status', 'N/A')
    status_category = get_order_status_category(status)
    
    # Add business context to status for better user understanding
    status_info = f"{status}"
    if status_category == "NEWEST":
        status_info += " (NEWEST - Pre-production)"
    elif status_category == "RELEASED":
        status_info += " (RELEASED - In production)"
    elif status_category == "COMPLETED":
        status_info += " (COMPLETED - Delivered/Invoiced)"
    
    # Calculate and format position information if requested
    positions_info = ""
    if show_positions and sanitized_order.get("positions"):
        total_positions = len(sanitized_order["positions"])
        # Calculate total order value by summing all position values
        total_value = sum(
            pos.get("netPricePerUnit", 0) * pos.get("targetQuantity", 0) 
            for pos in sanitized_order["positions"]
        )
        positions_info = f"\n  Positions: {total_positions} items, Total Value: €{total_value:.2f}"
        
        # Show first few positions as examples
        if total_positions > 0:
            positions_info += "\n  Sample Items:"
            for i, pos in enumerate(sanitized_order["positions"][:3]):
                positions_info += f"\n    - {pos.get('itemNo', 'N/A')} (Qty: {pos.get('targetQuantity', 0)}, €{pos.get('netPricePerUnit', 0):.2f}/unit)"
            if total_positions > 3:
                positions_info += f"\n    ... and {total_positions - 3} more items"
    
    return f"""
Order #{sanitized_order.get('customerOrderNo', 'N/A')}
  External Ref: {sanitized_order.get('customerOrderNoExt', 'N/A')}
  Customer: {sanitized_order.get('customerName', 'N/A')} ({sanitized_order.get('customerNo', 'N/A')})
  Status: {status_info}
  Order Date: {sanitized_order.get('orderDate', 'N/A')}{positions_info}
  Notes: {sanitized_order.get('note', 'None')}
"""

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
    """
    Get customer orders with unified filtering and consistent behavior.
    
    🔄 UNIFIED SYSTEM: Always returns recent, relevant data by default (last 12 months).
    📊 QUALITY FILTERING: Automatically excludes template and test orders.
    🆕 CONSISTENT SORTING: Always sorted by modification date (newest first).
    
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
            result = await make_oseon_request("/api/v2/sales/customerOrders", params)
            
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
        response += format_customer_order(order, show_positions=False)
        response += "-" * 100 + "\n"
        
    # Add pagination guidance
    if total_pages > end_page:
        response += "\n" + "=" * 100 + "\n"
        response += f"📄 PAGINATION: Showing {len(all_orders)} quality records from {pages_fetched} pages\n"
        response += f"💡 NEXT: Use page={end_page + 1} to continue\n"
        response += f"🔧 BULK: Use get_customer_orders_bulk() for 200+ records with array storage\n"
        response += f"🗂️ ALL DATA: Use include_all_data=True to access historical data beyond 12 months\n"
    elif len(all_orders) >= 200:
        response += "\n" + "=" * 100 + "\n"
        response += f"📊 BULK DATA: Fetched {len(all_orders)} quality records\n"
        response += f"🔧 BULK: Use get_customer_orders_bulk() for structured array storage of large datasets\n"
    
    return response

@mcp.tool()
async def browse_customer_orders_paginated(
    max_pages: int = 5,
    size: int = 25,
    status: Optional[str] = None,
    customer_no: Optional[str] = None,
    since_date: Optional[str] = None,
    search_term: Optional[str] = None,
    item_no: Optional[str] = None,
    sort_order: str = "desc"
) -> str:
    """
    Browse through multiple pages of customer orders with user-friendly pagination.
    This function fetches multiple pages automatically but warns about large datasets.
    
    Args:
        max_pages: Maximum number of pages to browse (default: 5, safety limit)
        size: Number of orders per page (default: 25, max: 50)
        status: Filter by order status
        customer_no: Filter by customer number
        since_date: Filter orders since this date
        search_term: Search term for order numbers/references
        item_no: Filter by item number
        sort_order: Sort order - "desc" for newest first, "asc" for oldest first
        
    Returns:
        Formatted results from multiple pages with pagination info
    """
    if max_pages > 10:
        return "⚠️  Maximum pages limited to 10 for performance reasons. Please refine your search criteria for larger datasets."
    
    all_orders = []
    total_found = 0
    pages_processed = 0
    
    try:
        for page_num in range(1, max_pages + 1):
            # Build parameters for this page
            params = {"size": min(size, 50), "page": page_num - 1}
            
            # Add sorting parameters
            if sort_order.lower() == "asc":
                params["sortBy"] = "modificationDate"
                params["sortOrder"] = "asc"
            else:
                params["sortBy"] = "modificationDate"
                params["sortOrder"] = "desc"
            
            # Add filters
            if status:
                params["status"] = status.upper()
            if customer_no:
                params["customerNo"] = customer_no
            if since_date:
                params["since"] = since_date
            if search_term:
                params["searchBy"] = search_term
            if item_no:
                params["itemNo"] = item_no
            
            result = await make_oseon_request("/api/v2/sales/customerOrders", params)
            
            if not result.get("collection"):
                break
                
            orders = result["collection"]
            total_records = result.get("records", 0)
            total_pages = result.get("pages", 0)
            
            all_orders.extend(orders)
            total_found = total_records
            pages_processed = page_num
            
            # If this is the last page or we've reached the end, break
            if page_num >= total_pages:
                break
        
        if not all_orders:
            return "No customer orders found matching the criteria."
        
        # Build comprehensive response
        filter_info = []
        if status:
            filter_info.append(f"Status: {status}")
        if customer_no:
            filter_info.append(f"Customer: {customer_no}")
        if since_date:
            filter_info.append(f"Since: {since_date}")
        if search_term:
            filter_info.append(f"Search: '{search_term}'")
        if item_no:
            filter_info.append(f"Item: {item_no}")
            
        filter_text = f" | Filters: {', '.join(filter_info)}" if filter_info else ""
        
        response = f"📊 MULTI-PAGE RESULTS: {len(all_orders)} orders from {pages_processed} pages (Total: {total_found}){filter_text}:\n"
        response += "=" * 80 + "\n"
        
        for order in all_orders:
            response += format_customer_order(order, show_positions=False)
            response += "-" * 80 + "\n"
            
        response += f"\n✅ Loaded {pages_processed} pages. Showing {len(all_orders)} of {total_found} total orders.\n"
        
        return response
        
    except Exception as e:
        return f"Error browsing paginated orders: {str(e)}"

@mcp.tool()
async def get_latest_orders_for_customer(
    customer_no: str,
    max_results: int = 50,
    days_back: int = 90
) -> str:
    """
    Get the latest orders for a specific customer efficiently.
    
    Args:
        customer_no: Customer number to filter by
        max_results: Maximum number of orders to return (default: 25)
        days_back: Number of days to look back (default: 90)
        
    Returns:
        Latest orders for the specified customer
    """
    # Calculate date threshold
    since_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%S")
    
    params = {
        "customerNo": customer_no,
        "since": since_date,
        "size": min(max_results, 50),
        "page": 0,
        "sortBy": "modificationDate",
        "sortOrder": "desc"
    }
    
    try:
        result = await make_oseon_request("/api/v2/sales/customerOrders", params)
        
        if not result.get("collection"):
            return f"No orders found for customer {customer_no} in the last {days_back} days."
            
        orders = result["collection"]
        total_found = result.get("records", 0)
        
        response = f"🏢 LATEST ORDERS FOR CUSTOMER {customer_no} (Last {days_back} days):\n"
        response += f"Found {len(orders)} of {total_found} total orders\n"
        response += "=" * 80 + "\n"
        
        for order in orders:
            response += format_customer_order(order, show_positions=False)
            response += "-" * 80 + "\n"
            
        return response
        
    except Exception as e:
        return f"Error retrieving latest orders for customer {customer_no}: {str(e)}"

@mcp.tool()
async def check_customer_order_overdue(
    customer_no: str,
    days_overdue: int = 7,
    max_results: int = 50
) -> str:
    """
    Check for overdue orders for a specific customer.
    This is efficient because it uses the customerNo API filter.
    
    Args:
        customer_no: Customer number to check (required for efficiency)
        days_overdue: Number of days past due date to consider (default: 7)
        max_results: Maximum number of orders to return (default: 50, API max)
        
    Returns:
        Overdue orders for the specified customer
    """
    params = {
        "customerNo": customer_no,
        "size": min(max_results, 50),
        "page": 0,
        "sortBy": "modificationDate",
        "sortOrder": "desc"
    }
    
    try:
        result = await make_oseon_request("/api/v2/sales/customerOrders", params)
        
        if not result.get("collection"):
            return f"No orders found for customer {customer_no}."
            
        orders = result["collection"]
        overdue_orders = []
        
        for order in orders:
            delivery_date = order.get('deliveryDate')
            status = order.get('status', '')
            
            if delivery_date and status not in ['COMPLETED', 'INVOICED', 'DELIVERED', 'FINISHED', 'CLOSED']:
                try:
                    delivery_dt = None
                    
                    # Try ISO format first
                    try:
                        delivery_dt = datetime.fromisoformat(delivery_date.replace('Z', '+00:00'))
                        if delivery_dt.tzinfo is not None:
                            delivery_dt = delivery_dt.replace(tzinfo=None)
                    except ValueError:
                        try:
                            delivery_dt = datetime.strptime(delivery_date, "%d.%m.%Y %H:%M:%S")
                        except ValueError:
                            continue
                    
                    if delivery_dt is None:
                        continue
                        
                    now = datetime.now()
                    if delivery_dt < now:
                        days_past_due = (now - delivery_dt).days
                        if days_past_due >= days_overdue:
                            order['days_past_due'] = days_past_due
                            overdue_orders.append(order)
                except (ValueError, TypeError):
                    continue
                    
        if not overdue_orders:
            return f"✅ No overdue orders found for customer {customer_no}."
            
        response = f"⚠️  OVERDUE ORDERS for Customer {customer_no} (Past due by {days_overdue}+ days):\n"
        response += f"Found {len(overdue_orders)} overdue orders\n"
        response += "=" * 80 + "\n"
        
        for order in overdue_orders:
            response += format_customer_order(order, show_positions=False)
            delivery_date = order.get('deliveryDate', 'N/A')
            days_past_due = order.get('days_past_due', 'N/A')
            response += f"   🔴 OVERDUE: Delivery planned for {delivery_date} ({days_past_due} days overdue)\n"
            response += "-" * 80 + "\n"
            
        return response
        
    except Exception as e:
        return f"Error checking overdue orders for customer {customer_no}: {str(e)}"

@mcp.tool()
async def get_orders_with_advanced_filter(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status_list: Optional[str] = None,
    customer_no: Optional[str] = None,
    max_results: int = 50,
    include_pagination: bool = True
) -> str:
    """
    Advanced filtering for customer orders with date ranges and multiple status filters.
    
    Args:
        date_from: Start date for filtering (ISO format: 2024-01-01T00:00:00)
        date_to: End date for filtering (ISO format: 2024-12-31T23:59:59)
        status_list: Comma-separated list of statuses (e.g., "RELEASED,IN_PRODUCTION,COMPLETED")
        customer_no: Specific customer number
        max_results: Maximum results to return (default: 50)
        include_pagination: Whether to show pagination info (default: true)
        
    Returns:
        Filtered customer orders with comprehensive information
    """
    params = {
        "size": min(max_results, 50),
        "page": 0,
        "sortBy": "modificationDate",
        "sortOrder": "desc"
    }
    
    if date_from:
        params["since"] = date_from
    if customer_no:
        params["customerNo"] = customer_no
        
    try:
        result = await make_oseon_request("/api/v2/sales/customerOrders", params)
        
        if not result.get("collection"):
            return "No orders found matching the advanced filter criteria."
            
        orders = result["collection"]
        filtered_orders = []
        
        # Apply additional filtering for date_to and status_list
        for order in orders:
            # Filter by end date if specified
            if date_to:
                order_date = order.get('modificationDate') or order.get('orderDate')
                if order_date:
                    try:
                        order_dt = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                        to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                        if order_dt > to_dt:
                            continue
                    except (ValueError, TypeError):
                        pass
            
            # Filter by status list if specified
            if status_list:
                allowed_statuses = [s.strip().upper() for s in status_list.split(',')]
                order_status = order.get('status', '').upper()
                if order_status not in allowed_statuses:
                    continue
                    
            filtered_orders.append(order)
        
        if not filtered_orders:
            return "No orders found matching all the specified criteria."
            
        # Build filter description
        filter_parts = []
        if date_from:
            filter_parts.append(f"From: {date_from}")
        if date_to:
            filter_parts.append(f"To: {date_to}")
        if status_list:
            filter_parts.append(f"Status: {status_list}")
        if customer_no:
            filter_parts.append(f"Customer: {customer_no}")
            
        filter_desc = " | ".join(filter_parts) if filter_parts else "No filters"
        
        response = f"🔍 ADVANCED FILTER RESULTS ({filter_desc}):\n"
        response += f"Found {len(filtered_orders)} matching orders\n"
        response += "=" * 80 + "\n"
        
        for order in filtered_orders:
            response += format_customer_order(order, show_positions=False)
            response += "-" * 80 + "\n"
            
        if include_pagination and len(orders) >= max_results:
            response += f"\n💡 Results limited to {max_results}. Use browse_customer_orders_paginated for more results.\n"
            
        return response
        
    except Exception as e:
        return f"Error with advanced filtering: {str(e)}"

@mcp.tool()
async def get_customer_order_details(customer_order_no: str) -> str:
    """
    Get detailed information about a specific customer order.
    
    Args:
        customer_order_no: The customer order number to retrieve
        
    Returns:
        Detailed customer order information including all positions
    """
    try:
        result = await make_oseon_request(f"/api/v2/sales/customerOrders/{customer_order_no}")
        
        if not result:
            return f"No customer order found with number: {customer_order_no}"
            
        # Detailed formatting
        order = sanitize_for_demo(result)
        response = f"DETAILED ORDER INFORMATION\n"
        response += "=" * 80 + "\n"
        response += f"Order Number: {order.get('customerOrderNo', 'N/A')}\n"
        response += f"External Reference: {order.get('customerOrderNoExt', 'N/A')}\n"
        response += f"Customer: {order.get('customerName', 'N/A')} (#{order.get('customerNo', 'N/A')})\n"
        response += f"Status: {order.get('status', 'N/A')}\n"
        response += f"Order Date: {order.get('orderDate', 'N/A')}\n"
        response += f"Notes: {order.get('note', 'None')}\n"
        response += f"Additional Notes: {order.get('note2', 'None')}\n"
        
        if order.get("positions"):
            response += f"\nORDER POSITIONS ({len(order['positions'])} items):\n"
            response += "-" * 80 + "\n"
            
            total_order_value = 0
            for pos in order["positions"]:
                line_total = pos.get("netPricePerUnit", 0) * pos.get("targetQuantity", 0)
                total_order_value += line_total
                
                response += f"Position {pos.get('positionNo', 'N/A')}: {pos.get('itemNo', 'N/A')}\n"
                response += f"  External Ref: {pos.get('positionNoExt', 'N/A')}\n"
                response += f"  Status: {pos.get('status', 'N/A')}\n"
                response += f"  Quantity - Target: {pos.get('targetQuantity', 0)}, Actual: {pos.get('actualQuantity', 0)}, Delivered: {pos.get('deliveredQuantity', 0)}\n"
                response += f"  Price: €{pos.get('netPricePerUnit', 0):.2f} per unit\n"
                response += f"  Line Total: €{line_total:.2f}\n"
                response += f"  Tax: {pos.get('taxRate', 0)}% ({pos.get('taxKey', 'N/A')})\n"
                response += f"  Discount: {pos.get('discount', 0)}%\n"
                response += f"  Currency: {pos.get('currency', 'N/A')}\n"
                response += f"  Delivery Date: {pos.get('deliveryDate', 'N/A')}\n"
                if pos.get('note'):
                    response += f"  Notes: {pos.get('note')}\n"
                response += "-" * 40 + "\n"
                
            response += f"\nTOTAL ORDER VALUE: €{total_order_value:.2f}\n"
        
        return response
        
    except Exception as e:
        return f"Error retrieving customer order details: {str(e)}"

@mcp.tool()
async def get_in_progress_production_orders(
    max_results: int = 50,
    since_days: Optional[int] = None,
    search_term: Optional[str] = None
) -> str:
    """
    Get production orders with IN_PROGRESS status (API status = 60).
    These orders are currently being manufactured.
    
    Args:
        max_results: Maximum number of results to return (default: 50, API max)
        since_days: Optional filter for orders from last N days
        search_term: Optional search term for OrderNo, OrderNoExt, Description
        
    Returns:
        Formatted list of in-progress production orders
    """
    params = {
        "status": "IN_PROGRESS",  # API status value
        "size": min(max_results, 50),
        "page": 0
    }
    
    if since_days:
        since_date = datetime.now() - timedelta(days=since_days)
        params["since"] = since_date.strftime("%Y-%m-%dT%H:%M:%S")
        
    if search_term:
        params["searchBy"] = search_term
    
    try:
        result = await make_oseon_request("/api/v2/pps/productionOrders/full/search", params)
        
        if not result.get("collection"):
            return "No in-progress production orders found with the specified criteria."
            
        orders = result["collection"]
        total_records = result.get("records", len(orders))
        
        since_text = f" (last {since_days} days)" if since_days else ""
        search_text = f" matching '{search_term}'" if search_term else ""
        
        response = f"IN-PROGRESS PRODUCTION ORDERS{since_text}{search_text} - {len(orders)} of {total_records} orders:\n"
        response += "=" * 100 + "\n"
        
        for order in orders[:max_results]:
            response += format_production_order(order, show_operations=True)
            response += "-" * 100 + "\n"
            
        # Add pagination guidance
        if len(orders) >= 50 and total_records > len(orders):
            response += f"\n📄 PAGINATION: Showing {len(orders)} of {total_records} total records\n"
            response += f"💡 MORE: Use get_production_orders() with status=IN_PROGRESS for auto-pagination up to 200 records\n"
            response += f"📊 BULK: Use get_production_orders_bulk() for 200+ records with array storage\n"
        elif len(orders) > max_results:
            response += f"\n💡 Showing {max_results} of {len(orders)} orders. Use max_results={len(orders)} to see all.\n"
            
        return response
        
    except Exception as e:
        return f"Error retrieving in-progress production orders: {str(e)}"

@mcp.tool()
async def get_released_production_orders(
    max_results: int = 50,
    since_days: Optional[int] = None,
    search_term: Optional[str] = None
) -> str:
    """
    Get production orders with RELEASED status (API status = 30).
    These orders are released for production but not yet in progress.
    
    Args:
        max_results: Maximum number of results to return (default: 50, API max)
        since_days: Optional filter for orders from last N days
        search_term: Optional search term for OrderNo, OrderNoExt, Description
        
    Returns:
        Formatted list of released production orders
    """
    params = {
        "status": "RELEASED",  # API status value
        "size": min(max_results, 50),
        "page": 0
    }
    
    if since_days:
        since_date = datetime.now() - timedelta(days=since_days)
        params["since"] = since_date.strftime("%Y-%m-%dT%H:%M:%S")
        
    if search_term:
        params["searchBy"] = search_term
    
    try:
        result = await make_oseon_request("/api/v2/pps/productionOrders/full/search", params)
        
        if not result.get("collection"):
            return "No released production orders found with the specified criteria."
            
        orders = result["collection"]
        total_records = result.get("records", len(orders))
        
        since_text = f" (last {since_days} days)" if since_days else ""
        search_text = f" matching '{search_term}'" if search_term else ""
        
        response = f"RELEASED PRODUCTION ORDERS{since_text}{search_text} - {len(orders)} of {total_records} orders:\n"
        response += "=" * 100 + "\n"
        
        for order in orders[:max_results]:
            response += format_production_order(order, show_operations=True)
            response += "-" * 100 + "\n"
            
        # Add pagination guidance
        if len(orders) >= 50 and total_records > len(orders):
            response += f"\n📄 PAGINATION: Showing {len(orders)} of {total_records} total records\n"
            response += f"💡 MORE: Use get_production_orders() with status=RELEASED for auto-pagination up to 200 records\n"
            response += f"📊 BULK: Use get_production_orders_bulk() for 200+ records with array storage\n"
        elif len(orders) > max_results:
            response += f"\n💡 Showing {max_results} of {len(orders)} orders. Use max_results={len(orders)} to see all.\n"
            
        return response
        
    except Exception as e:
        return f"Error retrieving released production orders: {str(e)}"

@mcp.tool()
async def get_finished_production_orders(
    max_results: int = 50,
    since_days: Optional[int] = None,
    search_term: Optional[str] = None
) -> str:
    """
    Get production orders with FINISHED status (API status = 90).
    These orders have completed manufacturing.
    
    Args:
        max_results: Maximum number of results to return (default: 50, API max)
        since_days: Optional filter for orders from last N days
        search_term: Optional search term for OrderNo, OrderNoExt, Description
        
    Returns:
        Formatted list of finished production orders
    """
    params = {
        "status": "FINISHED",  # API status value
        "size": min(max_results, 50),
        "page": 0
    }
    
    if since_days:
        since_date = datetime.now() - timedelta(days=since_days)
        params["since"] = since_date.strftime("%Y-%m-%dT%H:%M:%S")
        
    if search_term:
        params["searchBy"] = search_term
    
    try:
        result = await make_oseon_request("/api/v2/pps/productionOrders/full/search", params)
        
        if not result.get("collection"):
            return "No finished production orders found with the specified criteria."
            
        orders = result["collection"]
        total_records = result.get("records", len(orders))
        
        since_text = f" (last {since_days} days)" if since_days else ""
        search_text = f" matching '{search_term}'" if search_term else ""
        
        response = f"FINISHED PRODUCTION ORDERS{since_text}{search_text} - {len(orders)} of {total_records} orders:\n"
        response += "=" * 100 + "\n"
        
        for order in orders[:max_results]:
            response += format_production_order(order, show_operations=True)
            response += "-" * 100 + "\n"
            
        # Add pagination guidance
        if len(orders) >= 50 and total_records > len(orders):
            response += f"\n📄 PAGINATION: Showing {len(orders)} of {total_records} total records\n"
            response += f"💡 MORE: Use get_production_orders() with status=FINISHED for auto-pagination up to 200 records\n"
            response += f"📊 BULK: Use get_production_orders_bulk() for 200+ records with array storage\n"
        elif len(orders) > max_results:
            response += f"\n💡 Showing {max_results} of {len(orders)} orders. Use max_results={len(orders)} to see all.\n"
            
        return response
        
    except Exception as e:
        return f"Error retrieving finished production orders: {str(e)}"

@mcp.tool()
async def search_orders_advanced(
    search_term: str, 
    max_results: int = 50,
    status_category: Optional[str] = None,
    customer_no: Optional[str] = None,
    since_date: Optional[str] = None
) -> str:
    """
    Advanced search for customer orders with multiple filter options.
    
    Args:
        search_term: Search keyword for order numbers and external references (case-insensitive)
        max_results: Maximum number of results to return (default: 25)
        status_category: Filter by business category: 'newest', 'released', 'completed', or 'other'
        customer_no: Filter by exact customer number
        since_date: Filter orders modified since this date (ISO format: 2024-01-01T00:00:00)
        
    Returns:
        Formatted search results with enhanced filtering
    """
    params = {
        "searchBy": search_term,
        "size": min(max_results, 50)
    }
    
    if customer_no:
        params["customerNo"] = customer_no
    if since_date:
        params["since"] = since_date
    
    try:
        result = await make_oseon_request("/api/v2/sales/customerOrders", params)
        
        if not result.get("collection"):
            return f"No customer orders found matching search term: '{search_term}'"
            
        orders = result["collection"]
        
        # Apply status category filter if specified
        if status_category:
            category_upper = status_category.upper()
            filtered_orders = []
            for order in orders:
                order_category = get_order_status_category(order.get('status', ''))
                if order_category == category_upper:
                    filtered_orders.append(order)
            orders = filtered_orders
        
        if not orders:
            category_text = f" in category '{status_category}'" if status_category else ""
            return f"No orders found matching '{search_term}'{category_text}"
        
        total_found = result.get("records", len(orders))
        
        # Build filter description
        filter_parts = [f"Search: '{search_term}'"]
        if status_category:
            filter_parts.append(f"Category: {status_category}")
        if customer_no:
            filter_parts.append(f"Customer: {customer_no}")
        if since_date:
            filter_parts.append(f"Since: {since_date}")
        
        filter_text = " | ".join(filter_parts)
        
        response = f"ADVANCED SEARCH RESULTS ({len(orders)} of {total_found} matches) | {filter_text}:\n"
        response += "=" * 80 + "\n"
        
        for order in orders:
            response += format_customer_order(order, show_positions=False)
            response += "-" * 80 + "\n"
            
        return response
        
    except Exception as e:
        return f"Error searching customer orders: {str(e)}"

@mcp.tool()
async def get_modified_orders(
    since_date: str, 
    max_results: int = 50,
    status_category: Optional[str] = None,
    customer_no: Optional[str] = None
) -> str:
    """
    Get customer orders that have been modified since a specific date.
    This helps distinguish between orders that have been recently modified vs newly created.
    
    Args:
        since_date: Show orders modified since this date (ISO format: 2024-01-01T00:00:00)
        max_results: Maximum number of results to return (default: 25)
        status_category: Filter by business category: 'newest', 'released', 'completed', or 'other'
        customer_no: Filter by exact customer number
        
    Returns:
        Formatted list of recently modified orders
    """
    params = {
        "since": since_date,
        "size": min(max_results, 50)
    }
    
    if customer_no:
        params["customerNo"] = customer_no
    
    try:
        result = await make_oseon_request("/api/v2/sales/customerOrders", params)
        
        if not result.get("collection"):
            return f"No customer orders found modified since {since_date}"
            
        orders = result["collection"]
        
        # Apply status category filter if specified
        if status_category:
            category_upper = status_category.upper()
            filtered_orders = []
            for order in orders:
                order_category = get_order_status_category(order.get('status', ''))
                if order_category == category_upper:
                    filtered_orders.append(order)
            orders = filtered_orders
        
        if not orders:
            category_text = f" in category '{status_category}'" if status_category else ""
            return f"No orders found modified since {since_date}{category_text}"
        
        total_found = result.get("records", len(orders))
        
        # Build filter description
        filter_parts = [f"Modified since: {since_date}"]
        if status_category:
            filter_parts.append(f"Category: {status_category}")
        if customer_no:
            filter_parts.append(f"Customer: {customer_no}")
        
        filter_text = " | ".join(filter_parts)
        
        response = f"MODIFIED ORDERS ({len(orders)} of {total_found} total) | {filter_text}:\n"
        response += "=" * 80 + "\n"
        
        for order in orders:
            response += format_customer_order(order, show_positions=False)
            response += "-" * 80 + "\n"
            
        return response
        
    except Exception as e:
        return f"Error retrieving modified orders: {str(e)}"

@mcp.tool()
async def get_recent_orders(days: int = 30, max_results: int = 25, filter_quality: bool = True) -> str:
    """
    Get customer orders from the last specified number of days - UNIFIED SYSTEM.
    
    🔄 UNIFIED SYSTEM: Uses dynamic date calculation and quality filtering.
    
    Args:
        days: Number of days back to search (default: 30)
        max_results: Maximum number of results to return (default: 25)
        filter_quality: If True, filters out template/test orders (default: True)
        
    Returns:
        Formatted list of recent, quality orders with enhanced status interpretation
    """
    # Calculate the date threshold dynamically
    since_date = datetime.now() - timedelta(days=days)
    since_iso = since_date.strftime("%Y-%m-%dT%H:%M:%S")
    
    # Use unified API parameters
    params = get_unified_api_params(
        size=max_results,
        page=1,
        auto_filter_recent=False,  # We're providing specific since_date
        since_date=since_iso,
        include_all_data=False
    )
    
    try:
        result = await make_oseon_request("/api/v2/sales/customerOrders", params)
        
        if not result.get("collection"):
            return f"No customer orders found in the last {days} days"
            
        orders = result["collection"]
        
        # Apply quality filtering if enabled
        if filter_quality:
            orders = filter_quality_orders(orders)
        
        total_found = result.get("records", 0)
        
        response = f"🔄 RECENT ORDERS (Unified System - Last {days} days):\n"
        response += f"📊 {len(orders)} quality records of {total_found} total\n"
        response += "=" * 100 + "\n"
        
        for order in orders:
            response += format_customer_order(order, show_positions=False)
            response += "-" * 100 + "\n"
            
        return response
        
    except Exception as e:
        return f"Error retrieving recent orders: {str(e)}"

@mcp.tool()
async def get_orders_by_item(
    item_no: str, 
    max_results: int = 50,
    status_category: Optional[str] = None,
    since_date: Optional[str] = None
) -> str:
    """
    Get customer orders that contain a specific item number with enhanced filtering.
    Orders are automatically sorted by newest first.
    
    Args:
        item_no: Item number to search for in order positions
        max_results: Maximum number of results to return (default: 25)
        status_category: Filter by business category: 'newest', 'released', 'completed', or 'other'
        since_date: Filter orders modified since this date (ISO format: 2024-01-01T00:00:00)
        
    Returns:
        Formatted list of orders containing the specified item with enhanced status interpretation
    """
    params = {
        "itemNo": item_no,
        "size": min(max_results, 50)
    }
    
    if since_date:
        params["since"] = since_date
    
    try:
        result = await make_oseon_request("/api/v2/sales/customerOrders", params)
        
        if not result.get("collection"):
            return f"No customer orders found containing item: {item_no}"
            
        orders = result["collection"]
        
        # Apply status category filter if specified
        if status_category:
            category_upper = status_category.upper()
            filtered_orders = []
            for order in orders:
                order_category = get_order_status_category(order.get('status', ''))
                if order_category == category_upper:
                    filtered_orders.append(order)
            orders = filtered_orders
        
        if not orders:
            category_text = f" in category '{status_category}'" if status_category else ""
            return f"No orders found containing item '{item_no}'{category_text}"
        
        total_found = result.get("records", len(orders))
        
        # Build filter description
        filter_parts = [f"Item: {item_no}"]
        if status_category:
            filter_parts.append(f"Category: {status_category}")
        if since_date:
            filter_parts.append(f"Since: {since_date}")
        
        filter_text = " | ".join(filter_parts)
        
        response = f"ORDERS CONTAINING ITEM ({len(orders)} of {total_found} total) | {filter_text}:\n"
        response += "=" * 80 + "\n"
        
        for order in orders:
            response += format_customer_order(order, show_positions=False)
            # Highlight the specific item in this order
            if order.get("positions"):
                matching_positions = [p for p in order["positions"] if item_no.lower() in p.get("itemNo", "").lower()]
                if matching_positions:
                    response += "  Matching positions:\n"
                    for pos in matching_positions:
                        response += f"    • {pos.get('itemNo', 'N/A')} (Qty: {pos.get('targetQuantity', 0)}, €{pos.get('netPricePerUnit', 0):.2f}/unit)\n"
            response += "-" * 80 + "\n"
            
        return response
        
    except Exception as e:
        return f"Error retrieving orders by item: {str(e)}"

# ================================================================================================
# PRODUCTION ORDERS API FUNCTIONS
# ================================================================================================

@mcp.tool()
async def get_production_orders(
    size: int = 50,
    page: int = 1,
    status: Optional[int] = None,
    search_term: Optional[str] = None,
    since_date: Optional[str] = None,
    auto_filter_recent: bool = True,
    auto_paginate: bool = True,
    include_all_data: bool = False,
    filter_quality: bool = True
) -> str:
    """
    Get production orders with unified filtering and consistent behavior.
    
    🔄 UNIFIED SYSTEM: Always returns recent, relevant data by default (last 12 months).
    📊 QUALITY FILTERING: Automatically excludes template and test orders.
    🆕 CONSISTENT SORTING: Always sorted by modification date (newest first).
    
    Args:
        size: Number of records per page (default: 50, API max)
        page: Page number (1-based, default: 1)
        status: Optional status filter (integer)
        search_term: Search keyword for OrderNo, OrderNoExt, and Description (supports wildcards with %)
        since_date: Optional ISO 8601 date filter (overrides auto_filter_recent if provided)
        auto_filter_recent: If True, applies 12-month recent filter automatically (default: True)
        auto_paginate: If True, automatically fetches up to 200 records (default: True)
        include_all_data: If True, disables recent filtering to get all historical data (default: False)
        filter_quality: If True, filters out template/test orders (default: True)
        
    Returns:
        Formatted list of recent, quality production orders with key details
    """
    # Auto-paginate up to 200 records (4 pages) if enabled
    all_orders = []
    max_auto_pages = 4 if auto_paginate and page == 1 else 1
    total_pages = 0
    total_records = 0
    
    for page_num in range(page, page + max_auto_pages):
        # Use unified API parameters with consistent defaults
        params = get_unified_api_params(
            size=size,
            page=page_num,
            auto_filter_recent=auto_filter_recent,
            since_date=since_date,
            status=str(status) if status is not None else None,
            search_term=search_term,
            include_all_data=include_all_data
        )
        
        try:
            result = await make_oseon_request("/api/v2/pps/productionOrders/full/search", params)
            
            if not result.get("collection"):
                if page_num == page:  # First page
                    return "No production orders found with the specified criteria."
                else:
                    break  # No more data
                    
            orders = result["collection"]
            
            # Apply quality filtering if enabled
            if filter_quality:
                orders = filter_quality_orders(orders)
            
            all_orders.extend(orders)
            
            # Store metadata from first successful request
            if page_num == page:
                total_pages = result.get("pages", 1)
                total_records = result.get("records", 0)
            
            # If we got less than requested size, we've reached the end
            if len(orders) < size:
                break
                
        except Exception as e:
            if page_num == page:
                return f"Error retrieving production orders: {str(e)}"
            else:
                break  # Error fetching additional pages, stop here
    
    if not all_orders:
        return "No production orders found with the specified criteria."
    
    # Build response with unified system info
    filter_info = []
    if not include_all_data and auto_filter_recent:
        filter_info.append("Recent (12 months)")
    if since_date and not auto_filter_recent:
        filter_info.append(f"Since: {since_date}")
    if status is not None:
        filter_info.append(f"Status: {status}")
    if filter_quality:
        filter_info.append("Quality filtered")
    
    filter_desc = " | ".join(filter_info) if filter_info else "No filters"
    
    # Calculate display info
    pages_fetched = min(max_auto_pages, total_pages - page + 1) if auto_paginate else 1
    end_page = page + pages_fetched - 1
    
    if auto_paginate and pages_fetched > 1:
        response = f"🔄 PRODUCTION ORDERS (Unified System - {filter_desc}):\n"
        response += f"📊 Auto-paginated: Pages {page}-{end_page}, {len(all_orders)} quality records of {total_records} total\n"
    else:
        response = f"🔄 PRODUCTION ORDERS (Unified System - {filter_desc}):\n"
        response += f"📊 Page {page}, {len(all_orders)} quality records of {total_records} total\n"
    
    response += "=" * 100 + "\n"
    
    for order in all_orders:
        response += format_production_order(order)
        response += "-" * 100 + "\n"
        
    # Add pagination guidance
    if total_pages > end_page:
        response += "\n" + "=" * 100 + "\n"
        response += f"📄 PAGINATION: Showing {len(all_orders)} quality records from {pages_fetched} pages\n"
        response += f"💡 NEXT: Use page={end_page + 1} to continue\n"
        response += f"🔧 BULK: Use get_production_orders_bulk() for 200+ records with array storage\n"
        response += f"🗂️ ALL DATA: Use include_all_data=True to access historical data beyond 12 months\n"
    elif len(all_orders) >= 200:
        response += "\n" + "=" * 100 + "\n"
        response += f"📊 BULK DATA: Fetched {len(all_orders)} quality records\n"
        response += f"🔧 BULK: Use get_production_orders_bulk() for structured array storage of large datasets\n"
            
    return response

@mcp.tool()
async def get_production_orders_for_customer_order(
    customer_order_no: str,
    size: int = 50
) -> str:
    """
    Get all production orders related to a specific customer order.
    
    Args:
        customer_order_no: Customer order number to find related production orders
        size: Maximum number of results (default: 50)
        
    Returns:
        List of production orders linked to the customer order
    """
    # Use wildcard search to find all production orders for this customer order
    search_term = f"{customer_order_no}%"
    
    params = {
        "size": min(size, 50),
        "page": 0,
        "searchBy": search_term
    }
    
    try:
        result = await make_oseon_request("/api/v2/pps/productionOrders/full/search", params)
        
        if not result.get("collection"):
            return f"No production orders found for customer order {customer_order_no}."
            
        orders = result["collection"]
        # Filter to exact customer order matches
        related_orders = [order for order in orders if order.get("customerOrderNo") == customer_order_no]
        
        if not related_orders:
            return f"No production orders found for customer order {customer_order_no}."
            
        total_records = len(related_orders)
        
        response = f"PRODUCTION ORDERS FOR CUSTOMER ORDER {customer_order_no} - {total_records} orders found:\n"
        response += "=" * 100 + "\n"
        
        for order in related_orders:
            response += format_production_order(order, show_operations=True)
            response += "-" * 100 + "\n"
            
        return response
        
    except Exception as e:
        return f"Error retrieving production orders for customer order {customer_order_no}: {str(e)}"

@mcp.tool()
async def get_customer_order_for_production_order(
    production_order_no: str
) -> str:
    """
    Get the customer order details related to a specific production order.
    
    Args:
        production_order_no: Production order number (e.g., "238259-001")
        
    Returns:
        Customer order details for the related production order
    """
    # First, get the production order to find the customerOrderNo
    search_params = {
        "size": 10,
        "page": 0,
        "searchBy": production_order_no
    }
    
    try:
        prod_result = await make_oseon_request("/api/v2/pps/productionOrders/full/search", search_params)
        
        if not prod_result.get("collection"):
            return f"Production order {production_order_no} not found."
            
        production_order = None
        for order in prod_result["collection"]:
            if order.get("orderNo") == production_order_no:
                production_order = order
                break
                
        if not production_order:
            return f"Production order {production_order_no} not found."
            
        customer_order_no = production_order.get("customerOrderNo")
        if not customer_order_no:
            return f"No customer order linked to production order {production_order_no}."
            
        # Now get the customer order details
        customer_params = {
            "size": 10,
            "page": 0,
            "searchBy": customer_order_no
        }
        
        customer_result = await make_oseon_request("/api/v2/sales/customerOrders", customer_params)
        
        if not customer_result.get("collection"):
            return f"Customer order {customer_order_no} not found."
            
        customer_order = None
        for order in customer_result["collection"]:
            if order.get("customerOrderNo") == customer_order_no:
                customer_order = order
                break
                
        if not customer_order:
            return f"Customer order {customer_order_no} not found."
            
        response = f"CUSTOMER ORDER FOR PRODUCTION ORDER {production_order_no}:\n"
        response += "=" * 100 + "\n"
        response += format_customer_order(customer_order)
        response += "\n" + "=" * 100 + "\n"
        response += f"🔗 LINKED PRODUCTION ORDER:\n"
        response += format_production_order(production_order)
        
        return response
        
    except Exception as e:
        return f"Error retrieving customer order for production order {production_order_no}: {str(e)}"

@mcp.tool()
async def search_orders_with_wildcards(
    search_pattern: str,
    search_in: str = "both",
    size: int = 25
) -> str:
    """
    Search for orders using wildcard patterns (% symbol).
    
    Args:
        search_pattern: Search pattern with wildcards (e.g., "238259%", "%metal%", "200%")
        search_in: Where to search - "customer" for customer orders, "production" for production orders, "both" for both (default: "both")
        size: Maximum results per order type (default: 25)
        
    Returns:
        Search results from customer orders, production orders, or both
    """
    response = f"WILDCARD SEARCH RESULTS FOR PATTERN: '{search_pattern}'\n"
    response += "=" * 100 + "\n\n"
    
    try:
        if search_in in ["customer", "both"]:
            # Search customer orders
            customer_params = {
                "size": min(size, 50),
                "page": 0,
                "searchBy": search_pattern
            }
            
            customer_result = await make_oseon_request("/api/v2/sales/customerOrders", customer_params)
            
            if customer_result.get("collection"):
                customer_orders = customer_result["collection"]
                response += f"📋 CUSTOMER ORDERS ({len(customer_orders)} found):\n"
                response += "-" * 100 + "\n"
                
                for order in customer_orders:
                    response += format_customer_order(order)
                    response += "-" * 50 + "\n"
            else:
                response += "📋 CUSTOMER ORDERS: No matches found\n"
                
            response += "\n"
            
        if search_in in ["production", "both"]:
            # Search production orders
            production_params = {
                "size": min(size, 50),
                "page": 0,
                "searchBy": search_pattern
            }
            
            production_result = await make_oseon_request("/api/v2/pps/productionOrders/full/search", production_params)
            
            if production_result.get("collection"):
                production_orders = production_result["collection"]
                response += f"🏭 PRODUCTION ORDERS ({len(production_orders)} found):\n"
                response += "-" * 100 + "\n"
                
                for order in production_orders:
                    response += format_production_order(order)
                    response += "-" * 50 + "\n"
            else:
                response += "🏭 PRODUCTION ORDERS: No matches found\n"
                
        return response
        
    except Exception as e:
        return f"Error performing wildcard search: {str(e)}"

@mcp.tool()
async def get_production_orders_bulk(
    size: int = 50,
    start_page: int = 1,
    num_pages: int = 3,
    status: Optional[int] = None,
    search_term: Optional[str] = None,
    since_date: Optional[str] = None
) -> str:
    """
    Get multiple pages of production orders in bulk.
    Perfect for when you need large amounts of data (like pages 234, 235, 236).
    
    Args:
        size: Number of records per page (max 50, default: 50)
        start_page: Starting page number (1-based, default: 1)
        num_pages: Number of consecutive pages to fetch (default: 3, max: 10)
        status: Optional status filter (integer)
        search_term: Search keyword with wildcards (e.g., "238259%")
        since_date: Optional ISO 8601 date filter
        
    Returns:
        Formatted list of production orders from multiple pages
    """
    # Limit for performance
    num_pages = min(num_pages, 10)
    size = min(size, 50)
    
    all_orders = []
    total_pages = 0
    total_records = 0
    pages_fetched = []
    
    for page_offset in range(num_pages):
        current_page = start_page + page_offset
        params = get_standard_production_order_params(size, current_page, status, search_term, since_date)
        
        try:
            result = await make_oseon_request("/api/v2/pps/productionOrders/full/search", params)
            
            if not result.get("collection"):
                if page_offset == 0:
                    return f"No production orders found starting from page {start_page}."
                else:
                    break  # No more data
                    
            orders = result["collection"]
            all_orders.extend(orders)
            pages_fetched.append(current_page)
            
            # Capture metadata from first request
            if page_offset == 0:
                total_pages = result.get("pages", 1)
                total_records = result.get("records", 0)
                
        except Exception as e:
            if page_offset == 0:
                return f"Error retrieving production orders from page {current_page}: {str(e)}"
            else:
                break  # Stop on error
    
    if not all_orders:
        return f"No production orders found starting from page {start_page}."
    
    # Format page range
    if len(pages_fetched) > 1:
        page_range = f"Pages {pages_fetched[0]}-{pages_fetched[-1]}"
    else:
        page_range = f"Page {pages_fetched[0]}"
        
    response = f"PRODUCTION ORDERS BULK - {len(all_orders)} orders from {page_range} of {total_pages} total pages:\n"
    response += "=" * 100 + "\n"
    response += f"📊 Total records in system: {total_records}\n"
    response += "=" * 100 + "\n"
    
    for order in all_orders:
        response += format_production_order(order)
        response += "-" * 100 + "\n"
        
    response += "\n" + "=" * 100 + "\n"
    response += f"📄 BULK FETCH: Retrieved {len(pages_fetched)} pages ({len(all_orders)} orders)\n"
    if pages_fetched[-1] < total_pages:
        next_start = pages_fetched[-1] + 1
        response += f"💡 TIP: Use start_page={next_start} to continue, or increase num_pages for more data\n"
        
    return response

@mcp.tool()
async def get_customer_orders_bulk(
    size: int = 50,
    start_page: int = 1,
    num_pages: int = 3,
    status: Optional[str] = None,
    customer_no: Optional[str] = None,
    search_term: Optional[str] = None,
    since_date: Optional[str] = None
) -> str:
    """
    Get multiple pages of customer orders in bulk.
    Perfect for when you need large amounts of data.
    
    Args:
        size: Number of records per page (max 50, default: 50)
        start_page: Starting page number (1-based, default: 1)
        num_pages: Number of consecutive pages to fetch (default: 3, max: 10)
        status: Filter by order status
        customer_no: Filter by customer number
        search_term: Search with wildcards (e.g., "238259%")
        since_date: Optional ISO 8601 date filter
        
    Returns:
        Formatted list of customer orders from multiple pages
    """
    # Limit for performance
    num_pages = min(num_pages, 10)
    size = min(size, 50)
    
    all_orders = []
    total_pages = 0
    total_records = 0
    pages_fetched = []
    
    for page_offset in range(num_pages):
        current_page = start_page + page_offset
        params = get_standard_customer_order_params(size, current_page, status, customer_no, since_date, search_term, None)
        
        try:
            result = await make_oseon_request("/api/v2/sales/customerOrders", params)
            
            if not result.get("collection"):
                if page_offset == 0:
                    return f"No customer orders found starting from page {start_page}."
                else:
                    break  # No more data
                    
            orders = result["collection"]
            all_orders.extend(orders)
            pages_fetched.append(current_page)
            
            # Capture metadata from first request
            if page_offset == 0:
                total_pages = result.get("pages", 1)
                total_records = result.get("records", 0)
                
        except Exception as e:
            if page_offset == 0:
                return f"Error retrieving customer orders from page {current_page}: {str(e)}"
            else:
                break  # Stop on error
    
    if not all_orders:
        return f"No customer orders found starting from page {start_page}."
    
    # Format page range
    if len(pages_fetched) > 1:
        page_range = f"Pages {pages_fetched[0]}-{pages_fetched[-1]}"
    else:
        page_range = f"Page {pages_fetched[0]}"
        
    response = f"CUSTOMER ORDERS BULK - {len(all_orders)} orders from {page_range} of {total_pages} total pages:\n"
    response += "=" * 100 + "\n"
    response += f"📊 Total records in system: {total_records}\n"
    response += "=" * 100 + "\n"
    
    for order in all_orders:
        response += format_customer_order(order)
        response += "-" * 100 + "\n"
        
    response += "\n" + "=" * 100 + "\n"
    response += f"📄 BULK FETCH: Retrieved {len(pages_fetched)} pages ({len(all_orders)} orders)\n"
    if pages_fetched[-1] < total_pages:
        next_start = pages_fetched[-1] + 1
        response += f"💡 TIP: Use start_page={next_start} to continue, or increase num_pages for more data\n"
        
    return response

# Removed get_production_status_overview - inefficient data scanning
# Use specific status functions instead:
# - get_released_production_orders() for RELEASED status
# - get_in_progress_production_orders() for IN_PROGRESS status  
# - get_finished_production_orders() for FINISHED status

@mcp.tool()
async def check_production_order_overdue(
    search_term: str,
    days_overdue: int = 7,
    max_results: int = 50
) -> str:
    """
    Check for overdue production orders matching a search term.
    This is efficient because it uses the searchBy API filter.
    
    Args:
        search_term: Search term for OrderNo, OrderNoExt, Description (required for efficiency)
        days_overdue: Number of days past due date to consider (default: 7)
        max_results: Maximum number of results to return (default: 50, API max)
        
    Returns:
        Overdue production orders matching the search term
    """
    params = {
        "searchBy": search_term,
        "size": min(max_results, 50),
        "page": 0
    }
    
    try:
        result = await make_oseon_request("/api/v2/pps/productionOrders/full/search", params)
        
        if not result.get("collection"):
            return f"No production orders found matching '{search_term}'."
            
        orders = result["collection"]
        overdue_orders = []
        
        for order in orders:
            due_date_str = order.get("dueDate")
            if due_date_str and is_order_overdue(due_date_str, order.get("status")):
                try:
                    due_date = datetime.strptime(due_date_str, "%d.%m.%Y %H:%M:%S")
                    days_past_due = (datetime.now() - due_date).days
                    if days_past_due >= days_overdue:
                        order["days_overdue"] = days_past_due
                        overdue_orders.append(order)
                except ValueError:
                    pass
        
        if not overdue_orders:
            return f"✅ No overdue production orders found matching '{search_term}'."
        
        overdue_orders.sort(key=lambda x: x.get("days_overdue", 0), reverse=True)
        
        response = f"⚠️ OVERDUE PRODUCTION ORDERS matching '{search_term}' - {len(overdue_orders)} orders:\n"
        response += "=" * 100 + "\n"
        
        for order in overdue_orders[:max_results]:
            days_past_due = order.get("days_overdue", 0)
            urgency = "🔴 CRITICAL" if days_past_due > 7 else "🟡 URGENT" if days_past_due > 3 else "🟠 OVERDUE"
            
            response += f"{urgency} ({days_past_due} days overdue)\n"
            response += format_production_order(order, show_operations=True)
            response += "-" * 100 + "\n"
            
        return response
        
    except Exception as e:
        return f"Error checking overdue production orders: {str(e)}"

# Removed get_active_production_orders - inefficient operation scanning
# Use get_in_progress_production_orders instead for orders with IN_PROGRESS status

@mcp.tool()
async def search_production_orders(
    search_term: str,
    max_results: int = 50,
    status: Optional[int] = None
) -> str:
    """
    Search production orders by OrderNo, OrderNoExt, or Description.
    
    Args:
        search_term: Search keyword for OrderNo, OrderNoExt, and Description
        max_results: Maximum number of results to return (default: 25)
        status: Optional status filter (integer)
        
    Returns:
        Formatted list of matching production orders
    """
    params = {
        "searchBy": search_term,
        "size": min(max_results, 50)
    }
    
    if status is not None:
        params["status"] = status
    
    try:
        result = await make_oseon_request("/api/v2/pps/productionOrders/full/search", params)
        
        if not result.get("collection"):
            return f"No production orders found matching '{search_term}'."
            
        orders = result["collection"]
        total_records = result.get("records", len(orders))
        
        response = f"🔍 PRODUCTION ORDER SEARCH RESULTS for '{search_term}' - {len(orders)} of {total_records} orders:\n"
        response += "=" * 100 + "\n"
        
        for order in orders:
            response += format_production_order(order, show_operations=True)
            response += "-" * 100 + "\n"
            
        return response
        
    except Exception as e:
        return f"Error searching production orders: {str(e)}"

def format_production_order(order: Dict[str, Any], show_operations: bool = False, highlight_active: bool = False) -> str:
    """Format a production order for display."""
    order_no = order.get("orderNo", "N/A")
    description = order.get("description", "")
    status = order.get("status", "N/A")
    customer_name = order.get("customerName", "N/A")
    customer_order_no = order.get("customerOrderNo", "N/A")
    part_no = order.get("partNo", "N/A")
    part_description = order.get("partDescription", "")
    due_date = order.get("dueDate", "N/A")
    desired_qty = order.get("desiredQuantity", "N/A")
    processed_parts = order.get("processedParts", 0)
    
    result = f"📋 Order: {order_no}"
    if description:
        result += f" - {description}"
    result += f"\n"
    
    result += f"   Status: {status} | Customer: {customer_name} (Order: {customer_order_no})\n"
    result += f"   Part: {part_no}"
    if part_description:
        result += f" - {part_description}"
    result += f"\n"
    result += f"   Due: {due_date} | Qty: {processed_parts}/{desired_qty}\n"
    
    if show_operations and order.get("operations"):
        operations = order.get("active_operations", order.get("operations", []))
        if operations:
            result += f"   🔧 Operations:\n"
            for op in operations[:3]:  # Show max 3 operations
                op_no = op.get("operationNo", "N/A")
                activity = op.get("activity", "N/A")
                workplace = op.get("workplaceName", "N/A")
                op_status = op.get("status", "N/A")
                
                # Highlight active operations
                status_indicator = "🔄" if highlight_active and op_status not in ["COMPLETED", "CANCELED"] else "⚪"
                
                result += f"      {status_indicator} {op_no}: {activity} @ {workplace} ({op_status})\n"
            
            if len(operations) > 3:
                result += f"      ... and {len(operations) - 3} more operations\n"
    
    return result

@mcp.tool()
async def get_production_dashboard() -> str:
    """Get production status dashboard - consistent 4-step overview for management.
    
    🗓️ DEFAULT FILTER: 7-day timeframe for focused daily operations.
    
    Returns structured data for 'How's production?' with:
    - Active work (orders in progress, last 7 days)
    - Pipeline (orders ready to start, last 14 days)
    - Recent completions (last 3 days)
    - Production issues (1+ days overdue)
    
    Perfect for daily management meetings and AI agent consistency.
    
    📊 FOR MORE COMPREHENSIVE DATA:
    - Use get_production_orders(since_date="YYYY-MM-DD") for custom timeframes
    - Use get_production_orders(include_all_data=True) for all historical data
    - Use get_in_progress_production_orders(since_days=30) for broader active work
    """
    try:
        results = {
            "dashboard_type": "Production Status",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sections": []
        }
        
        # 1. Active Production Work (limit 25 for consistency)
        try:
            active_response = await get_in_progress_production_orders(max_results=25, since_days=7)
            active_count = len([line for line in active_response.split('\n') if 'Production Order:' in line])
            results["sections"].append({
                "name": "Active Production",
                "status": "✅",
                "count": active_count,
                "description": f"{active_count} orders currently in progress (last 7 days)",
                "timeframe": "7 days"
            })
        except Exception as e:
            results["sections"].append({
                "name": "Active Production",
                "status": "❌",
                "count": 0,
                "description": f"Error getting active orders: {str(e)}",
                "timeframe": "7 days"
            })
        
        # 2. Production Pipeline (limit 25 for consistency)
        try:
            pipeline_response = await get_released_production_orders(max_results=25, since_days=14)
            pipeline_count = len([line for line in pipeline_response.split('\n') if 'Production Order:' in line])
            results["sections"].append({
                "name": "Production Pipeline",
                "status": "⏳",
                "count": pipeline_count,
                "description": f"{pipeline_count} orders ready to start production (last 14 days)",
                "timeframe": "14 days"
            })
        except Exception as e:
            results["sections"].append({
                "name": "Production Pipeline",
                "status": "❌",
                "count": 0,
                "description": f"Error getting pipeline orders: {str(e)}",
                "timeframe": "14 days"
            })
        
        # 3. Recent Completions (limit 25 for consistency)
        try:
            completed_response = await get_finished_production_orders(max_results=25, since_days=3)
            completed_count = len([line for line in completed_response.split('\n') if 'Production Order:' in line])
            results["sections"].append({
                "name": "Recent Completions",
                "status": "🏆",
                "count": completed_count,
                "description": f"{completed_count} orders completed (last 3 days)",
                "timeframe": "3 days"
            })
        except Exception as e:
            results["sections"].append({
                "name": "Recent Completions",
                "status": "❌",
                "count": 0,
                "description": f"Error getting completed orders: {str(e)}",
                "timeframe": "3 days"
            })
        
        # 4. Production Issues (limit 25 for consistency)
        try:
            overdue_response = await check_production_order_overdue(search_term="%", max_results=25, days_overdue=1)
            overdue_count = len([line for line in overdue_response.split('\n') if 'Production Order:' in line])
            status_icon = "⚠️" if overdue_count > 0 else "✅"
            results["sections"].append({
                "name": "Production Issues",
                "status": status_icon,
                "count": overdue_count,
                "description": f"{overdue_count} orders overdue by 1+ days" if overdue_count > 0 else "No production delays",
                "timeframe": "1+ days overdue"
            })
        except Exception as e:
            results["sections"].append({
                "name": "Production Issues",
                "status": "❌",
                "count": 0,
                "description": f"Error checking overdue orders: {str(e)}",
                "timeframe": "1+ days overdue"
            })
        
        # Format consistent dashboard output
        output = f"""
🏭 PRODUCTION DASHBOARD - {results['timestamp']}

{results['sections'][0]['status']} {results['sections'][0]['name']}: {results['sections'][0]['count']} orders
   └── {results['sections'][0]['description']}

{results['sections'][1]['status']} {results['sections'][1]['name']}: {results['sections'][1]['count']} orders  
   └── {results['sections'][1]['description']}

{results['sections'][2]['status']} {results['sections'][2]['name']}: {results['sections'][2]['count']} orders
   └── {results['sections'][2]['description']}

{results['sections'][3]['status']} {results['sections'][3]['name']}: {results['sections'][3]['count']} orders
   └── {results['sections'][3]['description']}

📊 SUMMARY: {results['sections'][0]['count']} active | {results['sections'][1]['count']} pipeline | {results['sections'][2]['count']} completed | {results['sections'][3]['count']} issues

🗓️ TIMEFRAME: 7-day focused view for daily operations
💡 FOR MORE DATA: Use get_production_orders(since_days=30) or get_production_orders(include_all_data=True)
   For specific details, use individual production order tools.
"""
        
        return output.strip()
        
    except Exception as e:
        return f"❌ Error generating production dashboard: {str(e)}"


@mcp.tool()
async def get_production_dashboard_template() -> str:
    """Get React template for production dashboard - ready for Claude artifact creation.
    
    Returns precompiled React/TypeScript component with:
    - Modern dashboard design
    - Consistent structure matching get_production_dashboard()
    - Ready-to-use template for instant artifacts
    - Placeholder data that can be replaced with real data
    
    Perfect for Claude to quickly create visual dashboards.
    """
    template = '''import React from 'react';

interface DashboardSection {
  name: string;
  status: string;
  count: number;
  description: string;
  timeframe: string;
}

interface ProductionDashboardData {
  timestamp: string;
  sections: DashboardSection[];
  summary: {
    active: number;
    pipeline: number;
    completed: number;
    issues: number;
  };
}

const ProductionDashboard: React.FC<{ data?: ProductionDashboardData }> = ({ data }) => {
  // Default template data - replace with real data from get_production_dashboard()
  const defaultData: ProductionDashboardData = {
    timestamp: "2024-01-15 14:30:22",
    sections: [
      {
        name: "Active Production",
        status: "✅",
        count: 12,
        description: "12 orders currently in progress (last 7 days)",
        timeframe: "7 days"
      },
      {
        name: "Production Pipeline", 
        status: "⏳",
        count: 8,
        description: "8 orders ready to start production (last 14 days)",
        timeframe: "14 days"
      },
      {
        name: "Recent Completions",
        status: "🏆", 
        count: 5,
        description: "5 orders completed (last 3 days)",
        timeframe: "3 days"
      },
      {
        name: "Production Issues",
        status: "✅",
        count: 0,
        description: "No production delays",
        timeframe: "1+ days overdue"
      }
    ],
    summary: { active: 12, pipeline: 8, completed: 5, issues: 0 }
  };

  const dashboardData = data || defaultData;

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-3xl">🏭</span>
            <h1 className="text-3xl font-bold text-gray-800">Production Dashboard</h1>
          </div>
          <p className="text-gray-600">Last updated: {dashboardData.timestamp}</p>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
            <div className="text-2xl font-bold text-blue-700">{dashboardData.summary.active}</div>
            <div className="text-blue-600">Active</div>
          </div>
          <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded">
            <div className="text-2xl font-bold text-yellow-700">{dashboardData.summary.pipeline}</div>
            <div className="text-yellow-600">Pipeline</div>
          </div>
          <div className="bg-green-50 border-l-4 border-green-500 p-4 rounded">
            <div className="text-2xl font-bold text-green-700">{dashboardData.summary.completed}</div>
            <div className="text-green-600">Completed</div>
          </div>
          <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded">
            <div className="text-2xl font-bold text-red-700">{dashboardData.summary.issues}</div>
            <div className="text-red-600">Issues</div>
          </div>
        </div>

        {/* Detailed Sections */}
        <div className="grid grid-cols-2 gap-6">
          {dashboardData.sections.map((section, index) => (
            <div key={index} className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">{section.status}</span>
                <h3 className="text-xl font-semibold text-gray-800">{section.name}</h3>
                <span className="ml-auto text-2xl font-bold text-gray-700">{section.count}</span>
              </div>
              <p className="text-gray-600 mb-2">{section.description}</p>
              <div className="text-sm text-gray-500 bg-gray-50 px-3 py-1 rounded">
                Timeframe: {section.timeframe}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>💡 Use get_production_dashboard() to get real-time data for this template</p>
        </div>
      </div>
    </div>
  );
};

export default ProductionDashboard;'''

    return f"""
📊 PRODUCTION DASHBOARD TEMPLATE (React/TypeScript)

Ready-to-use React component for Claude artifacts:

{template}

🚀 USAGE INSTRUCTIONS:
1. Copy this entire component code
2. Replace defaultData with real data from get_production_dashboard()
3. Claude can instantly create visual dashboard artifacts
4. Modern responsive design with Tailwind CSS
5. TypeScript interfaces included for type safety

💡 BENEFITS:
- Instant artifact creation (no coding from scratch)
- Consistent with get_production_dashboard() structure
- Professional dashboard design
- Responsive layout for all devices
- Easy to customize colors and layout

🔧 TO USE WITH REAL DATA:
1. Call get_production_dashboard() to get current data
2. Parse the structured output into the ProductionDashboardData interface
3. Pass as props to the component
4. Claude can do this automatically for instant dashboards!
"""


@mcp.tool()
async def get_sales_dashboard_template() -> str:
    """Get React template for sales dashboard - ready for Claude artifact creation.
    
    Returns precompiled React/TypeScript component with:
    - Modern dashboard design  
    - Consistent structure matching get_sales_dashboard()
    - Ready-to-use template for instant artifacts
    - Placeholder data that can be replaced with real data
    
    Perfect for Claude to quickly create visual dashboards.
    """
    template = '''import React from 'react';

interface DashboardSection {
  name: string;
  status: string;
  count: number;
  description: string;
  timeframe: string;
}

interface SalesDashboardData {
  timestamp: string;
  sections: DashboardSection[];
  summary: {
    new: number;
    ready: number;
    issues: number;
    changes: number;
  };
}

const SalesDashboard: React.FC<{ data?: SalesDashboardData }> = ({ data }) => {
  // Default template data - replace with real data from get_sales_dashboard()
  const defaultData: SalesDashboardData = {
    timestamp: "2024-01-15 14:30:25",
    sections: [
      {
        name: "New Business",
        status: "💰",
        count: 6,
        description: "6 customer orders received (last 7 days)",
        timeframe: "7 days"
      },
      {
        name: "Ready for Production",
        status: "🔄", 
        count: 4,
        description: "4 orders released to manufacturing",
        timeframe: "current"
      },
      {
        name: "Delivery Issues",
        status: "⚠️",
        count: 1,
        description: "1 customer orders overdue by 1+ days",
        timeframe: "1+ days overdue"
      },
      {
        name: "Recent Changes",
        status: "📝",
        count: 3,
        description: "3 orders modified (last 3 days)",
        timeframe: "3 days"
      }
    ],
    summary: { new: 6, ready: 4, issues: 1, changes: 3 }
  };

  const dashboardData = data || defaultData;

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-3xl">💼</span>
            <h1 className="text-3xl font-bold text-gray-800">Sales Dashboard</h1>
          </div>
          <p className="text-gray-600">Last updated: {dashboardData.timestamp}</p>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="bg-green-50 border-l-4 border-green-500 p-4 rounded">
            <div className="text-2xl font-bold text-green-700">{dashboardData.summary.new}</div>
            <div className="text-green-600">New Orders</div>
          </div>
          <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
            <div className="text-2xl font-bold text-blue-700">{dashboardData.summary.ready}</div>
            <div className="text-blue-600">Ready</div>
          </div>
          <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded">
            <div className="text-2xl font-bold text-red-700">{dashboardData.summary.issues}</div>
            <div className="text-red-600">Issues</div>
          </div>
          <div className="bg-purple-50 border-l-4 border-purple-500 p-4 rounded">
            <div className="text-2xl font-bold text-purple-700">{dashboardData.summary.changes}</div>
            <div className="text-purple-600">Changes</div>
          </div>
        </div>

        {/* Detailed Sections */}
        <div className="grid grid-cols-2 gap-6">
          {dashboardData.sections.map((section, index) => (
            <div key={index} className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">{section.status}</span>
                <h3 className="text-xl font-semibold text-gray-800">{section.name}</h3>
                <span className="ml-auto text-2xl font-bold text-gray-700">{section.count}</span>
              </div>
              <p className="text-gray-600 mb-2">{section.description}</p>
              <div className="text-sm text-gray-500 bg-gray-50 px-3 py-1 rounded">
                Timeframe: {section.timeframe}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>💡 Use get_sales_dashboard() to get real-time data for this template</p>
        </div>
      </div>
    </div>
  );
};

export default SalesDashboard;'''

    return f"""
📊 SALES DASHBOARD TEMPLATE (React/TypeScript)

Ready-to-use React component for Claude artifacts:

{template}

🚀 USAGE INSTRUCTIONS:
1. Copy this entire component code
2. Replace defaultData with real data from get_sales_dashboard()
3. Claude can instantly create visual dashboard artifacts
4. Modern responsive design with Tailwind CSS
5. TypeScript interfaces included for type safety

💡 BENEFITS:
- Instant artifact creation (no coding from scratch)
- Consistent with get_sales_dashboard() structure
- Professional dashboard design
- Responsive layout for all devices
- Easy to customize colors and layout

🔧 TO USE WITH REAL DATA:
1. Call get_sales_dashboard() to get current data
2. Parse the structured output into the SalesDashboardData interface
3. Pass as props to the component
4. Claude can do this automatically for instant dashboards!
"""


@mcp.tool()
async def get_sales_dashboard_with_production() -> str:
    """Get enhanced sales dashboard with automatic production order linking.
    
    🗓️ DEFAULT FILTER: 7-day timeframe for recent sales orders with linked production.
    
    Returns comprehensive sales+production view:
    - Recent sales orders (last 7 days)
    - Matching production orders for each sales order
    - Production status breakdown
    - Cross-system insights
    
    Perfect for sales teams who need to see both sides of the business.
    
    💡 FOR MORE COMPREHENSIVE DATA:
    - Use get_customer_orders(since_date="YYYY-MM-DD") + manual production lookup
    - Use get_sales_dashboard_with_production_by_status(status="RELEASED")
    - Use search_orders_with_wildcards("ORDER123%") for specific order families
    """
    try:
        results = {
            "dashboard_type": "Sales + Production View",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sales_orders": [],
            "production_summary": {"total": 0, "in_progress": 0, "released": 0, "finished": 0}
        }
        
        # Get recent sales orders (last 7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)
        sales_response = await get_customer_orders(
            size=15, 
            since_date=seven_days_ago.strftime("%Y-%m-%dT%H:%M:%S"), 
            auto_paginate=False,
            filter_quality=True
        )
        
        # Extract sales order numbers from response
        sales_order_numbers = []
        for line in sales_response.split('\n'):
            if 'Order #' in line:
                # Extract order number (e.g., "Order #400139" -> "400139")
                order_num = line.split('Order #')[1].split()[0]
                sales_order_numbers.append(order_num)
        
        # For each sales order, find matching production orders
        total_production_orders = 0
        production_status_counts = {"in_progress": 0, "released": 0, "finished": 0}
        
        sales_with_production = []
        
        for order_num in sales_order_numbers[:10]:  # Limit to 10 for performance
            try:
                # Get production orders for this customer order
                production_response = await get_production_orders_for_customer_order(order_num, size=10)
                
                production_orders = []
                if "No production orders found" not in production_response:
                    # Count production orders and their statuses
                    for line in production_response.split('\n'):
                        if 'Status:' in line:
                            total_production_orders += 1
                            if 'Status: 60' in line:  # IN_PROGRESS
                                production_status_counts["in_progress"] += 1
                            elif 'Status: 30' in line:  # RELEASED
                                production_status_counts["released"] += 1
                            elif 'Status: 90' in line:  # FINISHED
                                production_status_counts["finished"] += 1
                            
                            # Extract basic production order info
                            if 'Order:' in line:
                                prod_order = line.split('Order:')[1].split()[0] if 'Order:' in line else "Unknown"
                                production_orders.append(prod_order)
                
                sales_with_production.append({
                    "sales_order": order_num,
                    "production_orders": production_orders,
                    "production_count": len(production_orders)
                })
                
            except Exception as e:
                # Skip problematic orders but continue
                pass
        
        results["sales_orders"] = sales_with_production
        results["production_summary"] = {
            "total": total_production_orders,
            "in_progress": production_status_counts["in_progress"],
            "released": production_status_counts["released"], 
            "finished": production_status_counts["finished"]
        }
        
        # Format comprehensive output
        output = f"""
🏢 SALES + PRODUCTION DASHBOARD - {results['timestamp']}

📊 RECENT SALES ACTIVITY (Last 7 Days):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Found {len(sales_with_production)} sales orders with linked production data:

"""
        
        for item in sales_with_production[:8]:  # Show top 8
            prod_list = ", ".join(item["production_orders"]) if item["production_orders"] else "No production orders"
            output += f"""📋 Sales Order: {item['sales_order']}
   🏭 Production: {item['production_count']} orders → {prod_list}
   
"""
        
        output += f"""
🏭 PRODUCTION SUMMARY FOR RECENT SALES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Total Production Orders: {results['production_summary']['total']}
🔄 In Progress: {results['production_summary']['in_progress']} orders
⏳ Released: {results['production_summary']['released']} orders  
✅ Finished: {results['production_summary']['finished']} orders

🗓️ TIMEFRAME: 7-day focused view linking sales to production
💡 FOR SPECIFIC ORDERS: Use search_orders_with_wildcards("ORDER123%")
🔍 FOR STATUS FILTERING: Use get_customer_orders(status="RELEASED") + manual production lookup
   For broader timeframes, use get_customer_orders(since_days=30)
"""
        
        return output.strip()
        
    except Exception as e:
        return f"❌ Error generating enhanced sales dashboard: {str(e)}"


@mcp.tool()
async def get_sales_orders_with_production_by_status(
    status: str = "RELEASED",
    since_days: int = 30,
    max_results: int = 15
) -> str:
    """Get sales orders by status with automatic production order linking.
    
    🔍 Perfect for: "Show me RELEASED orders and their production status"
    
    Args:
        status: Sales order status ("RELEASED", "DELIVERED", "COMPLETED", etc.)
        since_days: Look back this many days (default: 30)
        max_results: Maximum sales orders to process (default: 15)
        
    Returns:
        Sales orders filtered by status with linked production orders and status breakdown
    """
    try:
        # Get sales orders by status
        since_date = datetime.now() - timedelta(days=since_days)
        sales_response = await get_customer_orders(
            size=max_results,
            status=status,
            since_date=since_date.strftime("%Y-%m-%dT%H:%M:%S"),
            auto_paginate=False,
            filter_quality=True
        )
        
        # Extract sales order numbers
        sales_order_numbers = []
        for line in sales_response.split('\n'):
            if 'Order #' in line:
                order_num = line.split('Order #')[1].split()[0]
                sales_order_numbers.append(order_num)
        
        if not sales_order_numbers:
            return f"No {status} sales orders found in the last {since_days} days."
        
        # Link to production orders
        linked_data = []
        production_summary = {"total": 0, "in_progress": 0, "released": 0, "finished": 0}
        
        for order_num in sales_order_numbers:
            try:
                production_response = await get_production_orders_for_customer_order(order_num, size=10)
                
                production_details = []
                if "No production orders found" not in production_response:
                    for line in production_response.split('\n'):
                        if 'Order:' in line and 'Status:' in line:
                            # Extract production order and status
                            parts = line.split()
                            prod_order = "Unknown"
                            status_val = "Unknown"
                            
                            for i, part in enumerate(parts):
                                if part == "Order:" and i + 1 < len(parts):
                                    prod_order = parts[i + 1]
                                elif part == "Status:" and i + 1 < len(parts):
                                    status_val = parts[i + 1]
                            
                            production_details.append(f"{prod_order} (Status: {status_val})")
                            production_summary["total"] += 1
                            
                            # Count by status
                            if status_val == "60":
                                production_summary["in_progress"] += 1
                            elif status_val == "30":
                                production_summary["released"] += 1
                            elif status_val == "90":
                                production_summary["finished"] += 1
                
                linked_data.append({
                    "sales_order": order_num,
                    "production_orders": production_details
                })
                
            except Exception as e:
                linked_data.append({
                    "sales_order": order_num,
                    "production_orders": [f"Error: {str(e)}"]
                })
        
        # Format output
        output = f"""
🔍 SALES ORDERS ({status}) WITH PRODUCTION LINKS - Last {since_days} Days

📋 SALES ORDERS FOUND: {len(linked_data)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        
        for item in linked_data:
            output += f"""📋 Sales Order: {item['sales_order']} (Status: {status})
   🏭 Production Orders:
"""
            if item['production_orders']:
                for prod in item['production_orders']:
                    output += f"      • {prod}\n"
            else:
                output += "      • No production orders found\n"
            output += "\n"
        
        output += f"""
🏭 PRODUCTION SUMMARY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Total Production Orders: {production_summary['total']}
🔄 In Progress (60): {production_summary['in_progress']} orders
⏳ Released (30): {production_summary['released']} orders
✅ Finished (90): {production_summary['finished']} orders

💡 FOR SPECIFIC ORDER: Use search_orders_with_wildcards("ORDER123%")
🔍 FOR OTHER STATUS: Change status parameter to "DELIVERED", "COMPLETED", etc.
"""
        
        return output.strip()
        
    except Exception as e:
        return f"❌ Error getting {status} sales orders with production: {str(e)}"


@mcp.tool()
async def get_specific_sales_order_with_production(
    order_pattern: str,
    include_details: bool = True
) -> str:
    """Get specific sales order(s) with complete production order details.
    
    🎯 Perfect for: "Show me order 400139 and all its production orders"
    
    Args:
        order_pattern: Order number or pattern (e.g., "400139", "400%", "ORDER123")
        include_details: Include detailed production operations (default: True)
        
    Returns:
        Detailed sales order info with complete production order breakdown
    """
    try:
        # Search for the sales order(s)
        sales_response = await search_orders_with_wildcards(
            search_pattern=order_pattern if "%" in order_pattern else f"{order_pattern}%",
            search_in="customer",
            size=10
        )
        
        # Extract sales order numbers from the response
        sales_orders = []
        current_order = None
        
        for line in sales_response.split('\n'):
            if 'Order #' in line:
                order_num = line.split('Order #')[1].split()[0]
                current_order = {"number": order_num, "details": []}
                sales_orders.append(current_order)
            elif current_order and line.strip() and not line.startswith('=') and not line.startswith('-'):
                current_order["details"].append(line.strip())
        
        if not sales_orders:
            return f"No sales orders found matching pattern: {order_pattern}"
        
        # Get detailed production information for each sales order
        output = f"""
🎯 SPECIFIC SALES ORDER ANALYSIS: {order_pattern}

📋 SALES ORDERS FOUND: {len(sales_orders)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        
        for sales_order in sales_orders:
            output += f"""📋 SALES ORDER: {sales_order['number']}
"""
            
            # Show sales order details
            for detail in sales_order['details'][:5]:  # Limit details
                if detail:
                    output += f"   {detail}\n"
            
            output += "\n🏭 LINKED PRODUCTION ORDERS:\n"
            output += "   " + "─" * 70 + "\n"
            
            try:
                if include_details:
                    production_response = await get_production_orders_for_customer_order(
                        sales_order['number'], 
                        size=20
                    )
                else:
                    # Use search for quick overview
                    production_response = await get_production_orders(
                        search_term=f"{sales_order['number']}%",
                        size=10,
                        auto_paginate=False,
                        include_all_data=True
                    )
                
                if "No production orders found" in production_response:
                    output += "   ❌ No production orders found\n\n"
                else:
                    # Extract and format production order info
                    prod_lines = production_response.split('\n')
                    for line in prod_lines:
                        if 'Order:' in line or 'Status:' in line or 'Due:' in line or 'Operations:' in line:
                            output += f"   {line}\n"
                        elif line.strip() and line.startswith('      ⚪'):  # Operation details
                            output += f"   {line}\n"
                    output += "\n"
                    
            except Exception as e:
                output += f"   ❌ Error getting production orders: {str(e)}\n\n"
        
        output += f"""
💡 USAGE TIPS:
• Use wildcards: "{order_pattern[:-1]}%" to find order families
• Set include_details=False for quick overview
• Use search_orders_with_wildcards() for broader searches
"""
        
        return output.strip()
        
    except Exception as e:
        return f"❌ Error analyzing order {order_pattern}: {str(e)}"


@mcp.tool()
async def get_sales_dashboard() -> str:
    """Get sales status dashboard - consistent 4-step overview for management.
    
    🗓️ DEFAULT FILTER: 7-day timeframe for focused daily operations.
    
    Returns structured data for 'How's sales?' with:
    - New business (recent orders, last 7 days)
    - Orders ready for production (current RELEASED status)
    - Delivery issues (1+ days overdue)
    - Recent order changes (last 3 days)
    
    Perfect for daily management meetings and AI agent consistency.
    
    📊 FOR MORE COMPREHENSIVE DATA:
    - Use get_customer_orders(since_date="YYYY-MM-DD") for custom timeframes
    - Use get_customer_orders(include_all_data=True) for all historical data
    - Use get_customer_orders(since_days=30) for broader recent activity
    """
    try:
        results = {
            "dashboard_type": "Sales Status",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sections": []
        }
        
        # 1. New Business (limit 25 for consistency)
        try:
            # Calculate 7 days ago for new business filter
            seven_days_ago = datetime.now() - timedelta(days=7)
            new_response = await get_customer_orders(size=25, since_date=seven_days_ago.strftime("%Y-%m-%dT%H:%M:%S"), auto_paginate=False)
            new_count = len([line for line in new_response.split('\n') if 'Order Number:' in line])
            results["sections"].append({
                "name": "New Business",
                "status": "💰",
                "count": new_count,
                "description": f"{new_count} customer orders received (last 7 days)",
                "timeframe": "7 days"
            })
        except Exception as e:
            results["sections"].append({
                "name": "New Business", 
                "status": "❌",
                "count": 0,
                "description": f"Error getting new orders: {str(e)}",
                "timeframe": "7 days"
            })
        
        # 2. Ready for Production (limit 25 for consistency)
        try:
            released_response = await get_customer_orders(size=25, status="RELEASED", auto_paginate=False)
            released_count = len([line for line in released_response.split('\n') if 'Order Number:' in line])
            results["sections"].append({
                "name": "Ready for Production",
                "status": "🔄",
                "count": released_count,
                "description": f"{released_count} orders released to manufacturing",
                "timeframe": "current"
            })
        except Exception as e:
            results["sections"].append({
                "name": "Ready for Production",
                "status": "❌", 
                "count": 0,
                "description": f"Error getting released orders: {str(e)}",
                "timeframe": "current"
            })
        
        # 3. Delivery Issues (limit 25 for consistency)
        try:
            overdue_response = await check_customer_order_overdue(customer_no="%", max_results=25, days_overdue=1)
            overdue_count = len([line for line in overdue_response.split('\n') if 'Order Number:' in line])
            status_icon = "⚠️" if overdue_count > 0 else "✅"
            results["sections"].append({
                "name": "Delivery Issues",
                "status": status_icon,
                "count": overdue_count,
                "description": f"{overdue_count} customer orders overdue by 1+ days" if overdue_count > 0 else "No delivery delays",
                "timeframe": "1+ days overdue"
            })
        except Exception as e:
            results["sections"].append({
                "name": "Delivery Issues",
                "status": "❌",
                "count": 0,
                "description": f"Error checking overdue orders: {str(e)}",
                "timeframe": "1+ days overdue"
            })
        
        # 4. Recent Changes (limit 25 for consistency)
        try:
            # Calculate 3 days ago for recent changes filter
            three_days_ago = datetime.now() - timedelta(days=3)
            modified_response = await get_modified_orders(since_date=three_days_ago.strftime("%Y-%m-%dT%H:%M:%S"), max_results=25)
            modified_count = len([line for line in modified_response.split('\n') if 'Order Number:' in line])
            results["sections"].append({
                "name": "Recent Changes",
                "status": "📝",
                "count": modified_count,
                "description": f"{modified_count} orders modified (last 3 days)",
                "timeframe": "3 days"
            })
        except Exception as e:
            results["sections"].append({
                "name": "Recent Changes",
                "status": "❌",
                "count": 0,
                "description": f"Error getting modified orders: {str(e)}",
                "timeframe": "3 days"
            })
        
        # Format consistent dashboard output
        output = f"""
💼 SALES DASHBOARD - {results['timestamp']}

{results['sections'][0]['status']} {results['sections'][0]['name']}: {results['sections'][0]['count']} orders
   └── {results['sections'][0]['description']}

{results['sections'][1]['status']} {results['sections'][1]['name']}: {results['sections'][1]['count']} orders
   └── {results['sections'][1]['description']}

{results['sections'][2]['status']} {results['sections'][2]['name']}: {results['sections'][2]['count']} orders
   └── {results['sections'][2]['description']}

{results['sections'][3]['status']} {results['sections'][3]['name']}: {results['sections'][3]['count']} orders
   └── {results['sections'][3]['description']}

📊 SUMMARY: {results['sections'][0]['count']} new | {results['sections'][1]['count']} ready | {results['sections'][2]['count']} issues | {results['sections'][3]['count']} changes

🗓️ TIMEFRAME: 7-day focused view for daily operations
💡 FOR MORE DATA: Use get_customer_orders(since_days=30) or get_customer_orders(include_all_data=True)
   For specific details, use individual customer order tools.
"""
        
        return output.strip()
        
    except Exception as e:
        return f"❌ Error generating sales dashboard: {str(e)}"


def main():
    """Main entry point for the MCP server.
    
    Starts the MCP server using stdio transport for Claude Desktop integration.
    """
    load_dotenv()  # Load .env file at runtime
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()