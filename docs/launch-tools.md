# Launch Tools

**Scripts for server management and automation.**

## Available Scripts

### `tools/launch_mcp.sh` - Main Launcher

**Purpose:** Full-featured process management for the MCP server with background operation, logging, and status monitoring.

**Usage:**
```bash
./tools/launch_mcp.sh [OPTION]
```

**Options:**
- `--build` - Build/rebuild the project (install dependencies with uv)
- `--start` - Start the MCP server in background 
- `--stop` - Stop the MCP server gracefully
- `--restart` - Stop and restart the MCP server
- `--status` - Show current server status and process info
- `--logs` - Display recent server logs (last 50 lines)
- `--help` - Show detailed help message

**Examples:**
```bash
# First time setup and start
./tools/launch_mcp.sh --build --start

# Daily operations
./tools/launch_mcp.sh --start    # Start server
./tools/launch_mcp.sh --status   # Check if running  
./tools/launch_mcp.sh --logs     # View recent activity
./tools/launch_mcp.sh --stop     # Stop server

# Restart for updates
./tools/launch_mcp.sh --restart
```

**Features:**
- **Background Operation:** Server runs as daemon with PID tracking
- **Logging:** All output captured to `.mcp_server.log`
- **Process Management:** Safe start/stop with process validation
- **Environment Handling:** Automatic virtual environment activation
- **Colored Output:** Clear status indicators and progress

### `tools/raycast_mcp.sh` - Raycast Integration

**Purpose:** Streamlined script designed for [Raycast](https://raycast.com) integration and quick command execution.

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
- `build` - Build/rebuild the project

**Raycast Integration:**
1. Add a Raycast script command
2. Set command to: `./tools/raycast_mcp.sh`
3. Set argument handling to prompt for action
4. Now use "mcp start", "mcp status", etc. from Raycast

## Process Management Details

### File Locations
- **PID File:** `.mcp_server.pid` - Contains the background process ID
- **Log File:** `.mcp_server.log` - All server output and errors
- **Virtual Environment:** `.venv/` - Python dependencies

### Background Operation
```bash
# Server starts in background and detaches from terminal
./tools/launch_mcp.sh --start

# Check if it's actually running  
./tools/launch_mcp.sh --status
# Output: ✅ MCP Server is running (PID: 12345)

# View real-time logs
tail -f .mcp_server.log
```

### Error Handling
The scripts include comprehensive error handling for common issues:

- **Missing Dependencies:** Automatic `uv sync` when needed
- **Port Conflicts:** Detection and graceful handling
- **Process Cleanup:** Proper cleanup of hanging processes
- **Environment Issues:** Clear error messages for config problems

## Development Integration

### VS Code / Cursor Integration
Add these tasks to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Start MCP Server",
      "type": "shell",
      "command": "./tools/launch_mcp.sh --start",
      "group": "build",
      "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": false,
        "panel": "shared"
      }
    },
    {
      "label": "Stop MCP Server", 
      "type": "shell",
      "command": "./tools/launch_mcp.sh --stop",
      "group": "build"
    }
  ]
}
```

### Claude Desktop Integration
```bash
# Start server and monitor
./tools/launch_mcp.sh --start
./tools/launch_mcp.sh --logs
```

## Advanced Usage

### Production Deployment
```bash
# Set up for production use
./tools/launch_mcp.sh --build
./tools/launch_mcp.sh --start

# Add to system startup (example for systemd)
sudo cp tools/launch_mcp.sh /usr/local/bin/
sudo systemctl enable trumpf-oseon-mcp
```

### Monitoring and Logging
```bash
# Continuous log monitoring
tail -f .mcp_server.log | grep -E "(ERROR|WARN|INFO)"

# Log rotation (manual)
mv .mcp_server.log .mcp_server.log.old
./tools/launch_mcp.sh --restart

# Check server health
./tools/launch_mcp.sh --status && echo "Server healthy" || echo "Server issues"
```

### Debugging Mode
```bash
# Start with debug output
DEBUG=1 ./tools/launch_mcp.sh --start

# Or run directly for immediate feedback
uv run python -m trumpf_oseon_mcp
```

## Troubleshooting

### Common Issues

**Script permission denied:**
```bash
chmod +x tools/launch_mcp.sh tools/raycast_mcp.sh
```

**Server won't start:**
```bash
# Check logs for specific error
./tools/launch_mcp.sh --logs

# Try rebuilding dependencies
./tools/launch_mcp.sh --build --restart
```

**Port already in use:**
```bash
# Find and kill existing process
lsof -i :6274  # or whatever port MCP uses
kill -9 [PID]
```

**Environment file not found:**
```bash
# Ensure .env exists and is properly configured
cp env.example .env
# Edit .env with your Oseon server details
```

### Log Analysis
```bash
# Recent errors only
./tools/launch_mcp.sh --logs | grep -i error

# Connection issues
./tools/launch_mcp.sh --logs | grep -i "connection\|timeout\|refused"

# Authentication problems  
./tools/launch_mcp.sh --logs | grep -i "auth\|401\|403"
```

## Integration Examples

### GitHub Actions CI/CD
```yaml
name: Test MCP Server
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Test server startup
        run: |
          ./tools/launch_mcp.sh --build
          timeout 10s ./tools/launch_mcp.sh --start || true
          ./tools/launch_mcp.sh --status
```

### Docker Integration
```dockerfile
# Add to your Dockerfile
COPY tools/ /app/tools/
RUN chmod +x /app/tools/*.sh
CMD ["/app/tools/launch_mcp.sh", "--start"]
```

Tools for managing your MCP server with process monitoring and debugging.