#!/bin/bash

# TRUMPF Oseon MCP Server Launcher
# This script can build, launch, stop, and restart the MCP server
# Compatible with Raycast integration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$PROJECT_ROOT/.mcp_server.pid"
LOG_FILE="$PROJECT_ROOT/.mcp_server.log"
VENV_DIR="$PROJECT_ROOT/.venv"

# Function to print colored output
print_status() {
    echo -e "${BLUE}🚀 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

# Function to check if server is running
is_server_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # Server is running
        else
            # PID file exists but process is dead
            rm -f "$PID_FILE"
        fi
    fi
    return 1  # Server is not running
}

# Function to stop the server
stop_server() {
    if is_server_running; then
        local pid=$(cat "$PID_FILE")
        print_status "Stopping MCP server (PID: $pid)..."
        kill "$pid" 2>/dev/null || true
        sleep 2
        if kill -0 "$pid" 2>/dev/null; then
            print_warning "Server didn't stop gracefully, forcing termination..."
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
        print_success "MCP server stopped"
    else
        print_info "MCP server is not running"
    fi
}

# Function to start the server
start_server() {
    if is_server_running; then
        print_warning "MCP server is already running"
        return 0
    fi

    print_status "Starting MCP server..."
    
    # Activate virtual environment
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment not found. Please run with --build first."
        exit 1
    fi
    
    source "$VENV_DIR/bin/activate"
    
    # Check if .env file exists
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        print_warning "No .env file found. Please create one with your API credentials."
        print_info "You can copy from env.example: cp env.example .env"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Aborted"
            exit 1
        fi
    fi
    
    # Start the server in the background and get its PID
    python -m trumpf_oseon_mcp > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"
    
    # Wait a moment for the process to start
    sleep 1
    
    # Wait a moment to check if server started successfully
    sleep 2
    if kill -0 "$pid" 2>/dev/null; then
        # Give it a bit more time to fully initialize
        sleep 1
        if kill -0 "$pid" 2>/dev/null; then
            print_success "MCP server started successfully (PID: $pid)"
            print_info "Logs are being written to: $LOG_FILE"
            print_info "To stop the server, run: $0 --stop"
            print_info "To view logs: $0 --logs"
            print_info "Server is ready for MCP client connections"
        else
            print_error "MCP server started but exited unexpectedly"
            rm -f "$PID_FILE"
            print_info "Check the logs: tail -f $LOG_FILE"
            exit 1
        fi
    else
        print_error "Failed to start MCP server"
        rm -f "$PID_FILE"
        print_info "Check the logs: tail -f $LOG_FILE"
        exit 1
    fi
}

# Function to build/rebuild the project
build_project() {
    print_status "Building/rebuilding MCP server..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        if [ $? -ne 0 ]; then
            print_error "Failed to create virtual environment. Please check Python installation."
            exit 1
        fi
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip >/dev/null 2>&1
    
    # Install/upgrade dependencies
    print_status "Installing/upgrading dependencies..."
    pip install -e . --upgrade
    if [ $? -ne 0 ]; then
        print_error "Failed to install dependencies"
        exit 1
    fi
    print_success "Dependencies installed/upgraded"
    
    # Verify installation
    print_status "Verifying installation..."
    if python -c "import trumpf_oseon_mcp" 2>/dev/null; then
        print_success "MCP server package verified"
    else
        print_error "MCP server package verification failed"
        exit 1
    fi
}

# Function to show server status
show_status() {
    echo -e "${PURPLE}🔍 MCP Server Status${NC}"
    echo "=================="
    
    if is_server_running; then
        local pid=$(cat "$PID_FILE")
        print_success "Server is RUNNING (PID: $pid)"
        print_info "Log file: $LOG_FILE"
        print_info "To view logs: tail -f $LOG_FILE"
        print_info "To stop server: $0 --stop"
    else
        print_warning "Server is NOT RUNNING"
        print_info "To start server: $0 --start"
        print_info "To build and start: $0 --build --start"
    fi
    
    # Show environment info
    if [ -d "$VENV_DIR" ]; then
        print_success "Virtual environment: $VENV_DIR"
    else
        print_warning "Virtual environment not found"
    fi
    
    if [ -f "$PROJECT_ROOT/.env" ]; then
        print_success "Configuration file: .env"
    else
        print_warning "Configuration file: .env (not found)"
    fi
}

# Function to show logs
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_status "Showing recent logs (last 50 lines):"
        echo "=================="
        tail -n 50 "$LOG_FILE"
        echo "=================="
        print_info "To follow logs in real-time: tail -f $LOG_FILE"
    else
        print_warning "No log file found. Server may not have been started yet."
    fi
}

# Function to restart the server
restart_server() {
    print_status "Restarting MCP server..."
    stop_server
    sleep 1
    start_server
}

# Function to show help
show_help() {
    echo -e "${PURPLE}TRUMPF Oseon MCP Server Launcher${NC}"
    echo "=================================="
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  --build          Build/rebuild the project (install dependencies)"
    echo "  --start          Start the MCP server"
    echo "  --stop           Stop the MCP server"
    echo "  --restart        Restart the MCP server"
    echo "  --status         Show server status"
    echo "  --logs           Show recent server logs"
    echo "  --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --build --start    Build and start the server"
    echo "  $0 --restart          Restart the server"
    echo "  $0 --status           Check if server is running"
    echo "  $0 --logs             View recent logs"
    echo ""
    echo "Raycast Integration:"
    echo "  This script is designed to work with Raycast. Use --start to launch"
    echo "  the server and --stop to terminate it."
    echo ""
    echo "Process Management:"
    echo "  The server runs in the background with PID tracking."
    echo "  Logs are written to: $LOG_FILE"
    echo "  PID file: $PID_FILE"
}

# Main script logic
cd "$PROJECT_ROOT"

# Handle command line arguments
case "${1:-}" in
    --build)
        build_project
        ;;
    --start)
        start_server
        ;;
    --stop)
        stop_server
        ;;
    --restart)
        restart_server
        ;;
    --status)
        show_status
        ;;
    --logs)
        show_logs
        ;;
    --help|-h)
        show_help
        ;;
    "")
        # No arguments - show status and help
        show_status
        echo ""
        show_help
        ;;
    *)
        print_error "Unknown option: $1"
        echo ""
        show_help
        exit 1
        ;;
esac 