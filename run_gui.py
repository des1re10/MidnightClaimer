#!/usr/bin/env python3
"""
MidnightClaimer GUI Launcher
Convenient launcher script for the GUI application
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run the main application
from Src.main import main

if __name__ == "__main__":
    print("🌙 Starting MidnightClaimer GUI...")
    print("📁 Project directory:", project_root)
    print("🔧 Python version:", sys.version)
    print("=" * 50)
    
    main()