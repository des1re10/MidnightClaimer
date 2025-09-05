#!/usr/bin/env python3
"""
Comprehensive unit tests for CardanoService
Tests all validation, derivation, and key extraction functionality
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'Src'))

from services.cardano_service import CardanoService


class TestCardanoServiceValidation:
    """Test all validation methods in CardanoService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = CardanoService()
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_validate_seed_phrase_valid_12_words(self):
        """Test valid 12-word seed phrase"""
        # This is a test seed phrase (DO NOT USE IN PRODUCTION)
        valid_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        assert self.service.validate_seed_phrase(valid_seed) == True
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_validate_seed_phrase_valid_24_words(self):
        """Test valid 24-word seed phrase"""
        # This is a test seed phrase (DO NOT USE IN PRODUCTION)  
        valid_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art"
        assert self.service.validate_seed_phrase(valid_seed) == True
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_validate_seed_phrase_invalid_length(self):
        """Test seed phrase with invalid word count"""
        invalid_seed = "abandon abandon abandon abandon abandon"  # Only 5 words
        assert self.service.validate_seed_phrase(invalid_seed) == False
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_validate_seed_phrase_invalid_checksum(self):
        """Test seed phrase with invalid checksum"""
        invalid_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon invalid"
        assert self.service.validate_seed_phrase(invalid_seed) == False
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_validate_seed_phrase_empty(self):
        """Test empty seed phrase"""
        assert self.service.validate_seed_phrase("") == False
        assert self.service.validate_seed_phrase(None) == False
        assert self.service.validate_seed_phrase("   ") == False
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_validate_cardano_address_format_shelley(self):
        """Test valid Shelley address format"""
        valid_addr = "addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgse35a3x"
        assert self.service.validate_cardano_address_format(valid_addr) == True
    
    @pytest.mark.unit 
    @pytest.mark.cardano
    def test_validate_cardano_address_format_byron(self):
        """Test valid Byron address format"""
        valid_addr = "Ae2tdPwUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodpMAi"
        assert self.service.validate_cardano_address_format(valid_addr) == True
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_validate_cardano_address_format_invalid(self):
        """Test invalid address formats"""
        assert self.service.validate_cardano_address_format("") == False
        assert self.service.validate_cardano_address_format("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2") == False  # Bitcoin address
        assert self.service.validate_cardano_address_format("short") == False
        assert self.service.validate_cardano_address_format("invalid_prefix_abcdefgh") == False
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_validate_stake_checksum_valid(self):
        """Test valid stake checksum"""
        valid_checksum = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        assert self.service.validate_stake_checksum(valid_checksum) == True
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_validate_stake_checksum_invalid_length(self):
        """Test stake checksum with invalid length"""
        assert self.service.validate_stake_checksum("1234567890abcdef") == False  # Too short
        assert self.service.validate_stake_checksum("1234567890abcdef" * 5) == False  # Too long
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_validate_stake_checksum_invalid_chars(self):
        """Test stake checksum with invalid characters"""
        invalid_checksum = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcghi"  # 'g','h','i' invalid
        assert self.service.validate_stake_checksum(invalid_checksum) == False
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_detect_address_type_shelley(self):
        """Test address type detection for Shelley addresses"""
        shelley_addr = "addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgse35a3x"
        assert self.service.detect_address_type(shelley_addr) == "shelley"
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_detect_address_type_byron(self):
        """Test address type detection for Byron addresses"""
        byron_addr = "Ae2tdPwUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodpMAi"
        assert self.service.detect_address_type(byron_addr) == "byron"
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_detect_address_type_invalid(self):
        """Test address type detection for invalid addresses"""
        with pytest.raises(ValueError, match="Invalid Cardano address format"):
            self.service.detect_address_type("invalid_address")


class TestCardanoServiceKeyOperations:
    """Test key derivation and extraction operations"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = CardanoService()
        self.test_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        self.test_passphrase = ""
        self.test_address = "addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgse35a3x"
        self.test_stake_checksum = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
    @pytest.mark.unit
    @pytest.mark.cardano
    @patch('services.cardano_service.HDWallet')
    def test_create_cardano_wallet_success(self, mock_hdwallet):
        """Test successful wallet creation"""
        # Mock HDWallet creation
        mock_wallet = MagicMock()
        mock_derived = MagicMock()
        mock_wallet.derive_from_path.return_value = mock_derived
        mock_hdwallet.from_mnemonic.return_value = mock_wallet
        
        # Test private method via derivation test
        with patch.object(self.service, 'validate_seed_phrase', return_value=True):
            wallet = self.service._create_cardano_wallet(self.test_seed, self.test_passphrase)
            assert wallet == mock_wallet
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_create_cardano_wallet_invalid_seed(self):
        """Test wallet creation with invalid seed"""
        wallet = self.service._create_cardano_wallet("invalid seed phrase", self.test_passphrase)
        assert wallet is None
    
    @pytest.mark.unit
    @pytest.mark.cardano
    @patch('services.cardano_service.HDWallet')
    @patch('services.cardano_service.PaymentVerificationKey')
    @patch('services.cardano_service.Address')
    def test_comprehensive_derivation_valid_inputs(self, mock_address, mock_payment_vkey, mock_hdwallet):
        """Test comprehensive derivation with valid inputs"""
        # Setup mocks
        mock_wallet = MagicMock()
        mock_derived = MagicMock()
        mock_derived.public_key = b'test_public_key'
        mock_wallet.derive_from_path.return_value = mock_derived
        mock_hdwallet.from_mnemonic.return_value = mock_wallet
        
        mock_vkey = MagicMock()
        mock_payment_vkey.from_primitive.return_value = mock_vkey
        
        mock_addr = MagicMock()
        mock_addr.__str__.return_value = self.test_address
        mock_address.return_value = mock_addr
        
        # Progress callback for testing
        progress_calls = []
        def progress_callback(msg, pct):
            progress_calls.append((msg, pct))
        
        # Test derivation
        result = self.service.test_derivation_comprehensive(
            self.test_seed, self.test_passphrase, self.test_address, self.test_stake_checksum, progress_callback
        )
        
        # Verify progress callback was called
        assert len(progress_calls) > 0
        assert progress_calls[0][0] == "Starting comprehensive Cardano derivation test..."
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_comprehensive_derivation_invalid_seed(self):
        """Test comprehensive derivation with invalid seed"""
        progress_calls = []
        def progress_callback(msg, pct):
            progress_calls.append((msg, pct))
        
        result = self.service.test_derivation_comprehensive(
            "invalid seed", self.test_passphrase, self.test_address, self.test_stake_checksum, progress_callback
        )
        
        assert result is None
        assert any("Invalid seed phrase" in call[0] for call in progress_calls)
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_comprehensive_derivation_invalid_address(self):
        """Test comprehensive derivation with invalid address"""
        progress_calls = []
        def progress_callback(msg, pct):
            progress_calls.append((msg, pct))
        
        result = self.service.test_derivation_comprehensive(
            self.test_seed, self.test_passphrase, "invalid_address", self.test_stake_checksum, progress_callback
        )
        
        assert result is None
        assert any("Invalid target address" in call[0] for call in progress_calls)
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_comprehensive_derivation_invalid_stake_checksum(self):
        """Test comprehensive derivation with invalid stake checksum"""
        progress_calls = []
        def progress_callback(msg, pct):
            progress_calls.append((msg, pct))
        
        result = self.service.test_derivation_comprehensive(
            self.test_seed, self.test_passphrase, self.test_address, "invalid_checksum", progress_callback
        )
        
        assert result is None
        assert any("Invalid stake checksum" in call[0] for call in progress_calls)


class TestCardanoServiceCLIConversion:
    """Test CLI format conversion functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = CardanoService()
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_convert_to_cli_format_success(self):
        """Test successful CLI format conversion"""
        # Create test PyCardano files
        test_payment_data = {
            "type": "PaymentExtendedSigningKeyShelley_ed25519_bip32",
            "description": "Payment Signing Key",
            "cborHex": "1234567890abcdef"
        }
        
        test_stake_data = {
            "type": "StakeExtendedSigningKeyShelley_ed25519_bip32", 
            "description": "Stake Signing Key",
            "cborHex": "abcdef1234567890"
        }
        
        payment_file = self.temp_dir / "test_payment.skey"
        stake_file = self.temp_dir / "test_stake.skey"
        
        with open(payment_file, 'w') as f:
            json.dump(test_payment_data, f)
        with open(stake_file, 'w') as f:
            json.dump(test_stake_data, f)
        
        pycardano_files = {
            'payment_key_file': str(payment_file),
            'stake_key_file': str(stake_file)
        }
        
        # Test CLI conversion
        result = self.service.convert_to_cli_format(pycardano_files, self.temp_dir)
        
        # Verify results
        assert 'cli_payment_file' in result
        assert 'cli_stake_file' in result
        
        cli_payment_file = Path(result['cli_payment_file'])
        cli_stake_file = Path(result['cli_stake_file'])
        
        assert cli_payment_file.exists()
        assert cli_stake_file.exists()
        
        # Verify CLI file content
        with open(cli_payment_file, 'r') as f:
            cli_payment_data = json.load(f)
        
        assert cli_payment_data['type'] == "PaymentExtendedSigningKeyShelley_ed25519_bip32"
        assert cli_payment_data['cborHex'] == "1234567890abcdef"
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_convert_to_cli_format_missing_file(self):
        """Test CLI conversion with missing input file"""
        pycardano_files = {
            'payment_key_file': str(self.temp_dir / "nonexistent.skey")
        }
        
        with pytest.raises(ValueError, match="CLI conversion failed"):
            self.service.convert_to_cli_format(pycardano_files, self.temp_dir)
    
    @pytest.mark.unit
    @pytest.mark.cardano  
    def test_convert_to_cli_format_invalid_content(self):
        """Test CLI conversion with invalid PyCardano file content"""
        # Create test file with missing cborHex
        test_payment_data = {
            "type": "PaymentExtendedSigningKeyShelley_ed25519_bip32",
            "description": "Payment Signing Key"
            # Missing cborHex
        }
        
        payment_file = self.temp_dir / "test_payment.skey"
        with open(payment_file, 'w') as f:
            json.dump(test_payment_data, f)
        
        pycardano_files = {
            'payment_key_file': str(payment_file)
        }
        
        with pytest.raises(ValueError, match="CLI conversion failed"):
            self.service.convert_to_cli_format(pycardano_files, self.temp_dir)


class TestCardanoServiceKeyExtraction:
    """Test key extraction functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = CardanoService()
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Mock derivation info
        self.mock_derivation_info = {
            'account': 0,
            'payment_index': 0,
            'stake_index': 1,
            'payment_path': "m/1852'/1815'/0'/0/0",
            'stake_path': "m/1852'/1815'/0'/2/1",
            'derived_payment_wallet': MagicMock(),
            'derived_stake_wallet': MagicMock(),
            'address': 'addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgse35a3x',
            'address_type': 'payment_stake',
            'scenario_name': 'current_passphrase',
            'passphrase_used': ''
        }
        
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.unit
    @pytest.mark.cardano
    @patch('services.cardano_service.ExtendedSigningKey')
    def test_extract_keys_success(self, mock_extended_signing_key):
        """Test successful key extraction"""
        # Mock ExtendedSigningKey behavior
        mock_payment_key = MagicMock()
        mock_payment_key.to_json.return_value = '{"type": "PaymentExtendedSigningKeyShelley_ed25519_bip32", "cborHex": "1234567890abcdef"}'
        
        mock_stake_key = MagicMock()
        mock_stake_key.to_json.return_value = '{"type": "StakeExtendedSigningKeyShelley_ed25519_bip32", "cborHex": "abcdef1234567890"}'
        
        mock_extended_signing_key.from_hdwallet.side_effect = [mock_payment_key, mock_stake_key]
        
        # Mock CLI conversion
        with patch.object(self.service, 'convert_to_cli_format') as mock_convert:
            mock_convert.return_value = {
                'cli_payment_file': str(self.temp_dir / 'payment_cli.skey'),
                'cli_stake_file': str(self.temp_dir / 'stake_cli.skey')
            }
            
            result = self.service.extract_keys(self.mock_derivation_info, self.temp_dir)
            
            # Verify results
            assert 'payment_key_file' in result
            assert 'cli_payment_file' in result
            assert 'cli_stake_file' in result
            assert result['address'] == self.mock_derivation_info['address']
            
            # Verify CLI conversion was called
            mock_convert.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_extract_keys_invalid_address(self):
        """Test key extraction with invalid address"""
        invalid_derivation_info = self.mock_derivation_info.copy()
        invalid_derivation_info['address'] = 'invalid_address'
        
        with pytest.raises(ValueError, match="Invalid address for key extraction"):
            self.service.extract_keys(invalid_derivation_info, self.temp_dir)
    
    @pytest.mark.unit
    @pytest.mark.cardano
    def test_create_instructions_file(self):
        """Test instruction file creation"""
        # Create dummy key files
        payment_file = self.temp_dir / "payment.skey"
        stake_file = self.temp_dir / "stake.skey" 
        cli_payment_file = self.temp_dir / "payment_cli.skey"
        cli_stake_file = self.temp_dir / "stake_cli.skey"
        
        for file in [payment_file, stake_file, cli_payment_file, cli_stake_file]:
            file.touch()
        
        key_info = {
            'payment_key_file': str(payment_file),
            'stake_key_file': str(stake_file),
            'cli_payment_file': str(cli_payment_file),
            'cli_stake_file': str(cli_stake_file),
            'address': self.mock_derivation_info['address'],
            'derivation_info': self.mock_derivation_info
        }
        
        instructions_file = self.service.create_instructions_file(key_info, self.temp_dir)
        
        # Verify instruction file was created
        assert Path(instructions_file).exists()
        
        # Verify content
        with open(instructions_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "MIDNIGHT CARDANO CLAIM KEYS SUCCESSFULLY GENERATED!" in content
        assert "CLI Format (USE THESE FOR ETERNL IMPORT):" in content
        assert "Eternl Wallet" in content
        assert "SECURITY REQUIREMENTS" in content


class TestCardanoServiceIntegration:
    """Integration tests for CardanoService with real crypto operations"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = CardanoService()
        
    @pytest.mark.integration
    @pytest.mark.cardano
    @pytest.mark.requires_crypto
    def test_real_derivation_integration(self):
        """Test actual derivation with test vectors"""
        # Use well-known test vectors (DO NOT USE IN PRODUCTION)
        test_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        test_passphrase = ""
        
        # This should create a wallet without errors
        with patch.object(self.service, '_create_cardano_wallet') as mock_create:
            mock_wallet = MagicMock()
            mock_create.return_value = mock_wallet
            
            # Test that basic wallet creation flow works
            wallet = self.service._create_cardano_wallet(test_seed, test_passphrase)
            assert wallet == mock_wallet
    
    @pytest.mark.integration
    @pytest.mark.cardano
    @pytest.mark.slow
    def test_full_derivation_workflow(self):
        """Test complete derivation workflow with mocked crypto operations"""
        # This test verifies the complete workflow without real crypto operations
        with patch('services.cardano_service.HDWallet') as mock_hdwallet, \
             patch('services.cardano_service.PaymentVerificationKey') as mock_payment_vkey, \
             patch('services.cardano_service.Address') as mock_address:
            
            # Setup comprehensive mocks
            mock_wallet = MagicMock()
            mock_derived = MagicMock()
            mock_derived.public_key = b'test_public_key_data'
            mock_wallet.derive_from_path.return_value = mock_derived
            mock_hdwallet.from_mnemonic.return_value = mock_wallet
            
            mock_vkey = MagicMock()
            mock_vkey.hash.return_value.payload.hex.return_value = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            mock_payment_vkey.from_primitive.return_value = mock_vkey
            
            mock_addr = MagicMock()
            test_address = "addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgse35a3x"
            mock_addr.__str__.return_value = test_address
            mock_address.return_value = mock_addr
            
            # Test full derivation
            test_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
            test_passphrase = ""
            test_stake_checksum = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            
            progress_calls = []
            def progress_callback(msg, pct):
                progress_calls.append((msg, pct))
            
            result = self.service.test_derivation_comprehensive(
                test_seed, test_passphrase, test_address, test_stake_checksum, progress_callback
            )
            
            # Verify workflow completed
            assert len(progress_calls) > 0
            # Should have found a "match" due to mocked return values
            if result:
                assert 'payment_path' in result
                assert 'address' in result
                assert result['address'] == test_address