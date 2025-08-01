# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-31

### Added
- Initial release of TRUMPF Oseon MCP Server (proof of concept)
- 7 basic customer order tools:
  - `get_customer_orders` - Paginated orders with filtering
  - `get_customer_order_details` - Detailed order information
  - `search_customer_orders` - Search by order number/reference
  - `get_orders_by_status` - Filter by order status
  - `get_orders_by_customer` - Customer-specific order lists
  - `get_recent_orders` - Date-based filtering
  - `get_orders_by_item` - Find orders containing specific items
- Environment-based configuration management
- Basic error handling and logging
- Basic Authentication with TRUMPF Oseon API v2
- Documentation and setup instructions
- Test suite for server validation
- Claude for Desktop integration templates

### Features
- Efficient API usage with smart filtering
- Rich formatted output with pricing and details
- Secure credential management via environment variables
- Cross-platform compatibility (macOS, Linux, Windows)
- Basic logging for debugging

### Documentation
- README with installation and usage instructions
- API endpoint documentation
- Basic troubleshooting guide
- Example queries and use cases