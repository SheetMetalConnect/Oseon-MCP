# 🏭 TRUMPF Oseon MCP Server

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![MCP](https://img.shields.io/badge/MCP-1.2.0+-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

**Connect Claude AI to your TRUMPF Oseon manufacturing system. Ask questions in natural language, get real-time production insights.**

## Quick Start

**Requirements:** Python 3.10+, [Claude Desktop](https://claude.ai/download), TRUMPF Oseon API access

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# or: irm https://astral.sh/uv/install.ps1 | iex  # Windows

# Setup
git clone https://github.com/SheetMetalConnect/Oseon-MCP.git
cd Oseon-MCP
uv sync

# Configure
cp env.example .env
# Edit .env with your Oseon server details

# Install to Claude Desktop
uv run mcp install -m trumpf_oseon_mcp --name "TRUMPF Oseon"
```

**Test:** Open Claude Desktop and ask: *"Show me today's production status"*

## What You Can Ask

**Orders & Production:**
- *"Show me order 400139 with its production jobs"*
- *"What orders are overdue?"*
- *"Find all orders for customer ACME"*

**Analysis:**
- *"What's in production right now?"*
- *"Show me completed orders this week"*
- *"Which orders are released but not started?"*

**Dashboards:**
- *"Give me a production summary for the last 7 days"*

## Features

- **✅ Read-Only** - Safe, no data modifications
- **📄 Pagination** - Efficient handling of large datasets
- **🔍 Quality Filtering** - Excludes template/test orders
- **📅 Smart Defaults** - 12-month rolling window
- **🎯 15 Tools** - Customer orders, production orders, dashboards

## Architecture

```
src/trumpf_oseon_mcp/
├── api/          # HTTP client
├── models/       # Data types
├── utils/        # Filters, formatters, pagination
└── tools/        # MCP tools (customer_orders, production_orders, dashboards)
```

**Key Components:**
- **OseonAPIClient**: Centralized HTTP client for Oseon API
- **Customer Orders**: 6 read-only tools with pagination
- **Production Orders**: 7 read-only tools with status filtering
- **Dashboards**: 2 demo tools for quick analysis

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design.

## Examples

```python
# Get customer orders (auto-paginated, last 12 months)
get_customer_orders()

# Search orders
search_customer_orders(search_term="ACME%")

# Filter by status
get_customer_orders_by_status(status="COMPLETED")

# Get production orders in progress
get_in_progress_production_orders()

# Quick dashboard
get_production_summary(days_back=7)
```

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup.

```bash
# Install with dev dependencies
uv sync --dev

# Run tests
uv run python tests/test_unified_system.py
```

## How It Works

```
[TRUMPF Oseon] --> [MCP Server (local)] --> [Claude Desktop]
                         ↓
                  Your Credentials
                  Read-Only Access
```

**Privacy:** MCP server runs locally. Only chat messages go to Claude; your manufacturing data stays on your network.

## About

Built by [Luke van Enkhuizen](https://vanenkhuizen.com) to demonstrate AI + manufacturing integration.

**No TRUMPF affiliation** - Educational project using public API documentation.

**MIT License** - Use freely | **v2.0.0** - Modular architecture
