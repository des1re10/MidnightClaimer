#!/usr/bin/env python3
"""
MidnightClaimer GUI Application Entry Point
User-friendly graphical interface for claiming Midnight tokens from Trezor wallets
"""

import sys
import tkinter as tk
from tkinter import messagebox
import logging
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from Src.gui.main_window import MidnightClaimerGUI

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(project_root / 'midnight_claimer_gui.log', mode='a')
        ]
    )

def check_dependencies():
    """Check for required dependencies"""
    missing_deps = []
    
    try:
        import pycardano
    except ImportError:
        missing_deps.append("pycardano")
    
    try:
        import bitcoinlib
    except ImportError:
        missing_deps.append("bitcoinlib")
    
    try:
        from mnemonic import Mnemonic
    except ImportError:
        missing_deps.append("mnemonic")
    
    try:
        from PIL import Image, ImageTk
    except ImportError:
        missing_deps.append("Pillow")
    
    if missing_deps:
        error_msg = f"Missing required dependencies:\n\n"
        error_msg += "\n".join(f"• {dep}" for dep in missing_deps)
        error_msg += "\n\nPlease install them using:\n"
        error_msg += f"pip install {' '.join(missing_deps)}"
        
        # Show error dialog if tkinter is available
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Missing Dependencies", error_msg)
            root.destroy()
        except:
            print(error_msg)
        
        return False
    
    return True

def main():
    """Main application entry point"""
    print("🌙 MidnightClaimer GUI - Starting...")
    print("=" * 50)
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Check dependencies
        if not check_dependencies():
            sys.exit(1)
        
        logger.info("Starting MidnightClaimer GUI application")
        
        # Create and run the GUI application
        app = MidnightClaimerGUI()
        app.run()
        
        logger.info("MidnightClaimer GUI application terminated normally")
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        print("\n\n🛑 Application interrupted by user")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        
        # Show error dialog
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Unexpected Error", 
                               f"An unexpected error occurred:\n\n{e}\n\n"
                               "Please check the log file for details.")
            root.destroy()
        except:
            print(f"❌ Unexpected error: {e}")
        
        sys.exit(1)
    
    print("\n✨ Thank you for using MidnightClaimer!")

if __name__ == "__main__":
    main()