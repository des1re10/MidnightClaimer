#!/usr/bin/env python3
"""
MidnightClaimer GUI Launcher v2.0
Clean, simple launcher for the GUI application
"""

import sys
import os
from pathlib import Path

def main():
    """Launch the MidnightClaimer GUI"""
    print("🌙 MidnightClaimer GUI v1.0")
    print("=" * 40)
    
    # Get the directory containing this script
    script_dir = Path(__file__).parent.absolute()
    print(f"📁 Project directory: {script_dir}")
    
    # Add script directory to Python path
    sys.path.insert(0, str(script_dir))
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher required")
        print(f"   Current version: {sys.version}")
        input("Press Enter to exit...")
        return
    
    print(f"🐍 Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    try:
        # Import and run the main application
        print("🚀 Starting application...")
        from Src.main import main as app_main
        app_main()
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\nThis usually means missing dependencies or files.")
        print("Please ensure all required files are present:")
        print("• Src/main.py")
        print("• Src/gui/main_window.py") 
        print("• Src/services/cardano_service.py")
        print("• Src/services/bitcoin_service.py")
        print("• Src/utils/security.py")
        print("\nAnd install required packages:")
        print("pip install pycardano bitcoinlib mnemonic base58")
        input("\nPress Enter to exit...")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("Check the log file for more details.")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()