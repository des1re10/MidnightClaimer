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

# Configure tkinter mock widgets to return empty lists for children methods
def create_widget_mock():
    """Create a properly configured mock widget"""
    widget_mock = Mock()
    widget_mock.winfo_children = Mock(return_value=[])
    widget_mock.destroy = Mock()
    widget_mock.pack = Mock()
    widget_mock.grid = Mock()
    widget_mock.place = Mock()
    widget_mock.configure = Mock()
    widget_mock.get = Mock(return_value="")
    widget_mock.set = Mock()
    widget_mock.cget = Mock(return_value="normal")
    return widget_mock

mock_tkinter = Mock()
mock_tkinter.messagebox = mock_messagebox
mock_tkinter.Tk = Mock(return_value=create_widget_mock())
mock_tkinter.Entry = Mock(side_effect=create_widget_mock)
mock_tkinter.Text = Mock(side_effect=create_widget_mock)
mock_tkinter.Frame = Mock(side_effect=create_widget_mock)
mock_tkinter.Label = Mock(side_effect=create_widget_mock)
mock_tkinter.Button = Mock(side_effect=create_widget_mock)
mock_tkinter.StringVar = Mock(side_effect=create_widget_mock)
mock_tkinter.BooleanVar = Mock(side_effect=create_widget_mock)
mock_tkinter.Checkbutton = Mock(side_effect=create_widget_mock)
mock_tkinter.END = "end"
mock_tkinter.TclError = Exception  # Mock TclError as a regular Exception

# Install GUI mocks globally to prevent ANY GUI popups during testing
# Configure ttk mock
mock_ttk = Mock()
mock_ttk.Progressbar = Mock(side_effect=create_widget_mock)
mock_ttk.Combobox = Mock(side_effect=create_widget_mock)
mock_ttk.Style = Mock(return_value=Mock())

# Configure scrolledtext mock
mock_scrolledtext = Mock()
mock_scrolledtext.ScrolledText = Mock(side_effect=create_widget_mock)

sys.modules['tkinter'] = mock_tkinter
sys.modules['tkinter.messagebox'] = mock_messagebox
sys.modules['tkinter.ttk'] = mock_ttk
sys.modules['tkinter.scrolledtext'] = mock_scrolledtext

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

# Configure mnemonic module mock to return proper boolean values for check() method
def mock_check_seed(phrase):
    """Mock seed phrase validation that returns False for invalid phrases"""
    if not phrase or not phrase.strip():
        return False
    words = phrase.strip().split()
    # Return False for obviously invalid phrases
    if 'invalid' in phrase.lower():
        return False
    if len(words) not in [12, 15, 18, 21, 24]:
        return False
    # Valid test phrases return True
    return True

mock_mnemonic_module = MagicMock()
mock_mnemonic_instance = MagicMock()
mock_mnemonic_instance.check = Mock(side_effect=mock_check_seed)
mock_mnemonic_module.Mnemonic = Mock(return_value=mock_mnemonic_instance)
sys.modules['mnemonic'] = mock_mnemonic_module

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