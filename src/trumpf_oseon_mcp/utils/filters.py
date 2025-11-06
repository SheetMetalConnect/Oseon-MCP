"""Data filtering utilities for TRUMPF Oseon API.

This module provides functions for filtering and validating order data,
including quality checks and demo mode sanitization.
"""

from datetime import datetime
from typing import Any, Dict, List


def get_default_since_date(months_back: int = 12) -> str:
    """Get dynamic default since_date for filtering recent records.

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
    """Check if order represents real production data (not template/test).

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


def filter_quality_orders(orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter orders to include only quality production data.

    Args:
        orders: List of order dictionaries

    Returns:
        Filtered list containing only quality production orders
    """
    return [order for order in orders if is_quality_production_data(order)]


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


def sanitize_for_demo(data: Any, demo_mode: bool = False) -> Any:
    """Sanitize customer data for demo purposes.

    Replaces real customer information with demo-safe values.

    Args:
        data: Data to sanitize
        demo_mode: Whether demo mode is enabled

    Returns:
        Sanitized data if demo_mode is True, otherwise original data
    """
    if not demo_mode or not isinstance(data, dict):
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
        sanitized['positions'] = [sanitize_for_demo(pos, demo_mode) for pos in sanitized['positions']]

    return sanitized
