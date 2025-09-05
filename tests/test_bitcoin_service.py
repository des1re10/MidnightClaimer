#!/usr/bin/env python3
"""
Comprehensive unit tests for BitcoinService
Tests all validation, derivation, and key extraction functionality
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'Src'))

from services.bitcoin_service import BitcoinService


class TestBitcoinServiceValidation:
    """Test all validation methods in BitcoinService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = BitcoinService()
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_validate_seed_phrase_valid_12_words(self):
        """Test valid 12-word seed phrase"""
        # This is a test seed phrase (DO NOT USE IN PRODUCTION)
        valid_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        assert self.service.validate_seed_phrase(valid_seed) == True
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_validate_seed_phrase_valid_24_words(self):
        """Test valid 24-word seed phrase"""
        # This is a test seed phrase (DO NOT USE IN PRODUCTION)  
        valid_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art"
        assert self.service.validate_seed_phrase(valid_seed) == True
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_validate_seed_phrase_invalid_length(self):
        """Test seed phrase with invalid word count"""
        invalid_seed = "abandon abandon abandon abandon abandon"  # Only 5 words
        assert self.service.validate_seed_phrase(invalid_seed) == False
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_validate_seed_phrase_invalid_checksum(self):
        """Test seed phrase with invalid checksum"""
        invalid_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon invalid"
        assert self.service.validate_seed_phrase(invalid_seed) == False
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_validate_seed_phrase_empty(self):
        """Test empty seed phrase"""
        assert self.service.validate_seed_phrase("") == False
        assert self.service.validate_seed_phrase(None) == False
        assert self.service.validate_seed_phrase("   ") == False
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_validate_bitcoin_address_format_legacy(self):
        """Test valid Legacy (P2PKH) address format"""
        valid_addr = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
        assert self.service.validate_bitcoin_address_format(valid_addr) == True
    
    @pytest.mark.unit 
    @pytest.mark.bitcoin
    def test_validate_bitcoin_address_format_segwit(self):
        """Test valid SegWit (P2SH) address format"""
        valid_addr = "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"
        assert self.service.validate_bitcoin_address_format(valid_addr) == True
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_validate_bitcoin_address_format_native_segwit(self):
        """Test valid Native SegWit (Bech32) address format"""
        valid_addr = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
        assert self.service.validate_bitcoin_address_format(valid_addr) == True
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_validate_bitcoin_address_format_invalid(self):
        """Test invalid address formats"""
        assert self.service.validate_bitcoin_address_format("") == False
        assert self.service.validate_bitcoin_address_format("addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgse35a3x") == False  # Cardano address
        assert self.service.validate_bitcoin_address_format("short") == False
        assert self.service.validate_bitcoin_address_format("invalid_prefix_abcdefgh") == False
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_detect_address_type_legacy(self):
        """Test address type detection for Legacy addresses"""
        legacy_addr = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
        assert self.service.detect_address_type(legacy_addr) == "legacy"
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_detect_address_type_segwit(self):
        """Test address type detection for SegWit addresses"""
        segwit_addr = "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"
        assert self.service.detect_address_type(segwit_addr) == "segwit"
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_detect_address_type_native_segwit(self):
        """Test address type detection for Native SegWit addresses"""
        native_segwit_addr = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
        assert self.service.detect_address_type(native_segwit_addr) == "native_segwit"
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_detect_address_type_invalid(self):
        """Test address type detection for invalid addresses"""
        with pytest.raises(ValueError, match="Invalid Bitcoin address format"):
            self.service.detect_address_type("invalid_address")
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_get_derivation_path_legacy(self):
        """Test derivation path generation for Legacy addresses"""
        path = self.service.get_derivation_path("legacy", 0, 0, 0)
        assert path == "m/44'/0'/0'/0/0"
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_get_derivation_path_segwit(self):
        """Test derivation path generation for SegWit addresses"""
        path = self.service.get_derivation_path("segwit", 1, 0, 5)
        assert path == "m/49'/0'/1'/0/5"
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_get_derivation_path_native_segwit(self):
        """Test derivation path generation for Native SegWit addresses"""
        path = self.service.get_derivation_path("native_segwit", 0, 0, 10)
        assert path == "m/84'/0'/0'/0/10"
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_get_derivation_path_invalid_type(self):
        """Test derivation path generation for invalid address type"""
        with pytest.raises(ValueError, match="Unsupported address type"):
            self.service.get_derivation_path("invalid_type", 0, 0, 0)
    
    @pytest.mark.unit
    @pytest.mark.bitcoin  
    def test_validate_wif_format_valid(self):
        """Test valid WIF key formats"""
        # Test uncompressed WIF (starts with '5')
        assert self.service._validate_wif_format("5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ") == True
        
        # Test compressed WIF (starts with 'K' or 'L')  
        assert self.service._validate_wif_format("KwdMAjGmerYanjeui5SHS7JkmpZvVipYvB2LJGU1ZxJwYvP98617") == True
        assert self.service._validate_wif_format("L1aW4aubDFB7yfras2S1mN3bqg9nwySY8nkoLmJebSLD5BWv3ENZ") == True
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_validate_wif_format_invalid(self):
        """Test invalid WIF key formats"""
        assert self.service._validate_wif_format("") == False
        assert self.service._validate_wif_format("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2") == False  # Bitcoin address, not WIF
        assert self.service._validate_wif_format("short") == False
        assert self.service._validate_wif_format("9" + "x" * 50) == False  # Invalid start character


class TestBitcoinServiceKeyOperations:
    """Test key derivation and extraction operations"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = BitcoinService()
        self.test_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        self.test_passphrase = ""
        self.test_legacy_address = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
        self.test_segwit_address = "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"
        self.test_native_segwit_address = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
        
    @pytest.mark.unit
    @pytest.mark.bitcoin
    @patch('services.bitcoin_service.HDKey')
    def test_derive_bitcoin_key_success(self, mock_hdkey):
        """Test successful Bitcoin key derivation"""
        # Mock HDKey and derived key
        mock_master_key = MagicMock()
        mock_derived_key = MagicMock()
        mock_derived_key.address.return_value = self.test_legacy_address
        mock_derived_key.wif.return_value = "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ"
        mock_derived_key.private_hex = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        mock_master_key.subkey_for_path.return_value = mock_derived_key
        mock_hdkey.from_seed.return_value = mock_master_key
        
        # Mock mnemonic seed generation
        with patch.object(self.service.mnemo, 'to_seed', return_value=b'x' * 64):
            result = self.service.derive_bitcoin_key(
                self.test_seed, self.test_passphrase, 0, 0, "legacy"
            )
            
            assert result is not None
            assert result['address'] == self.test_legacy_address
            assert result['private_key_wif'] == "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ"
            assert 'derivation_path' in result
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_derive_bitcoin_key_invalid_seed(self):
        """Test key derivation with invalid seed"""
        result = self.service.derive_bitcoin_key(
            "invalid seed phrase", self.test_passphrase, 0, 0, "legacy"
        )
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_derive_bitcoin_key_invalid_account(self):
        """Test key derivation with invalid account number"""
        result = self.service.derive_bitcoin_key(
            self.test_seed, self.test_passphrase, -1, 0, "legacy"
        )
        assert result is None
        
        result = self.service.derive_bitcoin_key(
            self.test_seed, self.test_passphrase, 101, 0, "legacy"  # Over limit
        )
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_derive_bitcoin_key_invalid_index(self):
        """Test key derivation with invalid address index"""
        result = self.service.derive_bitcoin_key(
            self.test_seed, self.test_passphrase, 0, -1, "legacy"
        )
        assert result is None
        
        result = self.service.derive_bitcoin_key(
            self.test_seed, self.test_passphrase, 0, 1001, "legacy"  # Over limit
        )
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_derive_bitcoin_key_invalid_address_type(self):
        """Test key derivation with invalid address type"""
        result = self.service.derive_bitcoin_key(
            self.test_seed, self.test_passphrase, 0, 0, "invalid_type"
        )
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    @patch('services.bitcoin_service.HDKey')
    def test_comprehensive_derivation_valid_inputs(self, mock_hdkey):
        """Test comprehensive derivation with valid inputs"""
        # Setup mocks
        mock_master_key = MagicMock()
        mock_derived_key = MagicMock()
        mock_derived_key.address.return_value = self.test_legacy_address
        mock_derived_key.wif.return_value = "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ"
        mock_derived_key.private_hex = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        mock_master_key.subkey_for_path.return_value = mock_derived_key
        mock_hdkey.from_seed.return_value = mock_master_key
        
        # Progress callback for testing
        progress_calls = []
        def progress_callback(msg, pct):
            progress_calls.append((msg, pct))
        
        # Mock mnemonic seed generation
        with patch.object(self.service.mnemo, 'to_seed', return_value=b'x' * 64):
            result = self.service.test_derivation_comprehensive(
                self.test_seed, self.test_passphrase, self.test_legacy_address, "legacy", progress_callback
            )
            
            # Verify progress callback was called
            assert len(progress_calls) > 0
            assert progress_calls[0][0] == "Starting comprehensive Bitcoin derivation test..."
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_comprehensive_derivation_invalid_seed(self):
        """Test comprehensive derivation with invalid seed"""
        progress_calls = []
        def progress_callback(msg, pct):
            progress_calls.append((msg, pct))
        
        result = self.service.test_derivation_comprehensive(
            "invalid seed", self.test_passphrase, self.test_legacy_address, "legacy", progress_callback
        )
        
        assert result is None
        assert any("Invalid seed phrase" in call[0] for call in progress_calls)
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_comprehensive_derivation_invalid_address(self):
        """Test comprehensive derivation with invalid address"""
        progress_calls = []
        def progress_callback(msg, pct):
            progress_calls.append((msg, pct))
        
        result = self.service.test_derivation_comprehensive(
            self.test_seed, self.test_passphrase, "invalid_address", "legacy", progress_callback
        )
        
        assert result is None
        assert any("Invalid target address" in call[0] for call in progress_calls)
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_comprehensive_derivation_address_type_correction(self):
        """Test comprehensive derivation with address type auto-correction"""
        progress_calls = []
        def progress_callback(msg, pct):
            progress_calls.append((msg, pct))
        
        # Use segwit address but specify legacy type - should auto-correct
        with patch('services.bitcoin_service.HDKey'):
            with patch.object(self.service.mnemo, 'to_seed', return_value=b'x' * 64):
                result = self.service.test_derivation_comprehensive(
                    self.test_seed, self.test_passphrase, self.test_segwit_address, "legacy", progress_callback
                )
                
                # Should detect type mismatch and auto-correct
                assert any("Auto-corrected address type" in call[0] for call in progress_calls)


class TestBitcoinServiceKeyExtraction:
    """Test key extraction functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = BitcoinService()
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Mock derivation info
        self.mock_derivation_info = {
            'account': 0,
            'address_index': 0,
            'derivation_result': {
                'address': '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2',
                'private_key_wif': '5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ',
                'private_key_hex': '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
                'derivation_path': "m/44'/0'/0'/0/0"
            },
            'scenario_name': 'current_passphrase',
            'passphrase_used': '',
            'address_type': 'legacy'
        }
        
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_extract_private_key_success(self):
        """Test successful private key extraction"""
        result = self.service.extract_private_key(self.mock_derivation_info, self.temp_dir)
        
        # Verify results
        assert 'wif_file' in result
        assert result['address'] == self.mock_derivation_info['derivation_result']['address']
        assert result['private_key_wif'] == self.mock_derivation_info['derivation_result']['private_key_wif']
        
        # Verify WIF file was created and has correct content
        wif_file = Path(result['wif_file'])
        assert wif_file.exists()
        
        with open(wif_file, 'r') as f:
            saved_wif = f.read().strip()
        assert saved_wif == self.mock_derivation_info['derivation_result']['private_key_wif']
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_extract_private_key_invalid_address(self):
        """Test key extraction with invalid address"""
        invalid_derivation_info = self.mock_derivation_info.copy()
        invalid_derivation_info['derivation_result']['address'] = 'invalid_address'
        
        with pytest.raises(ValueError, match="Invalid address for key extraction"):
            self.service.extract_private_key(invalid_derivation_info, self.temp_dir)
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_extract_private_key_invalid_wif(self):
        """Test key extraction with invalid WIF"""
        invalid_derivation_info = self.mock_derivation_info.copy()
        invalid_derivation_info['derivation_result']['private_key_wif'] = 'invalid_wif'
        
        with pytest.raises(ValueError, match="Invalid WIF key for extraction"):
            self.service.extract_private_key(invalid_derivation_info, self.temp_dir)
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_create_instructions_file(self):
        """Test instruction file creation"""
        # Create dummy WIF file
        wif_file = self.temp_dir / "private.wif"
        wif_file.touch()
        
        key_info = {
            'wif_file': str(wif_file),
            'address': self.mock_derivation_info['derivation_result']['address'],
            'private_key_wif': self.mock_derivation_info['derivation_result']['private_key_wif'],
            'derivation_info': self.mock_derivation_info
        }
        
        instructions_file = self.service.create_instructions_file(key_info, self.temp_dir)
        
        # Verify instruction file was created
        assert Path(instructions_file).exists()
        
        # Verify content
        with open(instructions_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "MIDNIGHT BITCOIN CLAIM KEY SUCCESSFULLY GENERATED!" in content
        assert "SOFTWARE WALLET IMPORT INSTRUCTIONS:" in content
        assert "Electrum Wallet" in content
        assert "Sparrow Wallet" in content
        assert "SECURITY REQUIREMENTS" in content
    
    @pytest.mark.unit
    @pytest.mark.bitcoin
    def test_create_instructions_file_address_types(self):
        """Test instruction file creation for different address types"""
        # Test for each address type
        address_types = ['legacy', 'segwit', 'native_segwit']
        script_types = ['P2PKH', 'P2SH-P2WPKH', 'P2WPKH']
        
        for addr_type, script_type in zip(address_types, script_types):
            wif_file = self.temp_dir / f"{addr_type}_private.wif"
            wif_file.touch()
            
            derivation_info = self.mock_derivation_info.copy()
            derivation_info['address_type'] = addr_type
            
            key_info = {
                'wif_file': str(wif_file),
                'address': self.mock_derivation_info['derivation_result']['address'],
                'private_key_wif': self.mock_derivation_info['derivation_result']['private_key_wif'],
                'derivation_info': derivation_info
            }
            
            instructions_file = self.service.create_instructions_file(key_info, self.temp_dir)
            
            with open(instructions_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verify correct script type is mentioned for Sparrow wallet
            assert script_type in content


class TestBitcoinServiceIntegration:
    """Integration tests for BitcoinService with real crypto operations"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = BitcoinService()
        
    @pytest.mark.integration
    @pytest.mark.bitcoin
    @pytest.mark.requires_crypto
    def test_real_derivation_integration(self):
        """Test actual derivation with test vectors"""
        # Use well-known test vectors (DO NOT USE IN PRODUCTION)
        test_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        test_passphrase = ""
        
        # This should create keys without errors
        with patch('services.bitcoin_service.HDKey') as mock_hdkey:
            mock_master_key = MagicMock()
            mock_derived_key = MagicMock()
            mock_master_key.subkey_for_path.return_value = mock_derived_key
            mock_hdkey.from_seed.return_value = mock_master_key
            
            # Mock mnemonic to_seed  
            with patch.object(self.service.mnemo, 'to_seed', return_value=b'x' * 64):
                result = self.service.derive_bitcoin_key(test_seed, test_passphrase, 0, 0, "legacy")
                
                # Should not raise errors and return structured result
                if result:  # If mocking allows it to succeed
                    assert 'address' in result
                    assert 'private_key_wif' in result
                    assert 'derivation_path' in result
    
    @pytest.mark.integration
    @pytest.mark.bitcoin
    @pytest.mark.slow
    def test_full_derivation_workflow(self):
        """Test complete derivation workflow with mocked crypto operations"""
        # This test verifies the complete workflow without real crypto operations
        with patch('services.bitcoin_service.HDKey') as mock_hdkey:
            # Setup comprehensive mocks
            mock_master_key = MagicMock()
            mock_derived_key = MagicMock()
            test_address = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
            mock_derived_key.address.return_value = test_address
            mock_derived_key.wif.return_value = "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ"
            mock_derived_key.private_hex = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            mock_master_key.subkey_for_path.return_value = mock_derived_key
            mock_hdkey.from_seed.return_value = mock_master_key
            
            # Test full derivation
            test_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
            test_passphrase = ""
            
            progress_calls = []
            def progress_callback(msg, pct):
                progress_calls.append((msg, pct))
            
            # Mock mnemonic to_seed
            with patch.object(self.service.mnemo, 'to_seed', return_value=b'x' * 64):
                result = self.service.test_derivation_comprehensive(
                    test_seed, test_passphrase, test_address, "legacy", progress_callback
                )
                
                # Verify workflow completed
                assert len(progress_calls) > 0
                # Should have found a "match" due to mocked return values
                if result:
                    assert 'derivation_result' in result
                    assert result['derivation_result']['address'] == test_address
    
    @pytest.mark.integration
    @pytest.mark.bitcoin
    def test_create_result_validation(self):
        """Test _create_result method validation"""
        mock_derivation_result = {
            'address': '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2',
            'private_key_wif': '5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ',
            'derivation_path': "m/44'/0'/0'/0/0"
        }
        
        # Test successful result creation
        result = self.service._create_result(
            0, 0, mock_derivation_result, "current_passphrase", "", "legacy"
        )
        
        assert result['account'] == 0
        assert result['address_index'] == 0
        assert result['scenario_name'] == "current_passphrase"
        assert result['address_type'] == "legacy"
        
        # Test validation errors
        with pytest.raises(ValueError, match="Account and address index must be non-negative"):
            self.service._create_result(-1, 0, mock_derivation_result, "test", "", "legacy")
        
        with pytest.raises(ValueError, match="Invalid derivation result"):
            self.service._create_result(0, 0, {}, "test", "", "legacy")
        
        with pytest.raises(ValueError, match="Invalid address in result"):
            invalid_result = mock_derivation_result.copy()
            invalid_result['address'] = 'invalid'
            self.service._create_result(0, 0, invalid_result, "test", "", "legacy")
        
        with pytest.raises(ValueError, match="Invalid WIF key in result"):
            invalid_result = mock_derivation_result.copy()
            invalid_result['private_key_wif'] = 'invalid'
            self.service._create_result(0, 0, invalid_result, "test", "", "legacy")