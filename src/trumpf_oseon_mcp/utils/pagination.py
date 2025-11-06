"""Pagination utilities for TRUMPF Oseon API.

This module provides functions for handling pagination of API requests,
including smart pagination to fetch recent records efficiently.
"""

from typing import Dict, Optional


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
    """Get unified API parameters with consistent defaults across all commands.

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
    from .filters import get_default_since_date

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


def calculate_recent_page_params(
    total_pages: int,
    total_records: int,
    page_size: int,
    target_records: int = 150
) -> dict:
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


def get_standard_customer_order_params(
    size: int,
    page: int,
    status: Optional[str] = None,
    customer_no: Optional[str] = None,
    since_date: Optional[str] = None,
    search_term: Optional[str] = None,
    item_no: Optional[str] = None
) -> dict:
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


def get_standard_production_order_params(
    size: int,
    page: int,
    status: Optional[int] = None,
    search_term: Optional[str] = None,
    since_date: Optional[str] = None
) -> dict:
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
