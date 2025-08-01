#!/bin/bash

# Raycast Script for TRUMPF Oseon MCP Server Management
# This script is designed to be used as a Raycast command

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Oseon MCP Server
# @raycast.mode compact

# Optional parameters:
# @raycast.icon 🤖
# @raycast.argument1 { "type": "text", "placeholder": "Action (start/stop/restart/status/logs)", "optional": true }

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER_SCRIPT="$SCRIPT_DIR/launch_mcp.sh"

# Colors for Raycast output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output for Raycast
print_raycast() {
    echo -e "$1"
}

# Check if launcher script exists
if [ ! -f "$LAUNCHER_SCRIPT" ]; then
    print_raycast "${RED}❌ Launcher script not found at: $LAUNCHER_SCRIPT${NC}"
    exit 1
fi

# Make sure launcher script is executable
chmod +x "$LAUNCHER_SCRIPT"

# Get action from argument or default to status
ACTION="${1:-status}"

# Map Raycast-friendly actions to launcher script options
case "$ACTION" in
    "start"|"s")
        print_raycast "${BLUE}🚀 Starting Oseon MCP Server...${NC}"
        "$LAUNCHER_SCRIPT" --start
        ;;
    "stop"|"x")
        print_raycast "${YELLOW}⏹️  Stopping Oseon MCP Server...${NC}"
        "$LAUNCHER_SCRIPT" --stop
        ;;
    "restart"|"r")
        print_raycast "${BLUE}🔄 Restarting Oseon MCP Server...${NC}"
        "$LAUNCHER_SCRIPT" --restart
        ;;
    "build"|"b")
        print_raycast "${BLUE}🔨 Building Oseon MCP Server...${NC}"
        "$LAUNCHER_SCRIPT" --build
        ;;
    "status"|"i")
        print_raycast "${BLUE}🔍 Checking Oseon MCP Server Status...${NC}"
        "$LAUNCHER_SCRIPT" --status
        ;;
    "logs"|"l")
        print_raycast "${BLUE}📋 Showing Oseon MCP Server Logs...${NC}"
        "$LAUNCHER_SCRIPT" --logs
        ;;
    "help"|"h")
        print_raycast "${BLUE}❓ Oseon MCP Server Help${NC}"
        echo "Available actions:"
        echo "  start/s    - Start the MCP server"
        echo "  stop/x     - Stop the MCP server"
        echo "  restart/r  - Restart the MCP server"
        echo "  build/b    - Build/rebuild the project"
        echo "  status/i   - Show server status"
        echo "  logs/l     - Show recent logs"
        echo "  help/h     - Show this help"
        ;;
    *)
        print_raycast "${RED}❌ Unknown action: $ACTION${NC}"
        print_raycast "${YELLOW}Use 'help' to see available actions${NC}"
        exit 1
        ;;
esac 