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
# Set public_key as a mock that behaves like bytes with proper length support
test_public_key_data = b'test_public_key_32_bytes_long_abc'  # 32 bytes

# Create a mock public_key that behaves like bytes but supports len()
mock_public_key = Mock()
mock_public_key.__len__ = Mock(return_value=len(test_public_key_data))
mock_public_key.__bytes__ = Mock(return_value=test_public_key_data)
mock_public_key.__getitem__ = Mock(side_effect=lambda i: test_public_key_data[i])
# Make it act like bytes for most operations
for attr_name in ['hex', 'decode']:
    if hasattr(test_public_key_data, attr_name):
        setattr(mock_public_key, attr_name, Mock(return_value=getattr(test_public_key_data, attr_name)()))

mock_derived_key.public_key = mock_public_key
# Ensure the derived key itself also has length support
mock_derived_key.__len__ = Mock(return_value=32)

mock_hdwallet = MagicMock()
mock_hdwallet.derive_from_path = Mock(return_value=mock_derived_key)

# Ensure consistent returns across test runs
def mock_derive_from_path(*args, **kwargs):
    return mock_derived_key

mock_hdwallet.derive_from_path = Mock(side_effect=mock_derive_from_path)
# Ensure the HDWallet always returns the same configured mock
def mock_hdwallet_from_mnemonic(*args, **kwargs):
    return mock_hdwallet

mock_hdwallet_class = MagicMock()
mock_hdwallet_class.from_mnemonic = Mock(side_effect=mock_hdwallet_from_mnemonic)
mock_pycardano.HDWallet = mock_hdwallet_class

# Create mock for Bitcoin libraries
mock_bitcoinlib = MagicMock()
mock_bitcoinlib.keys = MagicMock()

# Create mock HDKey for Bitcoin tests with proper method returns
def create_bitcoin_hdkey_mock(address_type="legacy", derivation_path=None):
    """Create a mock HDKey with proper address and WIF generation"""
    mock_key = MagicMock()
    
    # Generate different addresses based on derivation path to simulate real behavior
    if derivation_path:
        import hashlib
        # Generate a deterministic but unique address based on the path
        path_hash = hashlib.md5(derivation_path.encode()).hexdigest()
        
        # Set private_hex attribute for validation (use first 64 chars of hash repeated)
        private_hex = (path_hash * 2)[:64]
        mock_key.private_hex = private_hex
        
        if address_type == "legacy":
            # Create a valid legacy address format starting with '1'
            # Use the first few characters of hash to make it unique
            unique_part = path_hash[:6]
            fixed_address = f"1{unique_part}BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"[:34]
            mock_key.address = Mock(return_value=fixed_address)
        elif address_type == "segwit":
            # Create a valid segwit address format starting with '3'
            unique_part = path_hash[:6]
            fixed_address = f"3{unique_part}J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"[:34]
            mock_key.address = Mock(return_value=fixed_address)
        else:  # native_segwit
            # Create a valid native segwit address format starting with 'bc1q'
            unique_part = path_hash[:10]
            fixed_address = f"bc1q{unique_part}ar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"[:42]
            mock_key.address = Mock(return_value=fixed_address)
    else:
        # Default addresses (fallback) - need private_hex for these too
        mock_key.private_hex = "a" * 64  # Default private key hex
        
        if address_type == "legacy":
            mock_key.address = Mock(return_value="1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2")
        elif address_type == "segwit":
            mock_key.address = Mock(return_value="3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy")
        else:  # native_segwit
            mock_key.address = Mock(return_value="bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")
    
    # Configure WIF generation (always compressed for newer types)
    if address_type == "legacy":
        mock_key.wif = Mock(return_value="5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ")
    else:
        mock_key.wif = Mock(return_value="L1aW4aubDFB7yfras2S1mN3bqg9nwySY8nkoLmJebSLD5BWv3ENZ")
    
    return mock_key

# Create the main HDKey mock
mock_bitcoin_hdkey = create_bitcoin_hdkey_mock("legacy")

# Create a cache to ensure same path always returns same address
_mock_key_cache = {}

# Configure subkey_for_path to return appropriate mocks based on derivation path
def mock_subkey_for_path(path):
    # Use cache to ensure consistent addresses for same paths
    if path in _mock_key_cache:
        return _mock_key_cache[path]
    
    if "44'" in path:  # Legacy P2PKH
        mock = create_bitcoin_hdkey_mock("legacy", path)
    elif "49'" in path:  # SegWit P2SH-P2WPKH
        mock = create_bitcoin_hdkey_mock("segwit", path)
    elif "84'" in path:  # Native SegWit P2WPKH
        mock = create_bitcoin_hdkey_mock("native_segwit", path)
    else:
        mock = create_bitcoin_hdkey_mock("legacy", path)  # Default fallback
    
    _mock_key_cache[path] = mock
    return mock

mock_bitcoin_hdkey.subkey_for_path = Mock(side_effect=mock_subkey_for_path)

# Ensure the HDKey always returns the same configured mock
def mock_hdkey_from_seed(*args, **kwargs):
    return mock_bitcoin_hdkey

# Configure HDKey as a class-like mock
mock_hdkey_class = MagicMock()
mock_hdkey_class.from_seed = Mock(side_effect=mock_hdkey_from_seed)
mock_bitcoinlib.keys.HDKey = mock_hdkey_class

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
# Also ensure direct attribute access works
mock_pycardano.key = mock_pycardano.key
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
    # Check for known invalid checksum phrases first
    if phrase == "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon":
        return False
    
    if len(words) in [12, 15, 18, 21, 24]:
        return True
    # For common test scenarios - but reject known invalid checksums
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

@pytest.fixture(autouse=True)
def ensure_crypto_mock_consistency():
    """Ensure crypto mocks remain consistently configured across tests.

    Some tests temporarily inject submodule entries like 'pycardano.HDWallet' into
    sys.modules. That can interfere with other tests that import symbols with
    'from pycardano import HDWallet'. Before each test, reset sys.modules to point
    back to our consistent mocks and remove any stray submodule entries.
    """
    import sys

    # Remove any polluted submodule entries so attribute imports work as expected
    for polluted in [
        'pycardano.HDWallet',
        'pycardano.PaymentVerificationKey',
        'pycardano.Address',
        'pycardano.Network',
    ]:
        if polluted in sys.modules:
            del sys.modules[polluted]

    # Reassert our top-level mocked modules
    sys.modules['pycardano'] = mock_pycardano
    sys.modules['pycardano.key'] = mock_pycardano.key
    sys.modules['bitcoinlib'] = mock_bitcoinlib
    sys.modules['bitcoinlib.keys'] = mock_bitcoinlib.keys
    sys.modules['base58'] = mock_base58
    sys.modules['mnemonic'] = mock_mnemonic_module

    # Reset and reconfigure Bitcoin HDKey mock
    mock_bitcoin_hdkey.subkey_for_path = Mock(side_effect=mock_subkey_for_path)
    mock_hdkey_class.from_seed = Mock(side_effect=mock_hdkey_from_seed)

    # Reset and reconfigure Cardano HDWallet mock
    mock_hdwallet.derive_from_path = Mock(side_effect=mock_derive_from_path)
    mock_hdwallet_class.from_mnemonic = Mock(side_effect=mock_hdwallet_from_mnemonic)

    # Ensure the derived key has proper public_key
    mock_derived_key.public_key = mock_public_key

    # Ensure attributes are present on pycardano mock
    mock_pycardano.HDWallet = mock_hdwallet_class

    yield

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
print("Global GUI popup prevention activated for all tests")
