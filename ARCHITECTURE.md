# TRUMPF Oseon MCP Server - Modular Architecture v2.0

## Overview

This document describes the refactored modular architecture of the TRUMPF Oseon MCP Server v2.0. The refactoring focuses on:

- **Modularity**: Separation of concerns with distinct modules
- **Best Practices**: Following MCP server development best practices
- **Read-Only Operations**: All operations are read-only with no update capabilities
- **Pagination**: Comprehensive pagination support for efficient data fetching
- **Secondary Features**: Dashboard tools as demo/quick analysis features

## Architecture

### Directory Structure

```
src/trumpf_oseon_mcp/
├── __init__.py                 # Package initialization and exports
├── __main__.py                 # Main MCP server entry point
├── config.py                   # Configuration management
├── api/
│   ├── __init__.py
│   └── client.py              # OseonAPIClient - HTTP client for Oseon API
├── models/
│   ├── __init__.py
│   └── schemas.py             # Data models and type definitions
├── utils/
│   ├── __init__.py
│   ├── filters.py             # Data filtering and quality checks
│   ├── formatters.py          # Display formatting functions
│   └── pagination.py          # Pagination utilities
└── tools/
    ├── __init__.py
    ├── customer_orders.py     # Customer order tools (primary)
    ├── production_orders.py   # Production order tools (primary)
    └── dashboards.py          # Dashboard tools (secondary/demo)
```

## Module Descriptions

### 1. API Client (`api/client.py`)

**Purpose**: Centralized HTTP client for all Oseon API communication.

**Key Class**: `OseonAPIClient`

**Features**:
- Basic authentication handling
- Async HTTP requests with proper error handling
- Dedicated methods for customer orders and production orders
- Configurable timeouts
- Comprehensive logging

**Example**:
```python
from trumpf_oseon_mcp.api.client import OseonAPIClient

client = OseonAPIClient(config)
result = await client.get_customer_orders(params)
```

### 2. Models (`models/schemas.py`)

**Purpose**: Type definitions and data models for API responses.

**Key Components**:
- `CustomerOrder`: Customer order structure
- `ProductionOrder`: Production order structure
- `OrderStatus`: Status constants and categorization
- `APIResponse`: Standard API response structure

**Features**:
- TypedDict definitions for better IDE support
- Status categorization (NEWEST, RELEASED, COMPLETED)
- Helper methods for status checking

### 3. Utilities

#### 3.1 Filters (`utils/filters.py`)

**Purpose**: Data filtering and quality validation.

**Key Functions**:
- `get_default_since_date()`: Dynamic 12-month date calculation
- `is_quality_production_data()`: Filter template/test orders
- `filter_quality_orders()`: Batch filtering
- `is_order_overdue()`: Overdue detection
- `sanitize_for_demo()`: Demo mode data sanitization

#### 3.2 Formatters (`utils/formatters.py`)

**Purpose**: Format data for human-readable display.

**Key Functions**:
- `format_customer_order()`: Format customer orders with status context
- `format_production_order()`: Format production orders with business context

#### 3.3 Pagination (`utils/pagination.py`)

**Purpose**: Pagination and parameter building utilities.

**Key Functions**:
- `get_unified_api_params()`: Unified parameter building
- `calculate_recent_page_params()`: Smart pagination for recent records
- `get_standard_customer_order_params()`: Customer order parameters
- `get_standard_production_order_params()`: Production order parameters

### 4. Tools

#### 4.1 Customer Orders (`tools/customer_orders.py`)

**Purpose**: Primary customer order management tools (read-only).

**Key Functions**:
- `get_customer_orders()`: Main fetch with pagination
- `get_customer_order_details()`: Single order details
- `search_customer_orders()`: Search with wildcards
- `get_customer_orders_by_status()`: Filter by status
- `get_orders_for_customer()`: Customer-specific orders

**Features**:
- Auto-pagination (up to 200 records)
- Quality filtering by default
- 12-month recent data by default
- Comprehensive search capabilities

#### 4.2 Production Orders (`tools/production_orders.py`)

**Purpose**: Primary production order management tools (read-only).

**Key Functions**:
- `get_production_orders()`: Main fetch with pagination
- `search_production_orders()`: Search functionality
- `get_in_progress_production_orders()`: Status: STARTED (40)
- `get_released_production_orders()`: Status: RELEASED (30)
- `get_finished_production_orders()`: Status: FINISHED (90)
- `get_overdue_production_orders()`: Overdue detection

**Status Codes**:
- 0: INVALID
- 10: VALID
- 20: PENDING
- 30: RELEASED
- 40: STARTED
- 90: FINISHED
- 95: COMPLETED

#### 4.3 Dashboards (`tools/dashboards.py`)

**Purpose**: Secondary/demo features for quick analysis.

**Key Functions**:
- `get_production_summary()`: Production overview dashboard
- `get_orders_summary()`: Customer orders overview dashboard

**Note**: These are demo features. For detailed data, use the specific order tools with pagination.

## Main Entry Point (`__main__.py`)

The main entry point registers all MCP tools and initializes the server:

**Structure**:
1. Configuration loading
2. API client initialization
3. Tool registration with `@mcp.tool()` decorators
4. Server startup via `mcp.run(transport="stdio")`

**Tools Exposed**:
- 6 customer order tools (primary)
- 7 production order tools (primary)
- 2 dashboard tools (secondary)

Total: 15 MCP tools

## Design Principles

### 1. Read-Only Operations

All operations are strictly read-only. No update, create, or delete operations are exposed.

**Rationale**:
- Safety: Prevents accidental data modification
- Simplicity: Easier to secure and validate
- Focus: Aligns with primary use case (order lookup and analysis)

### 2. Pagination by Default

All data fetching operations support pagination with sensible defaults.

**Default Behavior**:
- Page size: 50 (API maximum)
- Auto-pagination: Up to 200 records for customer orders
- Smart pagination: Fetch recent records efficiently

### 3. Quality Filtering

Automatic filtering of template and test orders.

**Filters Applied**:
- Future dates (>5 years)
- Test patterns in order numbers/descriptions
- Template customer names
- Year 5000+ dates

### 4. Recent Data by Default

12-month rolling window by default (configurable).

**Options**:
- `auto_filter_recent=True`: Default 12-month filter
- `since_date`: Custom date filter
- `include_all_data=True`: Access all historical data

### 5. Unified System

Consistent behavior across all tools:
- Same sorting (modificationDate, desc)
- Same filtering logic
- Same parameter naming
- Same error handling

## Configuration

Configuration via environment variables (`.env` file):

```bash
OSEON_BASE_URL=http://your-oseon-server:8999
OSEON_USERNAME=your-username
OSEON_PASSWORD=your-password
OSEON_USER_HEADER=your-user
OSEON_TERMINAL_HEADER=your-terminal
OSEON_API_VERSION=2.0
```

## Usage Examples

### Fetch Customer Orders

```python
# Default: Recent 12 months, auto-paginated
result = await get_customer_orders()

# Filter by status
result = await get_customer_orders(status="COMPLETED")

# Search with pagination
result = await search_customer_orders(
    search_term="Order%",
    page=1,
    size=50
)

# All historical data
result = await get_customer_orders(include_all_data=True)
```

### Fetch Production Orders

```python
# Default: Recent 12 months
result = await get_production_orders()

# In-progress orders
result = await get_in_progress_production_orders()

# Released orders
result = await get_released_production_orders()

# Overdue orders
result = await get_overdue_production_orders()
```

### Dashboard Analysis (Demo)

```python
# Quick production summary (last 7 days)
result = await get_production_summary(days_back=7)

# Quick customer orders summary
result = await get_orders_summary(days_back=7)
```

## Testing

Run the validation tests:

```bash
# Test unified system
python tests/test_unified_system.py
```

The tests validate:
- Dynamic date filtering
- Unified API parameters
- Quality filtering
- API connectivity
- Issue resolution

## Migration from v1.0

**Breaking Changes**:
- Old `make_oseon_request()` is now internal to `OseonAPIClient`
- Functions moved to separate modules (import paths changed)
- Some utility functions are now methods or in utils modules

**Migration Guide**:

Old:
```python
from trumpf_oseon_mcp.__main__ import make_oseon_request
result = await make_oseon_request(endpoint, params)
```

New:
```python
from trumpf_oseon_mcp.api.client import OseonAPIClient
client = OseonAPIClient(config)
result = await client.get_customer_orders(params)
```

## Future Enhancements

Potential future improvements:
- [ ] Caching layer for frequently accessed data
- [ ] Webhooks for real-time updates (if required)
- [ ] Advanced analytics dashboards
- [ ] Export functionality (CSV, Excel)
- [ ] Batch operations optimization
- [ ] GraphQL API support

## Changelog

### v2.0.0 (Current)
- ✅ Modular architecture with separate modules
- ✅ Dedicated API client
- ✅ Type definitions and data models
- ✅ Comprehensive pagination support
- ✅ Read-only operations focus
- ✅ Dashboard tools as secondary features
- ✅ Quality filtering by default
- ✅ Unified system parameters

### v1.0.0
- Initial monolithic implementation
- All code in single `__main__.py` file
- 29 tools with mixed concerns
