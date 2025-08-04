"""Configuration management for TRUMPF Oseon MCP Server"""

import os
from typing import Dict, Any

def get_config() -> Dict[str, Any]:
    """Get configuration from environment variables with fallback defaults."""
    return {
        "base_url": os.getenv("OSEON_BASE_URL", "http://your-oseon-server:8999"),
        "api_version": os.getenv("OSEON_API_VERSION", "2.0"),
        "username": os.getenv("OSEON_USERNAME", "your-username"),
        "password": os.getenv("OSEON_PASSWORD", "your-password"),
        "default_headers": {
            "Trumpf-User": os.getenv("OSEON_USER_HEADER", "your-user"),
            "Trumpf-Terminal": os.getenv("OSEON_TERMINAL_HEADER", "your-terminal"),
            "Accept": "application/json",
            "api-version": os.getenv("OSEON_API_VERSION", "2.0")
        }
    }

