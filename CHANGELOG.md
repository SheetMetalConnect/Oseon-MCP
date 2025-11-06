# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-11-06

### Added
- Modular architecture with separate modules (api, models, utils, tools)
- Custom exception classes for better error handling
- Health check tool for connectivity monitoring
- GitHub Actions CI/CD pipeline
- Comprehensive documentation (ARCHITECTURE.md, CONTRIBUTING.md)
- GitHub templates (issue templates, PR template)
- Examples folder with basic usage
- .gitattributes for consistent file handling
- 15 MCP tools (6 customer orders, 7 production orders, 2 dashboards)

### Changed
- **BREAKING:** Moved from monolithic to modular structure
- **BREAKING:** Import paths changed (functions moved to modules)
- Simplified from 29 tools to 15 focused tools
- All operations are now read-only (removed update/delete)
- Improved error messages with specific exception types
- Enhanced logging with secret masking
- Reduced documentation by 80% (removed bloat)
- tools/ renamed to scripts/ for clarity

### Removed
- **BREAKING:** `make_oseon_request()` from public API (use `OseonAPIClient`)
- Write/update/delete operations (read-only only)
- Outdated v1.0 documentation (46KB)
- Verbose and overlapping documentation

### Fixed
- Generic exception handling replaced with specific exceptions
- Password logging (now masked)
- Inconsistent error messages

### Security
- Secrets no longer logged in plain text
- Added security scanning (bandit) to CI pipeline
- Input validation improvements

## [1.0.0] - 2024-11-05

### Added
- Initial release
- 29 MCP tools for TRUMPF Oseon API
- Basic authentication support
- Pagination support
- Quality filtering

[2.0.0]: https://github.com/SheetMetalConnect/Oseon-MCP/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/SheetMetalConnect/Oseon-MCP/releases/tag/v1.0.0
