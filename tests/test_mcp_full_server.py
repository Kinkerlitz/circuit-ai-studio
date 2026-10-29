"""Tests for the full-featured MCP server from circuit-tracks-tools.

Tests the 30+ tools available in vendor/circuit-tracks-tools/src/circuit_mcp/server.py
Uses mock MIDI connection (no hardware required).
"""

import sys
from pathlib import Path

import pytest

# Add vendor path
vendor_path = Path(__file__).parent.parent / "vendor" / "circuit-tracks-tools" / "src"
if str(vendor_path) not in sys.path:
    sys.path.insert(0, str(vendor_path))


@pytest.fixture
def mcp_server():
    """Import and return the MCP server instance."""
    from circuit_mcp.server import mcp
    return mcp


class TestMCPServerBasics:
    """Test basic MCP server functionality."""

    def test_server_import(self, mcp_server):
        """Test that MCP server can be imported."""
        assert mcp_server is not None
        assert mcp_server.name == "Circuit Tracks"

    def test_server_has_instructions(self, mcp_server):
        """Test that server has instructions for LLMs."""
        assert mcp_server.instructions is not None
        assert len(mcp_server.instructions) > 0

    @pytest.mark.asyncio
    async def test_list_tools(self, mcp_server):
        """Test listing available tools."""
        tools = await mcp_server.list_tools()
        assert len(tools) > 0
        # Check for critical tools
        tool_names = [t.name for t in tools]
        assert "list_midi_ports" in tool_names
        assert "connect" in tool_names
        assert "play_notes" in tool_names
        assert "set_pattern" in tool_names


class TestToolRegistration:
    """Test that all tools are properly registered."""

    @pytest.mark.asyncio
    async def test_critical_tools_exist(self, mcp_server):
        """Test that critical tools are registered."""
        tools = await mcp_server.list_tools()
        tool_names = [t.name for t in tools]
        
        critical_tools = [
            "list_midi_ports",
            "connect",
            "disconnect",
            "connection_status",
            "play_notes",
            "set_pattern",
            "start_sequencer",
            "stop_sequencer",
            "get_parameter_reference",
        ]
        
        for tool_name in critical_tools:
            assert tool_name in tool_names, f"Tool '{tool_name}' not registered"

    @pytest.mark.asyncio
    async def test_tool_count(self, mcp_server):
        """Test that we have 30+ tools available."""
        tools = await mcp_server.list_tools()
        assert len(tools) >= 30, f"Expected 30+ tools, got {len(tools)}"


class TestMockMode:
    """Test that server works in mock mode (no hardware)."""

    def test_server_starts_without_hardware(self, mcp_server):
        """Verify server can start without MIDI hardware."""
        # Server should initialize even without hardware
        assert mcp_server is not None

    @pytest.mark.asyncio
    async def test_list_tools_mock_mode(self, mcp_server):
        """Test tool listing in mock mode."""
        tools = await mcp_server.list_tools()
        # Should work without hardware
        assert len(tools) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
