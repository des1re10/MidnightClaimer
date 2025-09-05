#!/usr/bin/env python3
"""
Tests for service layer components
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os

# Mock the dependencies that might not be available in test environment
with patch.dict('sys.modules', {
    'pycardano': MagicMock(),
    'pycardano.HDWallet': MagicMock(),
    'pycardano.PaymentVerificationKey': MagicMock(),
    'pycardano.Address': MagicMock(),
    'pycardano.Network': MagicMock(),
    'pycardano.key': MagicMock(),
    'bitcoinlib': MagicMock(),
    'bitcoinlib.keys': MagicMock(),
    'bitcoinlib.wallets': MagicMock(),
    'mnemonic': MagicMock()
}):
    from Src.services.cardano_service import CardanoService
    from Src.services.bitcoin_service import BitcoinService

class TestCardanoService(unittest.TestCase):
    """Tests for CardanoService"""
    
    def setUp(self):
        self.service = CardanoService()
    
    def test_detect_address_type(self):
        """Test address type detection"""
        # Use valid full addresses for testing
        valid_shelley = "addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgse35a3x"
        valid_byron_ae2 = "Ae2tdPwUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodpMAi"
        valid_byron_ddz = "DdzFFzCqrhtAvNhKx3gy7XTdqadZYHqzqLNjBaLKqMGXJHJQbJJfKHJp9k1ndVJFaC7Gq1tCGjQNqJVvwGzqQu5qKzNdkgqN5v8a"
        
        self.assertEqual(self.service.detect_address_type(valid_shelley), "shelley")
        self.assertEqual(self.service.detect_address_type(valid_byron_ae2), "byron")
        self.assertEqual(self.service.detect_address_type(valid_byron_ddz), "byron")
        
        # Test invalid addresses should raise ValueError  
        with self.assertRaises(ValueError):
            self.service.detect_address_type("unknown123")
    
    def test_validate_seed_phrase(self):
        """Test seed phrase validation - uses global mnemonic mock from conftest.py"""
        # Test valid seed phrase (mock returns True by default for valid phrases)
        self.assertTrue(self.service.validate_seed_phrase("valid seed phrase"))
        
        # Test invalid seed phrase (mock returns False for phrases with 'invalid')
        self.assertFalse(self.service.validate_seed_phrase("invalid seed"))
        
        # Test empty phrase
        self.assertFalse(self.service.validate_seed_phrase(""))
        
        # Test wrong word count
        self.assertFalse(self.service.validate_seed_phrase("only five words here"))
    
    def test_create_result(self):
        """Test result creation"""
        # Use a valid address for testing
        valid_address = "addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgse35a3x"
        result = self.service._create_result(
            0, 0, 5, "m/1852'/1815'/0'/0/0", "m/1852'/1815'/0'/2/5",
            Mock(), Mock(), valid_address, "payment_stake",
            "test_scenario", "test_passphrase"
        )
        
        self.assertEqual(result['account'], 0)
        self.assertEqual(result['stake_index'], 5)
        self.assertEqual(result['payment_path'], "m/1852'/1815'/0'/0/0")
        self.assertEqual(result['scenario_name'], "test_scenario")
    
    def test_extract_keys(self):
        """Test key extraction"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Mock derivation info
            valid_address = "addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgse35a3x"
            derivation_info = {
                'address': valid_address,
                'derived_payment_wallet': Mock(),
                'derived_stake_wallet': Mock(),
                'address_type': 'payment_stake'
            }
            
            # Mock ExtendedSigningKey
            with patch('Src.services.cardano_service.ExtendedSigningKey') as mock_esk:
                mock_payment_key = Mock()
                mock_stake_key = Mock()
                mock_payment_key.to_json.return_value = '{"payment": "key"}'
                mock_stake_key.to_json.return_value = '{"stake": "key"}'
                
                mock_esk.from_hdwallet.side_effect = [mock_payment_key, mock_stake_key]
                
                result = self.service.extract_keys(derivation_info, output_dir)
                
                self.assertIn('payment_key_file', result)
                self.assertIn('stake_key_file', result)
                self.assertEqual(result['address'], 'addr1test123456')

class TestBitcoinService(unittest.TestCase):
    """Tests for BitcoinService"""
    
    def setUp(self):
        self.service = BitcoinService()
    
    def test_detect_address_type(self):
        """Test Bitcoin address type detection"""
        self.assertEqual(self.service.detect_address_type("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"), "legacy")
        self.assertEqual(self.service.detect_address_type("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"), "segwit")
        self.assertEqual(self.service.detect_address_type("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"), "native_segwit")
        
        with self.assertRaises(ValueError):
            self.service.detect_address_type("invalid_address")
    
    def test_get_derivation_path(self):
        """Test derivation path generation"""
        self.assertEqual(
            self.service.get_derivation_path("legacy", 0, 0, 0),
            "m/44'/0'/0'/0/0"
        )
        self.assertEqual(
            self.service.get_derivation_path("segwit", 1, 1, 5),
            "m/49'/0'/1'/1/5"
        )
        self.assertEqual(
            self.service.get_derivation_path("native_segwit", 0, 0, 10),
            "m/84'/0'/0'/0/10"
        )
        
        with self.assertRaises(ValueError):
            self.service.get_derivation_path("invalid", 0, 0, 0)
    
    def test_validate_seed_phrase(self):
        """Test seed phrase validation - uses global mnemonic mock from conftest.py"""
        # Test valid seed phrase (mock returns True by default for valid phrases)
        self.assertTrue(self.service.validate_seed_phrase("valid seed phrase"))
        
        # Test invalid seed phrase (mock returns False for phrases with 'invalid')
        self.assertFalse(self.service.validate_seed_phrase("invalid seed"))
        
        # Test empty phrase
        self.assertFalse(self.service.validate_seed_phrase(""))
        
        # Test wrong word count
        self.assertFalse(self.service.validate_seed_phrase("only five words here"))
    
    def test_extract_private_key(self):
        """Test private key extraction"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Use a valid WIF key for testing
            valid_wif = "L1aW4aubDFB7yfras2S1mN3bqg9nwySY8nkoLmJebSLD5BWv3ENZ"
            derivation_info = {
                'derivation_result': {
                    'address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
                    'private_key_wif': valid_wif
                },
                'address_type': 'legacy',
                'account': 0,
                'address_index': 0
            }
            
            result = self.service.extract_private_key(derivation_info, output_dir)
            
            self.assertIn('wif_file', result)
            self.assertEqual(result['address'], '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa')
            
            # Verify file was created
            wif_file = Path(result['wif_file'])
            self.assertTrue(wif_file.exists())
            
            # Verify file contents
            with open(wif_file, 'r') as f:
                content = f.read()
                self.assertEqual(content, valid_wif)

if __name__ == '__main__':
    unittest.main()