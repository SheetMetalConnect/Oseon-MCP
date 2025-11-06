"""Custom exceptions for TRUMPF Oseon MCP Server.

Provides specific exception types for better error handling and user feedback.
"""


class OseonError(Exception):
    """Base exception for all Oseon-related errors."""
    pass


class OseonAPIError(OseonError):
    """Base exception for API-related errors."""
    pass


class OseonConnectionError(OseonAPIError):
    """Raised when connection to Oseon API fails."""
    pass


class OseonAuthenticationError(OseonAPIError):
    """Raised when authentication with Oseon API fails."""
    pass


class OseonNotFoundError(OseonAPIError):
    """Raised when requested resource is not found (404)."""
    pass


class OseonRateLimitError(OseonAPIError):
    """Raised when API rate limit is exceeded (429)."""
    pass


class OseonServerError(OseonAPIError):
    """Raised when Oseon server returns 5xx error."""
    pass


class OseonValidationError(OseonError):
    """Raised when input validation fails."""
    pass


class OseonConfigurationError(OseonError):
    """Raised when configuration is invalid or missing."""
    pass
