# LLM Integration Guide

> Connect Circuit Tracks MCP Server to your favorite AI coding assistant

## Quick Start

```bash
# Start the MCP server
./start_mcp.sh

# Or manually:
PYTHONPATH="vendor/circuit-tracks-tools/src:src:." uv run python mcp_server.py
```

The server uses **stdio transport** - your LLM client communicates via standard input/output.

---

## Cursor

Create `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "circuit-tracks": {
      "command": "/home/kai/circuit-ai-studio/start_mcp.sh",
      "args": [],
      "env": {}
    }
  }
}
```

**Usage:**
1. Open Cursor in the circuit-ai-studio directory
2. The MCP server auto-connects
3. Ask: "Create a 4-bar drum pattern with kick on beats 1 and 3"

---

## Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `~/.config/Claude/claude_desktop_config.json` (Linux):

```json
{
  "mcpServers": {
    "circuit-tracks": {
      "command": "/home/kai/circuit-ai-studio/start_mcp.sh",
      "args": [],
      "env": {}
    }
  }
}
```

**Usage:**
1. Restart Claude Desktop
2. Click the 🔌 icon to verify "circuit-tracks" is connected
3. Ask: "Design a synth patch with a sweeping filter"

---

## Windsurf

Create `.windsurf/mcp.json`:

```json
{
  "mcpServers": {
    "circuit-tracks": {
      "command": "/home/kai/circuit-ai-studio/start_mcp.sh",
      "args": [],
      "env": {}
    }
  }
}
```

---

## Aider

Add to your `.aider.conf.yml`:

```yaml
mcp:
  - command: /home/kai/circuit-ai-studio/start_mcp.sh
    name: circuit-tracks
```

**Usage:**
```bash
aider --mcp circuit-tracks
```

Then ask: "Compose a verse pattern with polyrhythmic drums"

---

## Mock Mode

The server automatically falls back to **mock mode** when no hardware is connected:
- All tools work normally
- MIDI messages are logged instead of sent
- Perfect for testing and development
- No Circuit Tracks required

---

## Example Prompts

### Pattern Creation
```
"Create a 16-step pattern with:
- Synth 1: Bass line on C2, E2, G2
- Drum 1: Kick on beats 1, 3
- Drum 2: Snare on beats 2, 4"
```

### Sound Design
```
"Design a synth patch with:
- Oscillator 1: Saw wave
- Filter: Low-pass, cutoff 80, resonance 60
- Amp envelope: Attack 10, Decay 40, Sustain 80, Release 60"
```

### Live Performance
```
"Set macro 1 (filter) to 100 on synth 1"
"Play a C major chord on synth 2"
```

### Song Structure
```
"Create a song with patterns: intro, verse, chorus, verse, chorus, outro"
```

---

## Troubleshooting

### Server won't start
```bash
# Check Python path
uv run python --version

# Verify dependencies
uv sync

# Test import
PYTHONPATH="vendor/circuit-tracks-tools/src:src:." python -c "from circuit_mcp.server import mcp; print('OK')"
```

### LLM client can't connect
- Ensure `start_mcp.sh` is executable: `chmod +x start_mcp.sh`
- Use absolute paths in config files
- Check server logs for errors

### Tools not showing up
- Restart your LLM client after config changes
- Verify MCP server is running: `./start_mcp.sh`
- Check tool list: Ask your LLM "list available tools"

---

## Architecture

```
LLM Client (Cursor/Claude/etc.)
    ↓ stdio
MCP Server (mcp_server.py)
    ↓ Python imports
circuit_mcp.server (vendor/circuit-tracks-tools)
    ↓ MIDI
Circuit Tracks Hardware (or Mock)
```

---

## Resources

- **Tool Reference**: `docs/MCP_TOOLS_REFERENCE.md`
- **Agent Spec**: `AGENT_SPEC.md`
- **Main README**: `README.md`
