#!/bin/bash
# VibeJudge E2E Test Runner
# Usage: ./run_e2e_tests.sh [smoke|critical|full|headed|debug]

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
MODE=${1:-smoke}
HEADLESS=${HEADLESS:-true}

# Print header
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  VibeJudge E2E Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Playwright is installed
if ! command -v playwright &> /dev/null; then
    echo -e "${RED}Error: Playwright not found${NC}"
    echo "Installing Playwright..."
    pip install playwright
    playwright install chromium
fi

# Check if Streamlit app is running
if ! curl -s http://localhost:8501 > /dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Streamlit app not running at http://localhost:8501${NC}"
    echo "Starting Streamlit in background..."
    cd streamlit_ui
    streamlit run VibeJudge_AI_Dashboard.py --server.port 8501 &
    STREAMLIT_PID=$!
    cd ..
    echo "Waiting for Streamlit to start..."
    sleep 10
fi

# Check if API is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${YELLOW}Warning: API not running at http://localhost:8000${NC}"
    echo "Please start the FastAPI backend first:"
    echo "  cd backend && uvicorn app.main:app --reload"
    exit 1
fi

# Run tests based on mode
case $MODE in
    smoke)
        echo -e "${GREEN}Running SMOKE tests (fast, critical paths)...${NC}"
        pytest e2e_tests/tests/ -m smoke -v --tb=short
        ;;
    critical)
        echo -e "${GREEN}Running CRITICAL tests...${NC}"
        pytest e2e_tests/tests/ -m critical -v --tb=short
        ;;
    full)
        echo -e "${GREEN}Running FULL test suite...${NC}"
        pytest e2e_tests/tests/ -v --tb=short
        ;;
    headed)
        echo -e "${GREEN}Running tests in HEADED mode (visible browser)...${NC}"
        HEADLESS=false pytest e2e_tests/tests/ -m smoke -v --headed
        ;;
    debug)
        echo -e "${GREEN}Running tests in DEBUG mode...${NC}"
        HEADLESS=false pytest e2e_tests/tests/ -m smoke -v --headed --pdb
        ;;
    specific)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Please specify test file or test name${NC}"
            echo "Usage: ./run_e2e_tests.sh specific test_auth_flows.py"
            exit 1
        fi
        echo -e "${GREEN}Running specific test: $2${NC}"
        pytest "e2e_tests/tests/$2" -xvs
        ;;
    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo "Usage: ./run_e2e_tests.sh [smoke|critical|full|headed|debug|specific]"
        echo ""
        echo "Modes:"
        echo "  smoke     - Fast smoke tests (~5 min)"
        echo "  critical  - Critical path tests (~10 min)"
        echo "  full      - All tests (~25 min)"
        echo "  headed    - Run with visible browser"
        echo "  debug     - Run with debugger"
        echo "  specific  - Run specific test file"
        exit 1
        ;;
esac

# Cleanup
if [ ! -z "$STREAMLIT_PID" ]; then
    echo -e "${YELLOW}Stopping Streamlit...${NC}"
    kill $STREAMLIT_PID 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Tests Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Screenshots (on failure): e2e_tests/visual_regression/failures/"
echo "Test reports: e2e_tests/reports/"
