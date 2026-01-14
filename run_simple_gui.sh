#!/bin/bash
# =============================================================================
# MidnightClaimer - Simple Step-by-Step GUI
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

PROJECT_NAME="MidnightClaimer"
PROJECT_DIR="$SCRIPT_DIR"

# Load common functions for terminal title
COMMON_FUNCTIONS="$SCRIPT_DIR/../Libraries/Scripts/common_functions.sh"
if [ -f "$COMMON_FUNCTIONS" ]; then
    sed -i 's/\r$//' "$COMMON_FUNCTIONS" 2>/dev/null || true
    source "$COMMON_FUNCTIONS"
    set_terminal_title "$PROJECT_NAME - GUI"
fi

echo "🌙 MidnightClaimer - Simple Step-by-Step GUI"
echo "============================================"
echo

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "Please install Python 3.8+ from your package manager"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if tkinter is available
if ! python3 -c "import tkinter" &> /dev/null; then
    echo "❌ tkinter is not available"
    echo "Please install tkinter:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-tk"
    echo "  CentOS/RHEL: sudo yum install tkinter"
    echo "  macOS: brew install python-tk"
    read -p "Press Enter to exit..."
    exit 1
fi

# Run the simple GUI
echo "✅ Starting simple GUI..."
python3 simple_gui.py

echo
read -p "Press Enter to exit..."