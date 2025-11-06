# Architecture

Modular MCP server v2.0 for TRUMPF Oseon API.

## Structure

```
src/trumpf_oseon_mcp/
├── __main__.py               # MCP server entry (15 tools registered)
├── config.py                 # Environment configuration
├── api/
│   └── client.py            # OseonAPIClient - HTTP client
├── models/
│   └── schemas.py           # Type definitions (OrderStatus, CustomerOrder, ProductionOrder)
├── utils/
│   ├── filters.py           # Quality filtering, overdue detection
│   ├── formatters.py        # Display formatting
│   └── pagination.py        # Parameter building, smart pagination
└── tools/
    ├── customer_orders.py   # 6 customer order tools
    ├── production_orders.py # 7 production order tools
    └── dashboards.py        # 2 dashboard tools (demo)
```

## Key Components

### API Client (`api/client.py`)

Centralized HTTP client for all Oseon API communication.

```python
client = OseonAPIClient(config)
result = await client.get_customer_orders(params)
result = await client.get_production_orders(params)
```

**Features:** Basic auth, async requests, error handling, logging

### Models (`models/schemas.py`)

Type definitions for API responses.

- `CustomerOrder`, `ProductionOrder` - Order structures
- `OrderStatus` - Status constants and categorization (NEWEST, RELEASED, COMPLETED)
- `APIResponse` - Standard response format

### Utils

**Filters (`utils/filters.py`):**
- `get_default_since_date()` - Dynamic 12-month window
- `is_quality_production_data()` - Filter template/test orders
- `is_order_overdue()` - Overdue detection
- `sanitize_for_demo()` - Demo mode sanitization

**Formatters (`utils/formatters.py`):**
- `format_customer_order()` - Human-readable customer orders
- `format_production_order()` - Human-readable production orders

**Pagination (`utils/pagination.py`):**
- `get_unified_api_params()` - Unified parameter building
- `calculate_recent_page_params()` - Smart pagination for recent records

### Tools

**Customer Orders (6 tools):**
- `get_customer_orders()` - Main fetch with auto-pagination (up to 200 records)
- `get_customer_order_details()` - Single order details
- `search_customer_orders()` - Search with wildcards
- `get_customer_orders_by_status()` - Filter by status
- `get_orders_for_customer()` - Customer-specific orders

**Production Orders (7 tools):**
- `get_production_orders()` - Main fetch with pagination
- `search_production_orders()` - Search functionality
- `get_in_progress_production_orders()` - Status: STARTED (40)
- `get_released_production_orders()` - Status: RELEASED (30)
- `get_finished_production_orders()` - Status: FINISHED (90)
- `get_overdue_production_orders()` - Overdue detection

**Status Codes:** 0=INVALID, 10=VALID, 20=PENDING, 30=RELEASED, 40=STARTED, 90=FINISHED, 95=COMPLETED

**Dashboards (2 tools):**
- `get_production_summary()` - Quick production overview (7 days)
- `get_orders_summary()` - Quick customer orders overview (7 days)

*Note: Dashboards are demo/secondary features. Use specific order tools for detailed data.*

## Design Principles

1. **Read-Only** - No updates/deletes, safe for production
2. **Pagination** - Default 50/page (API max), auto-pagination for customer orders
3. **Quality Filtering** - Excludes templates/tests by default
4. **Recent Data** - 12-month rolling window (configurable)
5. **Unified System** - Consistent sorting, filtering, error handling

## Configuration

Environment variables (`.env`):

```bash
OSEON_BASE_URL=http://your-oseon-server:8999
OSEON_USERNAME=your-username
OSEON_PASSWORD=your-password
OSEON_USER_HEADER=your-user
OSEON_TERMINAL_HEADER=your-terminal
OSEON_API_VERSION=2.0
```

## Data Flow

```
User Question → Claude Desktop → MCP Server (__main__.py)
    ↓
Tool Function (tools/*.py)
    ↓
Utils (filters, formatters, pagination)
    ↓
OseonAPIClient (api/client.py)
    ↓
TRUMPF Oseon API
```

## Adding a Tool

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guide.

Quick version:
1. Add function to appropriate `tools/*.py` module
2. Register in `__main__.py` with `@mcp.tool()` decorator
3. Use utils for filtering, formatting, pagination
4. Test with real API

## Migration from v1.0

v1.0 had 29 tools in single file. v2.0 has 15 tools across modules.

**Breaking changes:**
- Import paths changed (functions moved to modules)
- `make_oseon_request()` replaced by `OseonAPIClient`
- Some tools consolidated for clarity

**Migration:**
```python
# Old v1.0
from trumpf_oseon_mcp.__main__ import make_oseon_request

# New v2.0
from trumpf_oseon_mcp.api.client import OseonAPIClient
client = OseonAPIClient(config)
```
