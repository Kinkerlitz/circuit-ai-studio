#!/bin/bash
# Circuit AI Studio Setup Script
# Clones required dependencies and sets up the project

set -e

echo "🎛️  Circuit AI Studio Setup"
echo "=========================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📦 Setting up Python dependencies..."
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✓${NC} uv found"
    uv sync
else
    echo -e "${YELLOW}⚠${NC} uv not found, installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    uv sync
fi

echo ""
echo "📦 Setting up vendor dependencies..."

# Clone circuit-tracks-tools if not present
if [ ! -d "vendor/circuit-tracks-tools" ]; then
    echo "Cloning circuit-tracks-tools..."
    mkdir -p vendor
    git clone https://github.com/digitalhobbit/circuit-tools.git vendor/circuit-tracks-tools
    echo -e "${GREEN}✓${NC} circuit-tracks-tools cloned"
else
    echo -e "${GREEN}✓${NC} circuit-tracks-tools already exists"
fi

echo ""
echo "📦 Setting up frontend dependencies..."
cd frontend
if command -v npm &> /dev/null; then
    npm install
    echo -e "${GREEN}✓${NC} Frontend dependencies installed"
else
    echo -e "${YELLOW}⚠${NC} npm not found, skipping frontend setup"
fi
cd ..

echo ""
echo "📦 Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠${NC} .env created from .env.example"
        echo "   Please edit .env and add your GOOGLE_API_KEY"
    else
        echo -e "${YELLOW}⚠${NC} .env.example not found, skipping"
    fi
else
    echo -e "${GREEN}✓${NC} .env already exists"
fi

echo ""
echo "=========================="
echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your GOOGLE_API_KEY"
echo "2. Start backend: ./start_backend.sh"
echo "3. Start frontend: cd frontend && npm run dev"
echo "4. Open http://localhost:3000/"
echo ""
echo "For LLM integration:"
echo "- Get API key at: https://makersuite.google.com/app/apikey"
echo "- Add to .env: GOOGLE_API_KEY=your_key_here"
