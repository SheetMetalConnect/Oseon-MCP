# Development Guide

**Setup, architecture, and how to extend the server.**

## Setup

Follow the main README quickstart, then:

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Code formatting
uv run black src/ tests/
```

## Project Structure

```
trumpf-oseon-mcp/
├── src/
│   └── trumpf_oseon_mcp/
│       ├── __init__.py           # Package initialization
│       ├── __main__.py           # Main MCP server entry point (3000+ lines)
│       └── config.py             # Configuration management
├── docs/                         # Documentation
│   ├── advanced-usage.md         # Complex workflows & bulk operations
│   ├── development.md            # This file
│   ├── launch-tools.md           # Server management scripts
│   └── tools-reference.md        # Complete command reference
├── tests/                        # Test suite
│   ├── __init__.py
│   └── test_unified_system.py    # Comprehensive system validation
├── tools/                        # Server management scripts
│   ├── launch_mcp.sh             # Main launcher with process management
│   └── raycast_mcp.sh            # Raycast integration
├── pyproject.toml               # Python packaging & dependencies
├── uv.lock                      # Locked dependencies
├── env.example                  # Environment template
├── LICENSE                      # MIT License
└── README.md                    # Beginner-friendly main documentation
```

## Core Architecture

### MCP Server Structure

The main server code is in `src/trumpf_oseon_mcp/__main__.py` and follows this pattern:

```python
import mcp.server.stdio
from mcp import types

# Server initialization
server = mcp.server.stdio.Server("trumpf-oseon")

# Tool definition pattern
@server.tool()
async def tool_name(param1: str, param2: int = 25) -> list[types.TextContent]:
    """Tool description for AI assistant."""
    try:
        # Implementation
        result = await api_call(param1, param2)
        return [types.TextContent(type="text", text=format_result(result))]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

# Server runner
if __name__ == "__main__":
    import asyncio
    asyncio.run(server.run())
```

### Configuration Management

Configuration is handled in `config.py`:

```python
from dataclasses import dataclass
import os

@dataclass
class OseonConfig:
    base_url: str
    username: str
    password: str
    user_header: str
    terminal_header: str
    api_version: str

def load_config() -> OseonConfig:
    return OseonConfig(
        base_url=os.getenv("OSEON_BASE_URL", "http://localhost:8999"),
        username=os.getenv("OSEON_USERNAME", ""),
        password=os.getenv("OSEON_PASSWORD", ""),
        user_header=os.getenv("OSEON_USER_HEADER", ""),
        terminal_header=os.getenv("OSEON_TERMINAL_HEADER", ""),
        api_version=os.getenv("OSEON_API_VERSION", "2.0")
    )
```

## Adding New Tools

### Basic Tool Template

```python
@server.tool()
async def new_tool_name(
    required_param: str,
    optional_param: int = 25,
    filter_param: str = None
) -> list[types.TextContent]:
    """
    Brief description of what this tool does.
    
    Args:
        required_param: Description of required parameter
        optional_param: Description with default value
        filter_param: Optional filter description
    """
    try:
        # Validate inputs
        if not required_param:
            raise ValueError("required_param cannot be empty")
        
        # Build API request
        url = f"{config.base_url}/api/v2/endpoint"
        params = {
            "param1": required_param,
            "size": optional_param
        }
        
        if filter_param:
            params["filter"] = filter_param
        
        # Make API call
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                auth=aiohttp.BasicAuth(config.username, config.password),
                headers={
                    "Trumpf-User": config.user_header,
                    "Trumpf-Terminal": config.terminal_header,
                    "Accept": "application/json"
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Format response
                    result = format_new_tool_response(data)
                    return [types.TextContent(type="text", text=result)]
                else:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
                    
    except Exception as e:
        return [types.TextContent(
            type="text", 
            text=f"Error in new_tool_name: {str(e)}"
        )]

def format_new_tool_response(data: dict) -> str:
    """Format the API response for display."""
    # Implementation specific to your tool
    pass
```

### Tool Development Guidelines

1. **Error Handling**: Always wrap in try/catch and return helpful error messages
2. **Parameter Validation**: Validate inputs before making API calls
3. **Documentation**: Include comprehensive docstrings for the AI assistant
4. **Formatting**: Create helper functions for consistent response formatting
5. **Authentication**: Use the standard auth pattern with TRUMPF headers

### API Endpoint Patterns

Current endpoints follow these patterns:

```python
# Customer Orders
customer_orders_url = f"{base_url}/api/v2/sales/customerOrders"
customer_order_details_url = f"{base_url}/api/v2/sales/customerOrders/{order_no}"

# Production Orders
production_orders_url = f"{base_url}/api/v2/pps/productionOrders/full/search"

# Standard headers
headers = {
    "Trumpf-User": config.user_header,
    "Trumpf-Terminal": config.terminal_header,
    "Accept": "application/json"
}

# Standard auth
auth = aiohttp.BasicAuth(config.username, config.password)
```

## Testing

### Test Structure

Tests are in the `tests/` directory and use pytest:

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from src.trumpf_oseon_mcp.__main__ import get_customer_orders

@pytest.mark.asyncio
async def test_get_customer_orders():
    """Test customer orders retrieval."""
    # Mock the API response
    mock_response = {
        "content": [
            {"orderNo": "ORDER123", "customerName": "Test Customer"}
        ],
        "totalPages": 1,
        "totalElements": 1
    }
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
        
        result = await get_customer_orders()
        
        assert len(result) == 1
        assert "ORDER123" in result[0].text
        assert "Test Customer" in result[0].text
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_mcp_server.py -v

# Run with coverage
pytest --cov=src tests/
```

## Debugging

### Local Development

```bash
# Run with debug output
DEBUG=1 uv run mcp dev -m trumpf_oseon_mcp

# Test specific tool
echo '{"method": "tools/call", "params": {"name": "get_customer_orders", "arguments": {}}}' | \
uv run python -m trumpf_oseon_mcp
```

### Claude Desktop Integration

1. **Check Claude Desktop logs**:
   - macOS: `~/Library/Logs/Claude/`
   - Windows: `%APPDATA%\Claude\logs\`

2. **Verify configuration**:
   ```json
   {
     "mcpServers": {
       "trumpf-oseon": {
         "command": "uv",
         "args": [
           "--directory",
           "/absolute/path/to/project",
           "run",
           "python",
           "-m",
           "trumpf_oseon_mcp"
         ]
       }
     }
   }
   ```

3. **Test connection**:
   - Restart Claude Desktop after config changes
   - Check for connection errors in Claude chat
   - Verify environment variables are accessible

## Contributing

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and returns
- Include comprehensive docstrings
- Format with `black` and lint with `flake8`

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with tests
4. Run the full test suite: `make test`
5. Submit a pull request with description

### Adding API Endpoints

When adding support for new TRUMPF Oseon API endpoints:

1. **Study the Swagger documentation** in `resources/Swagger-API-Oseon-v2.json`
2. **Follow existing patterns** for authentication and error handling
3. **Add comprehensive tools** covering common use cases
4. **Include bulk operations** for large datasets where applicable
5. **Add cross-system linking** if the endpoint relates to existing data

## Release Process

```bash
# Update version in pyproject.toml
# Create release commit
git add .
git commit -m "Release v1.x.x"
git tag v1.x.x
git push origin main --tags

# Build and publish
make build
make publish
```

## Architecture Decisions

### Why MCP?
- Direct AI assistant integration
- Type-safe tool definitions
- Standardized communication protocol
- Future compatibility with multiple AI platforms

### Why Async?
- Non-blocking API calls
- Better performance for bulk operations
- Scalable to multiple concurrent requests

### Why TRUMPF Headers?
- Required by Oseon API for user identification
- Enables audit trails in Oseon system
- Supports multi-user environments