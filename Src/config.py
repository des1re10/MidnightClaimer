#!/usr/bin/env python3
"""
Configuration settings for MidnightClaimer GUI Application
Centralized configuration management for the application
"""

import os
from pathlib import Path

# Application metadata
APP_NAME = "MidnightClaimer"
APP_VERSION = "1.0"
APP_TITLE = f"{APP_NAME} - Secure Token Claiming Tool v{APP_VERSION}"

# Directories
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent
LOG_DIR = BASE_DIR / "logs"
WORKSPACE_DIR = BASE_DIR / "secure_workspace"

# GUI Configuration
DEFAULT_WINDOW_SIZE = "900x700"
MIN_WINDOW_SIZE = (800, 600)
GUI_RESIZABLE = True

# Security Configuration
SECURE_WORKSPACE_PREFIX = "midnight_claim_workspace_"
TEMP_FILE_PREFIX = "midnight_temp_"
MAX_DERIVATION_ACCOUNTS = 10
DEFAULT_DERIVATION_ACCOUNTS = 5

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 3

# Network Configuration
CARDANO_NETWORK = "mainnet"
BITCOIN_NETWORK = "mainnet"

# File Extensions
CARDANO_KEY_EXTENSION = ".skey"
BITCOIN_KEY_EXTENSION = ".wif"
LOG_EXTENSION = ".log"

# UI Colors and Styles
COLORS = {
    "success": "#28a745",
    "warning": "#ffc107", 
    "error": "#dc3545",
    "info": "#17a2b8"
}

# Default derivation paths
CARDANO_DERIVATION_PATH = "m/1852'/1815'/{account}'/0/{index}"
BITCOIN_DERIVATION_PATHS = {
    "legacy": "m/44'/0'/{account}'/0/{index}",  # P2PKH
    "segwit": "m/49'/0'/{account}'/0/{index}",  # P2SH-P2WPKH
    "native_segwit": "m/84'/0'/{account}'/0/{index}"  # P2WPKH
}

def get_log_file_path():
    """Get the path for the main log file"""
    LOG_DIR.mkdir(exist_ok=True)
    return LOG_DIR / f"midnight_claimer_gui{LOG_EXTENSION}"

def get_workspace_path():
    """Get a unique workspace path for this session"""
    WORKSPACE_DIR.mkdir(exist_ok=True)
    import os
    return WORKSPACE_DIR / f"{SECURE_WORKSPACE_PREFIX}{os.getpid()}"

def ensure_directories():
    """Ensure all required directories exist"""
    directories = [LOG_DIR, WORKSPACE_DIR]
    for directory in directories:
        directory.mkdir(exist_ok=True, parents=True)