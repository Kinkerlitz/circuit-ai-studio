#!/usr/bin/env bash
set -e
cd ~/circuit-ai-studio
lsof -ti:8770 | xargs kill -9 2>/dev/null || true

if [ ! -f "pyproject.toml" ]; then
    uv init --no-workspace --name circuit-ai-studio
    uv add mido python-rtmidi fastapi uvicorn websockets pydantic mcp
    uv add --dev pytest pytest-asyncio httpx
fi

aider --model gemini/gemini-3.7-flash "$@"
