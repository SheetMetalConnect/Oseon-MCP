"""Data models and type definitions for TRUMPF Oseon API.

This module defines the structure of data returned by the Oseon API
and provides type hints for better code maintainability.
"""

from typing import Any, Dict, List, Optional, TypedDict


class CustomerOrderPosition(TypedDict, total=False):
    """Customer order position/line item."""
    positionNo: str
    itemNo: str
    itemDescription: str
    quantity: float
    unit: str
    dueDate: str
    status: str
    price: float
    currency: str


class CustomerOrder(TypedDict, total=False):
    """Customer order from Oseon API."""
    orderNo: str
    customerNo: str
    customerName: str
    description: str
    status: str
    orderDate: str
    dueDate: str
    modificationDate: str
    positions: List[CustomerOrderPosition]
    totalValue: float
    currency: str
    priority: int


class ProductionOrderPosition(TypedDict, total=False):
    """Production order position/operation."""
    positionNo: str
    workplaceNo: str
    workplaceName: str
    operationNo: str
    operationDescription: str
    status: str
    plannedStartDate: str
    plannedEndDate: str
    actualStartDate: str
    actualEndDate: str
    quantity: float
    unit: str


class ProductionOrder(TypedDict, total=False):
    """Production order from Oseon API."""
    orderNo: str
    customerOrderNo: str
    customerNo: str
    customerName: str
    itemNo: str
    itemDescription: str
    description: str
    status: str
    orderDate: str
    releaseDate: str
    dueDate: str
    modificationDate: str
    positions: List[ProductionOrderPosition]
    quantity: float
    unit: str
    priority: int


class APIResponse(TypedDict, total=False):
    """Standard API response structure."""
    data: List[Dict[str, Any]]
    records: int
    pages: int
    page: int
    size: int


class OrderStatus:
    """Order status constants."""

    # Customer order statuses
    CUSTOMER_VALID = "VALID"
    CUSTOMER_INVALID = "INVALID"
    CUSTOMER_PENDING = "PENDING"
    CUSTOMER_RELEASED = "RELEASED"
    CUSTOMER_COMPLETED = "COMPLETED"
    CUSTOMER_DELIVERED = "DELIVERED"
    CUSTOMER_INVOICED = "INVOICED"
    CUSTOMER_CANCELED = "CANCELED"

    # Production order statuses
    PRODUCTION_VALID = "VALID"
    PRODUCTION_INVALID = "INVALID"
    PRODUCTION_PENDING = "PENDING"
    PRODUCTION_RELEASED = "RELEASED"
    PRODUCTION_STARTED = "STARTED"
    PRODUCTION_FINISHED = "FINISHED"
    PRODUCTION_COMPLETED = "COMPLETED"
    PRODUCTION_CANCELED = "CANCELED"

    @staticmethod
    def get_category(status: str) -> str:
        """Categorize order status into business-meaningful groups.

        Args:
            status: Order status string

        Returns:
            Status category: NEWEST, RELEASED, COMPLETED, or OTHER
        """
        status = status.upper() if status else ""

        # Pre-production statuses
        if status in ["INVALID", "VALID", "PENDING"]:
            return "NEWEST"

        # In-production statuses
        if status in ["RELEASED", "STARTED"]:
            return "RELEASED"

        # Post-production statuses
        if status in ["COMPLETED", "DELIVERED", "INVOICED", "FINISHED"]:
            return "COMPLETED"

        return "OTHER"

    @staticmethod
    def is_active(status: str) -> bool:
        """Check if order status indicates active/in-progress work.

        Args:
            status: Order status string

        Returns:
            True if status indicates active work
        """
        active_statuses = ["VALID", "PENDING", "RELEASED", "STARTED"]
        return status.upper() in active_statuses if status else False

    @staticmethod
    def is_completed(status: str) -> bool:
        """Check if order status indicates completion.

        Args:
            status: Order status string

        Returns:
            True if status indicates completion
        """
        completed_statuses = ["COMPLETED", "DELIVERED", "INVOICED", "FINISHED"]
        return status.upper() in completed_statuses if status else False
