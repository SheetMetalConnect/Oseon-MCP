"""Formatting utilities for TRUMPF Oseon API data.

This module provides functions for formatting order data into
human-readable strings for display.
"""

from typing import Any, Dict

from ..models.schemas import OrderStatus


def format_customer_order(order: Dict[str, Any], show_positions: bool = True, demo_mode: bool = False) -> str:
    """Format a customer order for display with enhanced status interpretation.

    This function takes raw order data from the TRUMPF Oseon API and formats it
    into a human-readable string with business context and calculated values.

    Args:
        order: Raw order data from the API
        show_positions: Whether to include detailed position information and calculations
        demo_mode: Whether to sanitize customer data for demo purposes

    Returns:
        str: Formatted order information ready for display to users
    """
    from .filters import sanitize_for_demo

    # Sanitize customer data for demo if needed
    sanitized_order = sanitize_for_demo(order, demo_mode)

    status = sanitized_order.get('status', 'N/A')
    status_category = OrderStatus.get_category(status)

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


def format_production_order(order: Dict[str, Any], show_details: bool = True, demo_mode: bool = False) -> str:
    """Format a production order for display.

    Args:
        order: Raw production order data from the API
        show_details: Whether to include detailed information
        demo_mode: Whether to sanitize customer data for demo purposes

    Returns:
        str: Formatted production order information
    """
    from .filters import sanitize_for_demo

    # Sanitize customer data for demo if needed
    sanitized_order = sanitize_for_demo(order, demo_mode)

    status = sanitized_order.get('status', 'N/A')
    status_category = OrderStatus.get_category(str(status))

    # Add business context to status
    status_info = f"{status}"
    if status_category == "NEWEST":
        status_info += " (Pre-production)"
    elif status_category == "RELEASED":
        status_info += " (In manufacturing)"
    elif status_category == "COMPLETED":
        status_info += " (Completed)"

    details_info = ""
    if show_details:
        details_info = f"""
  Item: {sanitized_order.get('itemNo', 'N/A')} - {sanitized_order.get('itemDescription', 'N/A')}
  Quantity: {sanitized_order.get('quantity', 'N/A')} {sanitized_order.get('unit', '')}
  Release Date: {sanitized_order.get('releaseDate', 'N/A')}
  Due Date: {sanitized_order.get('dueDate', 'N/A')}"""

    return f"""
Production Order #{sanitized_order.get('orderNo', 'N/A')}
  Customer Order: {sanitized_order.get('customerOrderNo', 'N/A')}
  Customer: {sanitized_order.get('customerName', 'N/A')} ({sanitized_order.get('customerNo', 'N/A')})
  Status: {status_info}{details_info}
"""
