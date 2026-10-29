#!/usr/bin/env python3
"""Entry point for Circuit Tracks MCP Server.

This script starts the full-featured MCP server from circuit-tracks-tools
with proper PYTHONPATH configuration.

Usage:
    uv run python mcp_server.py
    
Or with the shell script:
    ./start_mcp.sh
"""

import sys
from pathlib import Path

# Add vendor circuit-tracks-tools to path
vendor_path = Path(__file__).parent / "vendor" / "circuit-tracks-tools" / "src"
if str(vendor_path) not in sys.path:
    sys.path.insert(0, str(vendor_path))

# Add src to path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import and run the MCP server
from circuit_mcp.server import mcp

if __name__ == "__main__":
    print("Starting Circuit Tracks MCP Server...")
    print("Tools available: 30+")
    print("Mock mode: Enabled (no hardware required)")
    print("\nConnect your LLM client to this server.")
    print("See docs/LLM_INTEGRATION.md for configuration.\n")
    
    # Run the MCP server with stdio transport
    mcp.run()
