#!/usr/bin/env python3
"""
Comprehensive unit tests for Security utilities
Tests SecureEntry, SecureText, SecurityManager, and validation functions
"""

import pytest
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'Src'))

from utils.security import (
    SecureEntry, SecureText, SecurityManager,
    validate_seed_phrase_format, validate_address_format, validate_stake_checksum, validate_bitcoin_wif
)


class TestSecureWidgets:
    """Test secure input widgets"""
    
    def setup_method(self):
        """Set up test fixtures with mocked tkinter root"""
        self.root = Mock()
        # Configure the root mock to behave like a tkinter widget
        self.root.destroy = Mock()
        self.root.withdraw = Mock()
    
    @pytest.mark.unit
    @pytest.mark.security
    @patch('utils.security.tk.Entry')
    def test_secure_entry_creation(self, mock_entry):
        """Test SecureEntry widget creation"""
        # Configure the mock Entry class
        mock_entry_instance = Mock()
        mock_entry_instance.get = Mock(return_value="")
        mock_entry_instance.insert = Mock()
        mock_entry_instance.delete = Mock()
        mock_entry.return_value = mock_entry_instance
        
        entry = SecureEntry(self.root)
        assert hasattr(entry, '_secure_content')
        assert entry._secure_content == ""
    
    @pytest.mark.unit
    @pytest.mark.security
    @patch('utils.security.tk.Entry')
    def test_secure_entry_input_tracking(self, mock_entry):
        """Test SecureEntry input tracking"""
        # Configure the mock Entry class
        mock_entry_instance = Mock()
        mock_entry_instance.get = Mock(return_value="test_password")
        mock_entry_instance.insert = Mock()
        mock_entry_instance.delete = Mock()
        mock_entry.return_value = mock_entry_instance
        
        entry = SecureEntry(self.root)
        
        # Simulate typing
        entry.insert(0, "test_password")
        
        # Check that secure content is tracked
        assert entry.get() == "test_password"
        assert entry._secure_content == "test_password"
    
    @pytest.mark.unit
    @pytest.mark.security
    @patch('utils.security.tk.Entry')
    def test_secure_entry_clear(self, mock_entry):
        """Test SecureEntry secure clearing"""
        # Configure the mock Entry class
        mock_entry_instance = Mock()
        mock_entry_instance.get = Mock(return_value="")
        mock_entry_instance.insert = Mock()
        mock_entry_instance.delete = Mock()
        mock_entry.return_value = mock_entry_instance
        
        entry = SecureEntry(self.root)
        entry._secure_content = "sensitive_data"  # Simulate content
        
        # Clear securely
        entry.secure_clear()
        
        # Verify cleared
        assert entry._secure_content == ""
    
    @pytest.mark.unit
    @pytest.mark.security
    @patch('utils.security.tk.Text')
    def test_secure_text_creation(self, mock_text):
        """Test SecureText widget creation"""
        # Configure the mock Text class
        mock_text_instance = Mock()
        mock_text_instance.get = Mock(return_value="")
        mock_text_instance.bind = Mock()
        mock_text_instance.after_idle = Mock()
        mock_text.return_value = mock_text_instance
        
        text = SecureText(self.root)
        assert hasattr(text, '_secure_content')
        assert text._secure_content == ""
    
    @pytest.mark.unit
    @pytest.mark.security
    @patch('utils.security.tk.Text')
    def test_secure_text_input_tracking(self, mock_text):
        """Test SecureText input tracking"""
        # Configure the mock Text class
        mock_text_instance = Mock()
        mock_text_instance.get = Mock(return_value="test seed phrase")
        mock_text_instance.bind = Mock()
        mock_text_instance.after_idle = Mock()
        mock_text_instance.insert = Mock()
        mock_text.return_value = mock_text_instance
        
        text = SecureText(self.root)
        
        # Simulate typing
        text.insert("1.0", "test seed phrase")
        text._update_content()  # Manually trigger content update
        
        # Check that secure content is tracked
        content = text.get("1.0", tk.END)
        assert content == "test seed phrase"
    
    @pytest.mark.unit
    @pytest.mark.security
    @patch('utils.security.tk.Text')
    def test_secure_text_clear(self, mock_text):
        """Test SecureText secure clearing"""
        # Configure the mock Text class
        mock_text_instance = Mock()
        mock_text_instance.get = Mock(return_value="")
        mock_text_instance.bind = Mock()
        mock_text_instance.after_idle = Mock()
        mock_text_instance.insert = Mock()
        mock_text_instance.delete = Mock()
        mock_text.return_value = mock_text_instance
        
        text = SecureText(self.root)
        text._secure_content = "sensitive seed phrase data"  # Simulate content
        
        # Clear securely
        text.secure_clear()
        
        # Verify cleared
        assert text._secure_content == ""


class TestSecurityManager:
    """Test SecurityManager functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.security_manager = SecurityManager()
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_security_manager_initialization(self):
        """Test SecurityManager initialization"""
        sm = SecurityManager()
        assert sm.temp_files == []
        assert sm.secure_widgets == []
        assert sm.workspace_dir is None
        assert sm._cleanup_performed == False
    
    @pytest.mark.unit
    @pytest.mark.security
    @patch('utils.security.messagebox')
    def test_show_memory_warning(self, mock_messagebox):
        """Test memory warning dialog"""
        # Test user accepting warning
        mock_messagebox.askyesno.return_value = True
        result = self.security_manager.show_memory_warning()
        assert result == True
        mock_messagebox.askyesno.assert_called_once()
        
        # Test user rejecting warning
        mock_messagebox.askyesno.return_value = False
        result = self.security_manager.show_memory_warning()
        assert result == False
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_create_secure_workspace(self):
        """Test secure workspace creation"""
        workspace = self.security_manager.create_secure_workspace()
        
        assert workspace.exists()
        assert workspace.is_dir()
        assert "gui_session_" in workspace.name
        assert self.security_manager.workspace_dir == workspace
        
        # Cleanup
        import shutil
        shutil.rmtree(workspace)
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_register_temp_file(self):
        """Test temporary file registration"""
        test_file = self.temp_dir / "test_file.txt"
        test_file.touch()
        
        self.security_manager.register_temp_file(test_file)
        
        assert test_file in self.security_manager.temp_files
        assert len(self.security_manager.temp_files) == 1
        
        # Test duplicate registration (should not add twice)
        self.security_manager.register_temp_file(test_file)
        assert len(self.security_manager.temp_files) == 1
    
    @pytest.mark.unit
    @pytest.mark.security
    @patch('utils.security.tk.Entry')
    def test_register_secure_widget(self, mock_entry):
        """Test secure widget registration"""
        # Configure the mock Entry class
        mock_entry_instance = Mock()
        mock_entry_instance.get = Mock(return_value="")
        mock_entry_instance.insert = Mock()
        mock_entry_instance.delete = Mock()
        mock_entry.return_value = mock_entry_instance
        
        root = Mock()
        root.destroy = Mock()
        root.withdraw = Mock()
        
        widget = SecureEntry(root)
        self.security_manager.register_secure_widget(widget)
        
        assert widget in self.security_manager.secure_widgets
        assert len(self.security_manager.secure_widgets) == 1
        
        # Test duplicate registration (should not add twice)
        self.security_manager.register_secure_widget(widget)
        assert len(self.security_manager.secure_widgets) == 1
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_secure_delete_file(self):
        """Test secure file deletion"""
        # Create test file with content
        test_file = self.temp_dir / "secure_delete_test.txt"
        test_content = "sensitive data that should be overwritten"
        test_file.write_text(test_content)
        
        assert test_file.exists()
        
        # Securely delete the file
        self.security_manager._secure_delete_file(test_file)
        
        # Verify file is deleted
        assert not test_file.exists()
    
    @pytest.mark.unit
    @pytest.mark.security
    @patch('utils.security.messagebox')
    def test_secure_cleanup_with_confirmation(self, mock_messagebox):
        """Test secure cleanup with user confirmation"""
        # Create test file
        test_file = self.temp_dir / "test_cleanup.txt"
        test_file.write_text("test content")
        self.security_manager.register_temp_file(test_file)
        
        # User confirms cleanup
        mock_messagebox.askyesno.return_value = True
        mock_messagebox.showinfo.return_value = None
        
        result = self.security_manager.secure_cleanup()
        
        assert result == True
        assert not test_file.exists()
        assert self.security_manager._cleanup_performed == True
        mock_messagebox.askyesno.assert_called_once()


class TestValidationFunctions:
    """Test validation utility functions"""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_seed_phrase_format_valid(self):
        """Test seed phrase format validation with valid phrases"""
        # Test different valid lengths
        valid_12 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        valid_24 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art"
        
        assert validate_seed_phrase_format(valid_12) == (True, "")
        assert validate_seed_phrase_format(valid_24) == (True, "")
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_seed_phrase_format_invalid_length(self):
        """Test seed phrase format validation with invalid lengths"""
        invalid_5 = "abandon abandon abandon abandon abandon"
        invalid_13 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"  # 13 words
        
        is_valid, error = validate_seed_phrase_format(invalid_5)
        assert is_valid == False
        assert "must be 12, 15, 18, 21, or 24 words" in error
        
        is_valid, error = validate_seed_phrase_format(invalid_13)
        assert is_valid == False
        assert "must be 12, 15, 18, 21, or 24 words" in error
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_address_format_cardano(self):
        """Test Cardano address format validation"""
        valid_shelley = "addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgse35a3x"
        valid_byron = "Ae2tdPwUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodpMAi"
        
        assert validate_address_format(valid_shelley, "cardano") == (True, "")
        assert validate_address_format(valid_byron, "cardano") == (True, "")
        
        # Test invalid Cardano addresses
        is_valid, error = validate_address_format("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", "cardano")
        assert is_valid == False
        assert "must start with 'addr1', 'Ae2', or 'Ddz'" in error
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_address_format_bitcoin(self):
        """Test Bitcoin address format validation"""
        valid_legacy = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
        valid_segwit = "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"
        valid_native_segwit = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
        
        assert validate_address_format(valid_legacy, "bitcoin") == (True, "")
        assert validate_address_format(valid_segwit, "bitcoin") == (True, "")
        assert validate_address_format(valid_native_segwit, "bitcoin") == (True, "")
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_stake_checksum_valid(self):
        """Test stake checksum validation with valid checksums"""
        valid_checksum = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        assert validate_stake_checksum(valid_checksum) == (True, "")
        
        # Test with uppercase
        valid_checksum_upper = "1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF"
        assert validate_stake_checksum(valid_checksum_upper) == (True, "")
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_bitcoin_wif_valid(self):
        """Test Bitcoin WIF validation with valid keys"""
        # These are example WIF formats (not real keys)
        valid_wif_5 = "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ"  # Uncompressed
        valid_wif_k = "KwdMAjGmerYanjeui5SHS7JkmpZvVipYvB2LJGU1ZxJwYvP98617"  # Compressed
        valid_wif_l = "L1aW4aubDFB7yfras2S1mN3bqg9nwySY8nkoLmJebSLD5BWv3ENZ"  # Compressed
        
        # Note: These tests check format only, not actual base58 validity without mock
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'base58' else __import__(name, *args)):
            assert validate_bitcoin_wif(valid_wif_5) == (True, "")
            assert validate_bitcoin_wif(valid_wif_k) == (True, "")
            assert validate_bitcoin_wif(valid_wif_l) == (True, "")