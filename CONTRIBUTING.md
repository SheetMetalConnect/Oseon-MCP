# Contributing

Thanks for your interest! This project demonstrates MCP server development for manufacturing systems.

## Development Setup

```bash
# Clone and install
git clone https://github.com/SheetMetalConnect/Oseon-MCP.git
cd Oseon-MCP
uv sync --dev

# Configure
cp env.example .env
# Edit .env with your Oseon server details

# Run tests
uv run python tests/test_unified_system.py

# Format code
uv run black src/ tests/
```

## Project Structure

```
src/trumpf_oseon_mcp/
├── __main__.py           # MCP server entry point
├── config.py             # Configuration
├── api/
│   └── client.py         # OseonAPIClient - HTTP client
├── models/
│   └── schemas.py        # Data models and types
├── utils/
│   ├── filters.py        # Quality filtering
│   ├── formatters.py     # Display formatting
│   └── pagination.py     # Pagination utilities
└── tools/
    ├── customer_orders.py   # Customer order tools
    ├── production_orders.py # Production order tools
    └── dashboards.py        # Dashboard tools
```

## Adding a New Tool

1. **Choose the right module:**
   - Customer orders → `tools/customer_orders.py`
   - Production orders → `tools/production_orders.py`
   - Quick analysis → `tools/dashboards.py`

2. **Create the function:**
```python
async def my_new_tool(
    client: OseonAPIClient,
    param1: str,
    param2: int = 50
) -> str:
    """Tool description.
    
    Args:
        client: API client
        param1: Parameter description
        param2: Optional parameter
        
    Returns:
        Formatted results
    """
    # Implementation
    pass
```

3. **Register in `__main__.py`:**
```python
@mcp.tool()
async def my_new_tool(param1: str, param2: int = 50) -> str:
    """User-facing description."""
    return await tools.module.my_new_tool(
        client=api_client,
        param1=param1,
        param2=param2
    )
```

## Guidelines

**Code Style:**
- Use `black` for formatting
- Type hints required
- Async functions for API calls
- Descriptive docstrings

**Tool Design:**
- Read-only operations only
- Pagination by default (max 50/page)
- Quality filtering enabled
- Clear, concise output

**Testing:**
- Test with real API when possible
- Validate parameter handling
- Check error cases

## Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-tool`)
3. Make your changes
4. Run tests and formatting
5. Commit with clear message
6. Push and open a PR

## Questions?

Open an issue or contact [Luke van Enkhuizen](https://vanenkhuizen.com)

## License

MIT - See [LICENSE](LICENSE) file
