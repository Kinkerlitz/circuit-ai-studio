#!/bin/bash
# Start Circuit Tracks MCP Server
# 
# Usage:
#   ./start_mcp.sh
#
# This starts the MCP server with stdio transport for LLM clients.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🎛️  Circuit Tracks MCP Server"
echo "=============================="
echo ""
echo "Starting server with stdio transport..."
echo "Mock mode: Enabled (no hardware required)"
echo ""
echo "Connect your LLM client:"
echo "  - Cursor: See .cursor/mcp.json"
echo "  - Claude Desktop: See claude_desktop_config.json"
echo "  - Full docs: docs/LLM_INTEGRATION.md"
echo ""

# Set PYTHONPATH
export PYTHONPATH="$SCRIPT_DIR/vendor/circuit-tracks-tools/src:$SCRIPT_DIR/src:$SCRIPT_DIR"

# Use uv to run in the project's virtual environment
# Try full path first, then fall back to PATH
if [ -x "$HOME/.local/bin/uv" ]; then
    exec "$HOME/.local/bin/uv" run python mcp_server.py
elif command -v uv &> /dev/null; then
    exec uv run python mcp_server.py
else
    echo "Error: uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
