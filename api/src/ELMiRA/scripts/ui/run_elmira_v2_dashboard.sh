#!/bin/bash
# =============================================================================
# ELMiRA v2 Dashboard Launcher (run_elmira_v2_dashboard.sh)
# =============================================================================
#
# This script sources the NICO virtual environment and launches the Streamlit
# dashboard for ELMiRA v2.
#
# Usage:
#     ./run_dashboard.sh
#     ./run_dashboard.sh --port 8502
#
# =============================================================================

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Path to activate.bash (relative to script location)
ACTIVATE_BASH="$SCRIPT_DIR/../../../../activate.bash"

# Check if activate.bash exists
if [ ! -f "$ACTIVATE_BASH" ]; then
    echo "Error: Could not find activate.bash at $ACTIVATE_BASH"
    echo "Please ensure the NICO environment is properly installed."
    exit 1
fi

# Source the NICO environment
echo "🔧 Sourcing NICO environment..."
source "$ACTIVATE_BASH"

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "⚠️  Streamlit not found. Installing..."
    pip install streamlit pandas
fi

# Default port
PORT="${1:-8501}"
if [[ "$1" == "--port" ]]; then
    PORT="$2"
fi

# Dashboard file
DASHBOARD="$SCRIPT_DIR/elmira_v2_dashboard.py"

echo "🚀 Starting ELMiRA v2 Dashboard..."
echo "   URL: http://localhost:$PORT"
echo "   Press Ctrl+C to stop"
echo ""

# Run streamlit
streamlit run "$DASHBOARD" \
    --server.port "$PORT" \
    --server.address "0.0.0.0" \
    --server.headless true \
    --browser.gatherUsageStats false
