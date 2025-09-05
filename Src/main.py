#!/usr/bin/env python3
"""
MidnightClaimer GUI Application Entry Point
Updated to handle import paths correctly and provide better error handling
"""

import sys
import tkinter as tk
from tkinter import messagebox
import logging
from pathlib import Path
import os

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def setup_logging():
    """Setup logging configuration"""
    try:
        from config import get_log_file_path, LOG_FORMAT, LOG_LEVEL, ensure_directories
        ensure_directories()
        log_file = get_log_file_path()
    except ImportError:
        # Fallback if config not available
        log_file = current_dir / 'midnight_claimer_gui.log'
        LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        LOG_LEVEL = 'INFO'
    
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, mode='a')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("MidnightClaimer GUI starting...")
    logger.info(f"Current directory: {current_dir}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python path: {sys.path[:3]}...")  # Show first 3 entries
    
    return logger

def check_dependencies():
    """Check for required dependencies"""
    missing_deps = []
    dependency_errors = []
    
    # Check tkinter (should be built-in)
    try:
        import tkinter
        import tkinter.ttk
        import tkinter.scrolledtext
    except ImportError as e:
        missing_deps.append("tkinter")
        dependency_errors.append(f"tkinter: {e}")
    
    # Check PyCardano
    try:
        import pycardano
        from pycardano import HDWallet, PaymentVerificationKey, Address, Network
        from pycardano.key import ExtendedSigningKey
    except ImportError as e:
        missing_deps.append("pycardano")
        dependency_errors.append(f"pycardano: {e}")
    
    # Check bitcoinlib
    try:
        import bitcoinlib
        from bitcoinlib.keys import HDKey
    except ImportError as e:
        missing_deps.append("bitcoinlib")
        dependency_errors.append(f"bitcoinlib: {e}")
    
    # Check mnemonic
    try:
        from mnemonic import Mnemonic
    except ImportError as e:
        missing_deps.append("mnemonic")
        dependency_errors.append(f"mnemonic: {e}")
    
    # Check base58 (used by bitcoin validation)
    try:
        import base58
    except ImportError as e:
        missing_deps.append("base58")
        dependency_errors.append(f"base58: {e}")
    
    if missing_deps:
        error_msg = f"Missing required dependencies:\n\n"
        for error in dependency_errors:
            error_msg += f"• {error}\n"
        error_msg += "\nPlease install them using:\n"
        error_msg += f"pip install {' '.join(missing_deps)}"
        
        # Show error dialog if tkinter is available
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Missing Dependencies", error_msg)
            root.destroy()
        except:
            print(error_msg)
        
        return False, error_msg
    
    return True, "All dependencies available"

def check_required_files():
    """Check that required service files exist"""
    required_files = [
        'gui/main_window.py',
        'services/cardano_service.py', 
        'services/bitcoin_service.py',
        'utils/security.py'
    ]
    
    missing_files = []
    for file in required_files:
        file_path = current_dir / file
        if not file_path.exists():
            missing_files.append(file)
    
    if missing_files:
        error_msg = f"Missing required files:\n\n"
        error_msg += "\n".join(f"• {file}" for file in missing_files)
        error_msg += f"\n\nPlease ensure all files are in: {current_dir}"
        
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Missing Files", error_msg)
            root.destroy()
        except:
            print(error_msg)
        
        return False, error_msg
    
    return True, "All required files found"

def test_imports():
    """Test that all required modules can be imported"""
    try:
        # Test service imports
        from gui.main_window import MidnightClaimerGUI
        from services.cardano_service import CardanoService
        from services.bitcoin_service import BitcoinService
        from utils.security import SecurityManager
        
        logger = logging.getLogger(__name__)
        logger.info("All modules imported successfully")
        
        return True, "Import test successful"
        
    except Exception as e:
        error_msg = f"Import test failed: {e}"
        
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Import Error", error_msg)
            root.destroy()
        except:
            print(error_msg)
        
        return False, error_msg

def main():
    """Main application entry point"""
    print("🌙 MidnightClaimer GUI v1.0 - Starting...")
    print("=" * 50)
    
    # Setup logging first
    logger = setup_logging()
    
    try:
        # Check that all required files exist
        files_ok, files_msg = check_required_files()
        if not files_ok:
            logger.error(f"File check failed: {files_msg}")
            sys.exit(1)
        
        # Check dependencies
        deps_ok, deps_msg = check_dependencies()
        if not deps_ok:
            logger.error(f"Dependency check failed: {deps_msg}")
            sys.exit(1)
        
        logger.info("Dependency check passed")
        
        # Test imports
        import_ok, import_msg = test_imports()
        if not import_ok:
            logger.error(f"Import test failed: {import_msg}")
            sys.exit(1)
        
        logger.info("Import test passed")
        
        # Import and create the GUI application
        from gui.main_window import MidnightClaimerGUI
        
        logger.info("Starting MidnightClaimer GUI application")
        print("✅ All checks passed - launching GUI...")
        
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
                               "Please check the log file for details.\n"
                               f"Log location: {current_dir}/midnight_claimer_gui.log")
            root.destroy()
        except:
            print(f"❌ Unexpected error: {e}")
        
        sys.exit(1)
    
    print("\n✨ Thank you for using MidnightClaimer!")

if __name__ == "__main__":
    main()