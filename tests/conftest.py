#!/usr/bin/env python3
"""
pytest configuration and fixtures
Provides universal GUI popup prevention for all tests
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock

# Create comprehensive GUI mocks BEFORE any test imports
mock_messagebox = Mock()
mock_messagebox.askyesno = Mock(return_value=True)
mock_messagebox.showinfo = Mock(return_value=None)
mock_messagebox.showwarning = Mock(return_value=None)
mock_messagebox.showerror = Mock(return_value=None)

mock_tkinter = Mock()
mock_tkinter.messagebox = mock_messagebox
mock_tkinter.Tk = Mock()
mock_tkinter.Entry = Mock()
mock_tkinter.Text = Mock()
mock_tkinter.TclError = Exception  # Mock TclError as a regular Exception

# Install GUI mocks globally to prevent ANY GUI popups during testing
sys.modules['tkinter'] = mock_tkinter
sys.modules['tkinter.messagebox'] = mock_messagebox
sys.modules['tkinter.ttk'] = Mock()
sys.modules['tkinter.scrolledtext'] = Mock()

# Mock crypto libraries to allow tests to run without actual crypto dependencies
mock_pycardano = MagicMock()
mock_pycardano.key = MagicMock()
mock_pycardano.key.ExtendedSigningKey = MagicMock()

mock_bitcoinlib = MagicMock()
mock_bitcoinlib.keys = MagicMock()

sys.modules['pycardano'] = mock_pycardano
sys.modules['pycardano.key'] = mock_pycardano.key
sys.modules['bitcoinlib'] = mock_bitcoinlib
sys.modules['bitcoinlib.keys'] = mock_bitcoinlib.keys
sys.modules['mnemonic'] = MagicMock()

@pytest.fixture(autouse=True)
def reset_gui_mocks():
    """Reset GUI mock call counts before each test"""
    mock_messagebox.askyesno.reset_mock()
    mock_messagebox.showinfo.reset_mock()
    mock_messagebox.showwarning.reset_mock()
    mock_messagebox.showerror.reset_mock()

@pytest.fixture
def mock_security_manager():
    """Provide a mocked SecurityManager that doesn't show popups"""
    mock_manager = Mock()
    mock_manager.show_memory_warning = Mock(return_value=True)
    mock_manager.secure_cleanup = Mock(return_value=True)
    mock_manager.register_temp_file = Mock()
    mock_manager.temp_files = []
    mock_manager.secure_widgets = []
    mock_manager.workspace_dir = None
    mock_manager._cleanup_performed = False
    return mock_manager

# Print confirmation that popup prevention is active
print("✅ Global GUI popup prevention activated for all tests")