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
def create_widget_mock(**kwargs):
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
    
    # Support initialization values
    if 'value' in kwargs:
        widget_mock.get = Mock(return_value=kwargs['value'])
    
    return widget_mock

mock_tkinter = Mock()
mock_tkinter.messagebox = mock_messagebox
mock_tkinter.Tk = Mock(return_value=create_widget_mock())
mock_tkinter.Entry = Mock(return_value=create_widget_mock())
mock_tkinter.Text = Mock(return_value=create_widget_mock())  
mock_tkinter.Frame = Mock(return_value=create_widget_mock())
mock_tkinter.Label = Mock(return_value=create_widget_mock())
mock_tkinter.Button = Mock(return_value=create_widget_mock())
mock_tkinter.StringVar = Mock(return_value=create_widget_mock())
mock_tkinter.BooleanVar = Mock(return_value=create_widget_mock())
mock_tkinter.Checkbutton = Mock(return_value=create_widget_mock())
mock_tkinter.END = "end"
mock_tkinter.TclError = Exception  # Mock TclError as a regular Exception

# Install GUI mocks globally to prevent ANY GUI popups during testing
# Configure ttk mock
mock_ttk = Mock()
mock_ttk.Progressbar = Mock(return_value=create_widget_mock())
mock_ttk.Combobox = Mock(return_value=create_widget_mock())
mock_ttk.Style = Mock(return_value=Mock())

# Configure scrolledtext mock
mock_scrolledtext = Mock()
mock_scrolledtext.ScrolledText = Mock(return_value=create_widget_mock())

sys.modules['tkinter'] = mock_tkinter
sys.modules['tkinter.messagebox'] = mock_messagebox
sys.modules['tkinter.ttk'] = mock_ttk
sys.modules['tkinter.scrolledtext'] = mock_scrolledtext

# Mock crypto libraries to allow tests to run without actual crypto dependencies
mock_pycardano = MagicMock()
mock_pycardano.key = MagicMock()

# Create proper ExtendedSigningKey mock that returns JSON strings
mock_extended_signing_key_class = MagicMock()
mock_payment_key = MagicMock()
mock_stake_key = MagicMock()
mock_payment_key.to_json.return_value = '{"type": "PaymentExtendedSigningKeyShelley_ed25519", "description": "Payment Signing Key", "cborHex": "5880abcdef"}'
mock_stake_key.to_json.return_value = '{"type": "StakeExtendedSigningKeyShelley_ed25519", "description": "Stake Signing Key", "cborHex": "5880123456"}'

# Configure the class mock to return appropriate instances
def mock_from_hdwallet(wallet):
    # Create a new mock instance each time that returns a proper string
    mock_instance = Mock()
    mock_instance.to_json.return_value = '{"type": "PaymentExtendedSigningKeyShelley_ed25519", "description": "Payment Signing Key", "cborHex": "5880abcdef"}'
    return mock_instance

mock_extended_signing_key_class.from_hdwallet.side_effect = mock_from_hdwallet
mock_pycardano.key.ExtendedSigningKey = mock_extended_signing_key_class

# Create mock HDWallet for Cardano tests
mock_derived_key = MagicMock()
# Set public_key as bytes with proper length support
test_public_key = b'test_public_key_32_bytes_long_abc'  # 32 bytes
mock_derived_key.public_key = test_public_key
# Ensure the derived key itself also has length support
mock_derived_key.__len__ = Mock(return_value=32)

mock_hdwallet = MagicMock()
mock_hdwallet.derive_from_path = Mock(return_value=mock_derived_key)
mock_pycardano.HDWallet = MagicMock()
mock_pycardano.HDWallet.from_mnemonic = Mock(return_value=mock_hdwallet)

# Create mock for Bitcoin libraries
mock_bitcoinlib = MagicMock()
mock_bitcoinlib.keys = MagicMock()

# Create mock HDKey for Bitcoin tests
mock_bitcoin_hdkey = MagicMock()
mock_bitcoin_hdkey.address = Mock(return_value="1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2")
# Make the address() callable return the address string directly
mock_bitcoin_hdkey.address = lambda: "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
# Add WIF key generation
mock_bitcoin_hdkey.wif = lambda: "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ"

mock_bitcoinlib.keys.HDKey = MagicMock()
mock_bitcoinlib.keys.HDKey.from_seed = Mock(return_value=mock_bitcoin_hdkey)
mock_bitcoin_hdkey.subkey_for_path = Mock(return_value=mock_bitcoin_hdkey)

# Mock base58 for address and WIF validation
mock_base58 = MagicMock()
def mock_b58decode_check(data):
    """Mock base58 decode that validates Bitcoin addresses and WIF keys"""
    # Bitcoin addresses
    if data.startswith('1') and len(data) >= 25:
        return b'\x00' + b'0' * 20  # P2PKH format
    elif data.startswith('3') and len(data) >= 25:
        return b'\x05' + b'0' * 20  # P2SH format
    elif data.startswith('bc1') and len(data) >= 14:
        return b'0' * 22  # Bech32 format
    # WIF private keys
    elif data.startswith('5') and len(data) == 51:
        return b'\x80' + b'0' * 32  # Uncompressed WIF
    elif (data.startswith('K') or data.startswith('L')) and len(data) == 52:
        return b'\x80' + b'0' * 32 + b'\x01'  # Compressed WIF
    else:
        raise ValueError("Invalid data")

mock_base58.b58decode_check = Mock(side_effect=mock_b58decode_check)

sys.modules['pycardano'] = mock_pycardano
sys.modules['pycardano.key'] = mock_pycardano.key
sys.modules['bitcoinlib'] = mock_bitcoinlib
sys.modules['bitcoinlib.keys'] = mock_bitcoinlib.keys
sys.modules['base58'] = mock_base58

# Configure mnemonic module mock to return proper boolean values for check() method
def mock_check_seed(phrase):
    """Mock seed phrase validation that returns False for invalid phrases"""
    if not phrase or not phrase.strip():
        return False
    words = phrase.strip().split()
    # Return False for obviously invalid phrases
    if 'invalid' in phrase.lower():
        return False
    # For testing purposes, accept any reasonable length including test phrases
    if len(words) < 3:
        return False
    # Special handling for test phrases
    if "valid seed phrase" in phrase:
        return True
    if len(words) in [12, 15, 18, 21, 24]:
        return True
    # For common test scenarios
    if "abandon" in phrase and len(words) >= 12:
        return True
    return False

def mock_to_seed(phrase, passphrase=""):
    """Mock seed generation that returns realistic 64-byte seed"""
    # Return deterministic but different seeds based on phrase+passphrase combination
    import hashlib
    combined = phrase + str(passphrase)
    seed_hash = hashlib.sha512(combined.encode('utf-8')).digest()
    return seed_hash  # This is exactly 64 bytes

mock_mnemonic_module = MagicMock()
mock_mnemonic_instance = MagicMock()
mock_mnemonic_instance.check = Mock(side_effect=mock_check_seed)
mock_mnemonic_instance.to_seed = Mock(side_effect=mock_to_seed)
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