#!/bin/bash
# Circuit AI Studio Snoop - Live Monitor & Error Detector
# Usage: ./snoop.sh

# Don't exit on error - we want to continue monitoring

echo "🔍 Circuit AI Studio Snoop"
echo "=========================="
echo ""
echo "Monitoring services..."
echo "Press Ctrl+C to stop"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check services
check_service() {
    local name=$1
    local url=$2
    local expected=$3
    
    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null || echo "000")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "$expected" ]; then
        echo -e "${GREEN}✓${NC} $name: OK (HTTP $http_code)"
        return 0
    else
        echo -e "${RED}✗${NC} $name: FAILED (HTTP $http_code)"
        return 1
    fi
}

# Continuous monitoring
while true; do
    clear
    echo "🔍 Circuit AI Studio Snoop - $(date '+%H:%M:%S')"
    echo "========================================="
    echo ""
    
    # Check services
    echo "Service Status:"
    check_service "Frontend (Vite)" "http://localhost:3000" "200"
    check_service "Backend (FastAPI)" "http://localhost:8770/status" "200"
    check_service "Strata (LLM)" "http://localhost:8080/health" "200"
    echo ""
    
    # Check backend logs for errors
    echo "Recent Backend Activity:"
    if [ -f "/home/kai/.qwen/tmp/e6114d73fb14f063ed69ce4202a0ac4692ed6a4e26ed3079136e72e368cc518e/background-shells/a85d137b-34e6-412a-a846-980d693e4366/shell-bg_e5763c57.output" ]; then
        tail -5 "/home/kai/.qwen/tmp/e6114d73fb14f063ed69ce4202a0ac4692ed6a4e26ed3079136e72e368cc518e/background-shells/a85d137b-34e6-412a-a846-980d693e4366/shell-bg_e5763c57.output" 2>/dev/null | grep -E "(ERROR|WARNING|INFO)" | tail -5 || echo "No recent logs"
    fi
    echo ""
    
    # Check frontend logs
    echo "Recent Frontend Activity:"
    if [ -f "/home/kai/.qwen/tmp/e6114d73fb14f063ed69ce4202a0ac4692ed6a4e26ed3079136e72e368cc518e/background-shells/a85d137b-34e6-412a-a846-980d693e4366/shell-bg_571af2c3.output" ]; then
        tail -3 "/home/kai/.qwen/tmp/e6114d73fb14f063ed69ce4202a0ac4692ed6a4e26ed3079136e72e368cc518e/background-shells/a85d137b-34e6-412a-a846-980d693e4366/shell-bg_571af2c3.output" 2>/dev/null | grep -E "(error|warning)" -i | tail -3 || echo "No errors"
    fi
    echo ""
    
    # Test agent endpoint
    echo "Agent Endpoint Test:"
    agent_response=$(curl -s -X POST http://localhost:8770/api/agent \
        -H "Content-Type: application/json" \
        -d '{"prompt":"test","style":"acid","key":"A minor"}' \
        --max-time 5 2>&1)
    
    if echo "$agent_response" | grep -q "LLM API error"; then
        echo -e "${YELLOW}⚠${NC} Agent: Strata not running (expected)"
    elif echo "$agent_response" | grep -q "success"; then
        echo -e "${GREEN}✓${NC} Agent: Working!"
    else
        echo -e "${RED}✗${NC} Agent: Unknown error"
    fi
    echo ""
    
    # Quick stats
    echo "Quick Stats:"
    echo "  Backend processes: $(ps aux | grep uvicorn | grep -v grep | wc -l)"
    echo "  Frontend processes: $(ps aux | grep vite | grep -v grep | wc -l)"
    echo "  Strata processes: $(ps aux | grep strata | grep -v grep | wc -l)"
    echo ""
    
    echo "Next check in 5 seconds... (Ctrl+C to stop)"
    sleep 5
done
