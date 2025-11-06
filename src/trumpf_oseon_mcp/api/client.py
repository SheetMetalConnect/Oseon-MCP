"""TRUMPF Oseon API Client

This module provides a clean, async HTTP client for interacting with the TRUMPF Oseon API v2.
Handles authentication, request construction, and error handling.
"""

import base64
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class OseonAPIClient:
    """Async HTTP client for TRUMPF Oseon API v2.

    Provides methods for making authenticated requests to the Oseon API endpoints.
    Supports customer orders and production orders endpoints.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the Oseon API client.

        Args:
            config: Configuration dictionary containing:
                - base_url: Base URL of the Oseon API
                - username: API username
                - password: API password
                - default_headers: Default headers to include in requests
        """
        self.config = config
        self.base_url = config['base_url']
        self.username = config['username']
        self.password = config['password']
        self.default_headers = config['default_headers'].copy()

    def _get_auth_header(self) -> str:
        """Generate Basic Auth header for TRUMPF Oseon API.

        Returns:
            Basic authentication header string
        """
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"

    async def request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Make an authenticated GET request to the TRUMPF Oseon API.

        Args:
            endpoint: API endpoint path (e.g., "/api/v2/sales/customerOrders")
            params: Optional query parameters
            timeout: Request timeout in seconds (default: 30.0)

        Returns:
            JSON response as dictionary

        Raises:
            Exception: If the request fails or returns an error status
        """
        url = f"{self.base_url}{endpoint}"
        headers = self.default_headers.copy()
        headers["Authorization"] = self._get_auth_header()

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
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

    async def get_customer_orders(
        self,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Fetch customer orders from the Oseon API.

        Args:
            params: Query parameters for filtering and pagination

        Returns:
            API response containing customer orders data
        """
        return await self.request("/api/v2/sales/customerOrders", params)

    async def get_production_orders(
        self,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Fetch production orders from the Oseon API.

        Args:
            params: Query parameters for filtering and pagination

        Returns:
            API response containing production orders data
        """
        return await self.request("/api/v2/pps/productionOrders/full/search", params)

    async def get_customer_order_details(
        self,
        order_no: str
    ) -> Dict[str, Any]:
        """Fetch detailed information for a specific customer order.

        Args:
            order_no: Customer order number

        Returns:
            API response containing customer order details
        """
        return await self.request(f"/api/v2/sales/customerOrders/{order_no}")
