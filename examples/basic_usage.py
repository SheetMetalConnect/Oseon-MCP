#!/usr/bin/env python3
"""
Basic usage examples for TRUMPF Oseon MCP Server.

This demonstrates how to use the tools programmatically.
For Claude Desktop integration, just ask questions naturally.
"""

import asyncio
from trumpf_oseon_mcp.api.client import OseonAPIClient
from trumpf_oseon_mcp.config import get_config
from trumpf_oseon_mcp.tools import customer_orders, production_orders, dashboards


async def main():
    """Run basic examples."""
    
    # Initialize API client
    config = get_config()
    client = OseonAPIClient(config)
    
    print("=" * 60)
    print("TRUMPF Oseon MCP Server - Basic Examples")
    print("=" * 60)
    
    # Example 1: Get customer orders (recent 12 months, auto-paginated)
    print("\n1. Get customer orders (last 12 months):")
    result = await customer_orders.get_customer_orders(
        client=client,
        size=10,  # 10 per page
        auto_paginate=False  # Just one page for demo
    )
    print(result[:500] + "..." if len(result) > 500 else result)
    
    # Example 2: Search for specific customer
    print("\n2. Search for orders by customer:")
    result = await customer_orders.search_customer_orders(
        client=client,
        search_term="ACME%",  # Wildcard search
        size=5
    )
    print(result[:500] + "..." if len(result) > 500 else result)
    
    # Example 3: Get production orders in progress
    print("\n3. Get in-progress production orders:")
    result = await production_orders.get_in_progress_production_orders(
        client=client,
        size=5
    )
    print(result[:500] + "..." if len(result) > 500 else result)
    
    # Example 4: Quick dashboard
    print("\n4. Production summary (last 7 days):")
    result = await dashboards.get_production_summary(
        client=client,
        days_back=7
    )
    print(result)
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
