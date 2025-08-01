# TRUMPF Oseon MCP Tools

This folder contains utility scripts for managing the TRUMPF Oseon MCP server.

## Scripts

### `launch_mcp.sh`
Main launcher script for the MCP server with full process management.

**Usage:**
```bash
./tools/launch_mcp.sh [OPTION]
```

**Options:**
- `--build` - Build/rebuild the project (install dependencies)
- `--start` - Start the MCP server
- `--stop` - Stop the MCP server
- `--restart` - Restart the MCP server
- `--status` - Show server status
- `--logs` - Show recent server logs
- `--help` - Show help message

### `raycast_mcp.sh`
Raycast-compatible script for quick MCP server management.

**Usage:**
```bash
./tools/raycast_mcp.sh [action]
```

**Actions:**
- `start` - Start the MCP server
- `stop` - Stop the MCP server
- `restart` - Restart the MCP server
- `status` - Show server status
- `logs` - Show recent logs
- `build` - Build the project

## Examples

```bash
# First time setup
./tools/launch_mcp.sh --build --restart

# Daily usage
./tools/launch_mcp.sh --start    # Start server
./tools/launch_mcp.sh --status   # Check if running
./tools/launch_mcp.sh --stop     # Stop server

# Raycast integration
./tools/raycast_mcp.sh start     # Start via Raycast
./tools/raycast_mcp.sh status    # Check status via Raycast
``` 