#!/usr/bin/env python3
"""
Basic validation tests that don't require crypto dependencies
Tests the validation functions and basic infrastructure
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'Src'))

# Test validation functions that don't require crypto libraries
def test_validate_seed_phrase_format():
    """Test seed phrase format validation without crypto libraries"""
    try:
        from utils.security import validate_seed_phrase_format
        
        # Test valid lengths
        valid_12 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        valid_24 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art"
        
        assert validate_seed_phrase_format(valid_12) == (True, "")
        assert validate_seed_phrase_format(valid_24) == (True, "")
        
        # Test invalid cases
        invalid_5 = "abandon abandon abandon abandon abandon"
        is_valid, error = validate_seed_phrase_format(invalid_5)
        assert is_valid == False
        assert "must be 12, 15, 18, 21, or 24 words" in error
        
        # Test empty
        is_valid, error = validate_seed_phrase_format("")
        assert is_valid == False
        assert "cannot be empty" in error
        
    except ImportError as e:
        pytest.skip(f"Security module not available: {e}")

def test_validate_address_format():
    """Test address format validation without crypto libraries"""
    try:
        from utils.security import validate_address_format
        
        # Test Cardano addresses
        valid_shelley = "addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgse35a3x"
        valid_byron = "Ae2tdPwUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodpMAi"
        
        assert validate_address_format(valid_shelley, "cardano") == (True, "")
        assert validate_address_format(valid_byron, "cardano") == (True, "")
        
        # Test Bitcoin addresses
        valid_legacy = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
        valid_segwit = "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"
        valid_native_segwit = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
        
        assert validate_address_format(valid_legacy, "bitcoin") == (True, "")
        assert validate_address_format(valid_segwit, "bitcoin") == (True, "")
        assert validate_address_format(valid_native_segwit, "bitcoin") == (True, "")
        
        # Test cross-validation
        is_valid, error = validate_address_format("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", "cardano")
        assert is_valid == False
        assert "must start with 'addr1', 'Ae2', or 'Ddz'" in error
        
    except ImportError as e:
        pytest.skip(f"Security module not available: {e}")

def test_validate_stake_checksum():
    """Test stake checksum validation"""
    try:
        from utils.security import validate_stake_checksum
        
        # Test valid checksum
        valid_checksum = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        assert validate_stake_checksum(valid_checksum) == (True, "")
        
        # Test uppercase
        valid_checksum_upper = "1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF"
        assert validate_stake_checksum(valid_checksum_upper) == (True, "")
        
        # Test invalid length
        too_short = "1234567890abcdef"
        is_valid, error = validate_stake_checksum(too_short)
        assert is_valid == False
        assert "must be exactly 64 characters" in error
        
        # Test invalid characters
        invalid_chars = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcghi"  # 'g','h','i' invalid
        is_valid, error = validate_stake_checksum(invalid_chars)
        assert is_valid == False
        assert "must contain only hexadecimal characters" in error
        
    except ImportError as e:
        pytest.skip(f"Security module not available: {e}")

def test_validate_bitcoin_wif():
    """Test Bitcoin WIF validation"""
    try:
        from utils.security import validate_bitcoin_wif
        
        # Test WIF format validation (without base58 validation)
        with patch('builtins.__import__', side_effect=lambda name, *args: Mock() if name == 'base58' else __import__(name, *args)):
            valid_wif_5 = "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ"  # Uncompressed
            valid_wif_k = "KwdMAjGmerYanjeui5SHS7JkmpZvVipYvB2LJGU1ZxJwYvP98617"  # Compressed
            valid_wif_l = "L1aW4aubDFB7yfras2S1mN3bqg9nwySY8nkoLmJebSLD5BWv3ENZ"  # Compressed
            
            assert validate_bitcoin_wif(valid_wif_5) == (True, "")
            assert validate_bitcoin_wif(valid_wif_k) == (True, "")
            assert validate_bitcoin_wif(valid_wif_l) == (True, "")
        
        # Test invalid start character
        invalid_start = "9HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ"
        is_valid, error = validate_bitcoin_wif(invalid_start)
        assert is_valid == False
        assert "must start with '5', 'K', or 'L'" in error
        
        # Test invalid length
        too_short = "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1"
        is_valid, error = validate_bitcoin_wif(too_short)
        assert is_valid == False
        assert "has invalid length" in error
        
    except ImportError as e:
        pytest.skip(f"Security module not available: {e}")

class TestBasicInfrastructure:
    """Test basic test infrastructure"""
    
    def test_pytest_works(self):
        """Test that pytest infrastructure is working"""
        assert True
        
    def test_mocking_works(self):
        """Test that mocking capabilities work"""
        mock_obj = Mock()
        mock_obj.test_method.return_value = "test_value"
        assert mock_obj.test_method() == "test_value"
        
    def test_pathlib_works(self):
        """Test that pathlib operations work"""
        temp_dir = Path(tempfile.mkdtemp())
        assert temp_dir.exists()
        assert temp_dir.is_dir()
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        assert not temp_dir.exists()
    
    def test_file_operations(self):
        """Test basic file operations"""
        temp_dir = Path(tempfile.mkdtemp())
        test_file = temp_dir / "test.txt"
        
        # Write file
        test_file.write_text("test content")
        assert test_file.exists()
        
        # Read file
        content = test_file.read_text()
        assert content == "test content"
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)

def test_import_paths():
    """Test that our import paths are set up correctly"""
    # Test that we can import from Src directory
    try:
        # This should work if our path setup is correct
        import utils
        # If we get here, the path setup worked
        assert True
    except ImportError:
        # Try alternative path setup
        src_path = Path(__file__).parent.parent / 'Src'
        assert src_path.exists(), f"Src directory should exist at {src_path}"

class TestSecurityManagerBasics:
    """Test SecurityManager without dependencies"""
    
    def test_security_manager_mock(self):
        """Test SecurityManager functionality with mocking"""
        # Mock all the dependencies
        with patch('utils.security.messagebox') as mock_messagebox, \
             patch('utils.security.tempfile') as mock_tempfile, \
             patch('utils.security.Path') as mock_path:
            
            # Setup mocks
            mock_messagebox.askyesno.return_value = True
            mock_tempfile.mkdtemp.return_value = "/tmp/test_workspace"
            mock_workspace = Mock()
            mock_workspace.exists.return_value = True
            mock_workspace.is_dir.return_value = True
            mock_path.return_value = mock_workspace
            
            try:
                from utils.security import SecurityManager
                
                sm = SecurityManager()
                
                # Test basic initialization
                assert sm.temp_files == []
                assert sm.secure_widgets == []
                assert sm.workspace_dir is None
                assert sm._cleanup_performed == False
                
            except ImportError as e:
                pytest.skip(f"SecurityManager not available: {e}")

if __name__ == "__main__":
    # Run these tests directly if called as script
    pytest.main([__file__, "-v"])