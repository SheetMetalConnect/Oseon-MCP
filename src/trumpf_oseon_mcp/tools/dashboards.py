"""Dashboard tools for TRUMPF Oseon MCP Server.

This module provides demo dashboard tools for quick production analysis.
These are secondary features meant to demonstrate quick analysis capabilities.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any

from ..api.client import OseonAPIClient
from ..models.schemas import OrderStatus
from ..utils.filters import filter_quality_orders


async def get_production_summary(
    client: OseonAPIClient,
    days_back: int = 7,
    demo_mode: bool = False
) -> str:
    """Get a quick production summary dashboard.

    This is a demo feature to show how to quickly analyze production data.

    Args:
        client: OseonAPIClient instance
        days_back: Number of days to look back (default: 7)
        demo_mode: If True, sanitizes customer data for demos (default: False)

    Returns:
        Formatted production summary dashboard
    """
    try:
        # Calculate date range
        since_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")

        # Fetch production orders
        params = {
            "size": 50,
            "page": 0,
            "since": since_date,
            "sortBy": "modificationDate",
            "sortOrder": "desc"
        }

        result = await client.get_production_orders(params)

        if not result.get("collection"):
            return f"No production data found for the last {days_back} days."

        orders = result["collection"]
        orders = filter_quality_orders(orders)

        if not orders:
            return f"No production data found for the last {days_back} days (after quality filtering)."

        # Analyze data
        total_orders = len(orders)
        status_counts: Dict[str, int] = {}
        customer_counts: Dict[str, int] = {}

        for order in orders:
            status = str(order.get("status", "UNKNOWN"))
            status_category = OrderStatus.get_category(status)
            status_counts[status_category] = status_counts.get(status_category, 0) + 1

            if not demo_mode:
                customer = order.get("customerName", "Unknown")
                customer_counts[customer] = customer_counts.get(customer, 0) + 1

        # Build dashboard
        response = f"""
╔═══════════════════════════════════════════════════════════╗
║           PRODUCTION SUMMARY DASHBOARD                   ║
║           Last {days_back} days                                      ║
╚═══════════════════════════════════════════════════════════╝

📊 OVERVIEW:
   Total Orders: {total_orders}
   Data Quality: Filtered for production data only

📈 STATUS BREAKDOWN:
"""

        for status_category, count in sorted(status_counts.items()):
            percentage = (count / total_orders * 100) if total_orders > 0 else 0
            response += f"   {status_category}: {count} ({percentage:.1f}%)\n"

        if not demo_mode and customer_counts:
            response += "\n👥 TOP CUSTOMERS:\n"
            sorted_customers = sorted(customer_counts.items(), key=lambda x: x[1], reverse=True)
            for customer, count in sorted_customers[:5]:
                response += f"   {customer}: {count} orders\n"

        response += "\n💡 NOTE: This is a demo dashboard for quick production analysis.\n"
        response += "   Use specific tools for detailed order information and pagination.\n"

        return response

    except Exception as e:
        return f"Error generating production summary: {str(e)}"


async def get_orders_summary(
    client: OseonAPIClient,
    days_back: int = 7,
    demo_mode: bool = False
) -> str:
    """Get a quick customer orders summary dashboard.

    This is a demo feature to show how to quickly analyze customer order data.

    Args:
        client: OseonAPIClient instance
        days_back: Number of days to look back (default: 7)
        demo_mode: If True, sanitizes customer data for demos (default: False)

    Returns:
        Formatted customer orders summary dashboard
    """
    try:
        # Calculate date range
        since_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")

        # Fetch customer orders
        params = {
            "size": 50,
            "page": 0,
            "since": since_date,
            "sortBy": "modificationDate",
            "sortOrder": "desc"
        }

        result = await client.get_customer_orders(params)

        if not result.get("collection"):
            return f"No customer order data found for the last {days_back} days."

        orders = result["collection"]
        orders = filter_quality_orders(orders)

        if not orders:
            return f"No customer order data found for the last {days_back} days (after quality filtering)."

        # Analyze data
        total_orders = len(orders)
        status_counts: Dict[str, int] = {}
        customer_counts: Dict[str, int] = {}
        total_value = 0.0

        for order in orders:
            status = order.get("status", "UNKNOWN")
            status_category = OrderStatus.get_category(status)
            status_counts[status_category] = status_counts.get(status_category, 0) + 1

            if not demo_mode:
                customer = order.get("customerName", "Unknown")
                customer_counts[customer] = customer_counts.get(customer, 0) + 1

            # Calculate order value if positions are available
            if order.get("positions"):
                for pos in order["positions"]:
                    price = pos.get("netPricePerUnit", 0)
                    qty = pos.get("targetQuantity", 0)
                    total_value += price * qty

        # Build dashboard
        response = f"""
╔═══════════════════════════════════════════════════════════╗
║         CUSTOMER ORDERS SUMMARY DASHBOARD                ║
║           Last {days_back} days                                      ║
╚═══════════════════════════════════════════════════════════╝

📊 OVERVIEW:
   Total Orders: {total_orders}
   Total Value: €{total_value:,.2f}
   Data Quality: Filtered for production data only

📈 STATUS BREAKDOWN:
"""

        for status_category, count in sorted(status_counts.items()):
            percentage = (count / total_orders * 100) if total_orders > 0 else 0
            response += f"   {status_category}: {count} ({percentage:.1f}%)\n"

        if not demo_mode and customer_counts:
            response += "\n👥 TOP CUSTOMERS:\n"
            sorted_customers = sorted(customer_counts.items(), key=lambda x: x[1], reverse=True)
            for customer, count in sorted_customers[:5]:
                response += f"   {customer}: {count} orders\n"

        response += "\n💡 NOTE: This is a demo dashboard for quick analysis.\n"
        response += "   Use specific tools for detailed order information and pagination.\n"

        return response

    except Exception as e:
        return f"Error generating customer orders summary: {str(e)}"
