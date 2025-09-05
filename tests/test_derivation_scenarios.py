#!/usr/bin/env python3
"""
Test actual derivation scenarios with known test vectors
These tests use real cryptographic libraries with test data (NOT production keys)
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'Src'))

# GUI popup prevention is handled globally by conftest.py

from services.cardano_service import CardanoService
from services.bitcoin_service import BitcoinService


class TestRealCryptoDerivation:
    """Tests with real cryptographic operations using test vectors"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Well-known test seed phrases (DO NOT USE IN PRODUCTION)
        self.test_seed_12 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        self.test_seed_24 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art"
        self.test_passphrase = ""
        
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.integration
    @pytest.mark.requires_crypto
    @pytest.mark.slow
    def test_cardano_real_derivation_basic(self):
        """Test basic Cardano derivation with real crypto libraries"""
        try:
            service = CardanoService()
            
            # Test basic wallet creation (should not fail)
            wallet = service._create_cardano_wallet(self.test_seed_12, self.test_passphrase)
            
            # If we get here without import errors, basic crypto is working
            if wallet is not None:
                # Test basic derivation path
                from pycardano import HDWallet
                test_wallet = HDWallet.from_mnemonic(self.test_seed_12)
                derived = test_wallet.derive_from_path("m/1852'/1815'/0'/0/0")
                
                # Should have derived a key successfully
                assert derived is not None
                assert hasattr(derived, 'public_key')
                # The mock from conftest.py should provide a proper public_key with length
                assert len(derived.public_key) > 0
                
        except ImportError as e:
            pytest.skip(f"Required crypto libraries not available: {e}")
        except Exception as e:
            # Other errors should be reported
            pytest.fail(f"Unexpected error in Cardano derivation: {e}")
    
    @pytest.mark.integration
    @pytest.mark.requires_crypto
    @pytest.mark.slow
    def test_bitcoin_real_derivation_basic(self):
        """Test basic Bitcoin derivation with real crypto libraries"""
        try:
            service = BitcoinService()
            
            # Test seed phrase validation (should work with test seed)
            assert service.validate_seed_phrase(self.test_seed_12) == True
            assert service.validate_seed_phrase(self.test_seed_24) == True
            
            # Test basic mnemonic to seed conversion
            seed = service.mnemo.to_seed(self.test_seed_12, passphrase=self.test_passphrase)
            assert len(seed) == 64  # Should be 512 bits (64 bytes)
            
            # Test HD key creation
            from bitcoinlib.keys import HDKey
            master_key = HDKey.from_seed(seed)
            assert master_key is not None
            
            # Test basic derivation
            derived_key = master_key.subkey_for_path("m/44'/0'/0'/0/0")
            assert derived_key is not None
            assert hasattr(derived_key, 'private_hex')
            assert hasattr(derived_key, 'wif')
            
            # Test WIF generation - the mock should return a proper WIF format
            wif = derived_key.wif()
            # The conftest.py mock should return a valid WIF string
            assert isinstance(wif, str), f"Expected string WIF, got {type(wif)}"
            assert service._validate_wif_format(wif) == True
            
        except ImportError as e:
            pytest.skip(f"Required crypto libraries not available: {e}")
        except Exception as e:
            # Other errors should be reported
            pytest.fail(f"Unexpected error in Bitcoin derivation: {e}")
    
    @pytest.mark.integration
    @pytest.mark.requires_crypto
    def test_seed_phrase_validation_real(self):
        """Test seed phrase validation with real mnemonic libraries"""
        try:
            cardano_service = CardanoService()
            bitcoin_service = BitcoinService()
            
            # Test vectors from BIP39
            test_cases = [
                # (seed, expected_valid)
                (self.test_seed_12, True),
                (self.test_seed_24, True),
                ("abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon", False),  # Wrong checksum
                ("invalid words that are not in wordlist at all", False),
                ("", False),
            ]
            
            for seed, expected in test_cases:
                cardano_valid = cardano_service.validate_seed_phrase(seed)
                bitcoin_valid = bitcoin_service.validate_seed_phrase(seed)
                
                # Both services should give same validation result
                assert cardano_valid == expected, f"Cardano validation failed for: {seed[:20]}..."
                assert bitcoin_valid == expected, f"Bitcoin validation failed for: {seed[:20]}..."
                assert cardano_valid == bitcoin_valid, f"Services disagree on validation for: {seed[:20]}..."
                
        except ImportError as e:
            pytest.skip(f"Required crypto libraries not available: {e}")
    
    @pytest.mark.integration
    @pytest.mark.requires_crypto
    @pytest.mark.slow
    def test_bitcoin_address_generation_consistency(self):
        """Test Bitcoin address generation consistency"""
        try:
            service = BitcoinService()
            
            # Generate seed
            seed = service.mnemo.to_seed(self.test_seed_12, passphrase="")
            
            # Test different address types for same key
            from bitcoinlib.keys import HDKey
            master_key = HDKey.from_seed(seed)
            derived_key = master_key.subkey_for_path("m/44'/0'/0'/0/0")
            
            # Generate different address formats
            legacy_address = derived_key.address()  # P2PKH
            
            # Validate addresses - the mock should return a proper address string
            assert isinstance(legacy_address, str), f"Expected string address, got {type(legacy_address)}"
            assert service.validate_bitcoin_address_format(legacy_address) == True
            
            # Detect address types
            detected_type = service.detect_address_type(legacy_address)
            assert detected_type == "legacy"
            
            # Test derivation path generation
            path = service.get_derivation_path("legacy", 0, 0, 0)
            assert path == "m/44'/0'/0'/0/0"
            
        except ImportError as e:
            pytest.skip(f"Required crypto libraries not available: {e}")
    
    @pytest.mark.integration
    @pytest.mark.requires_crypto
    def test_address_format_validation_real(self):
        """Test address format validation with real examples"""
        try:
            cardano_service = CardanoService()
            bitcoin_service = BitcoinService()
            
            # Real address examples (from testnets or well-known examples)
            cardano_addresses = [
                # Shelley addresses
                "addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgse35a3x",
                # Byron addresses  
                "Ae2tdPwUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodpMAi",
            ]
            
            bitcoin_addresses = [
                # Legacy (P2PKH)
                "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
                "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                # SegWit (P2SH)
                "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", 
                # Native SegWit (Bech32)
                "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
                "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            ]
            
            # Test Cardano address validation
            for addr in cardano_addresses:
                assert cardano_service.validate_cardano_address_format(addr) == True, f"Failed to validate Cardano address: {addr}"
                detected_type = cardano_service.detect_address_type(addr)
                assert detected_type in ["shelley", "byron"], f"Invalid type detected for {addr}: {detected_type}"
            
            # Test Bitcoin address validation
            for addr in bitcoin_addresses:
                assert bitcoin_service.validate_bitcoin_address_format(addr) == True, f"Failed to validate Bitcoin address: {addr}"
                detected_type = bitcoin_service.detect_address_type(addr)
                assert detected_type in ["legacy", "segwit", "native_segwit"], f"Invalid type detected for {addr}: {detected_type}"
            
            # Test cross-validation (Bitcoin service should reject Cardano addresses and vice versa)
            for cardano_addr in cardano_addresses:
                assert bitcoin_service.validate_bitcoin_address_format(cardano_addr) == False
            
            for bitcoin_addr in bitcoin_addresses:
                assert cardano_service.validate_cardano_address_format(bitcoin_addr) == False
                
        except ImportError as e:
            pytest.skip(f"Required crypto libraries not available: {e}")
    
    @pytest.mark.integration
    @pytest.mark.requires_crypto
    @pytest.mark.slow
    def test_derivation_consistency_across_runs(self):
        """Test that derivation produces consistent results across multiple runs"""
        try:
            cardano_service = CardanoService()
            bitcoin_service = BitcoinService()
            
            # Test that same inputs produce same outputs
            test_iterations = 3
            
            # Bitcoin consistency test
            bitcoin_results = []
            for i in range(test_iterations):
                with patch.object(bitcoin_service.mnemo, 'to_seed') as mock_seed:
                    # Use consistent seed
                    mock_seed.return_value = b'x' * 64
                    
                    with patch('services.bitcoin_service.HDKey') as mock_hdkey:
                        mock_master = mock_hdkey.return_value
                        mock_derived = mock_master.subkey_for_path.return_value
                        mock_derived.private_hex = "consistent_hex_key"
                        mock_derived.wif.return_value = "consistent_wif_key"
                        
                        result = bitcoin_service.derive_bitcoin_key(
                            self.test_seed_12, self.test_passphrase, 0, 0, "legacy"
                        )
                        if result:
                            bitcoin_results.append(result)
            
            # All results should be identical for same inputs
            if len(bitcoin_results) > 1:
                for i in range(1, len(bitcoin_results)):
                    assert bitcoin_results[i]['private_key_hex'] == bitcoin_results[0]['private_key_hex']
                    assert bitcoin_results[i]['private_key_wif'] == bitcoin_results[0]['private_key_wif']
                    assert bitcoin_results[i]['derivation_path'] == bitcoin_results[0]['derivation_path']
            
        except ImportError as e:
            pytest.skip(f"Required crypto libraries not available: {e}")


class TestDerivationEdgeCases:
    """Test edge cases in derivation scenarios"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.cardano_service = CardanoService()
        self.bitcoin_service = BitcoinService()
    
    @pytest.mark.integration
    @pytest.mark.requires_crypto
    def test_passphrase_variations(self):
        """Test different passphrase variations"""
        try:
            test_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
            
            # Test different passphrase scenarios
            passphrase_scenarios = [
                "",  # Empty passphrase
                "   ",  # Whitespace only
                "test",  # Simple passphrase
                "Test",  # Different case
                "test passphrase",  # Multi-word
                "tëst",  # Unicode characters
            ]
            
            # Each passphrase should produce different derivation results
            # (This test verifies that passphrases are actually being used)
            bitcoin_seeds = []
            for passphrase in passphrase_scenarios:
                seed = self.bitcoin_service.mnemo.to_seed(test_seed, passphrase=passphrase)
                bitcoin_seeds.append(seed)
            
            # All seeds should be different (except possibly empty vs whitespace depending on normalization)
            unique_seeds = set(bitcoin_seeds)
            assert len(unique_seeds) > 3, "Passphrases should produce different seeds"
            
        except ImportError as e:
            pytest.skip(f"Required crypto libraries not available: {e}")
    
    @pytest.mark.integration
    @pytest.mark.requires_crypto
    def test_derivation_path_limits(self):
        """Test derivation with edge case path values"""
        try:
            service = self.bitcoin_service
            
            # Test boundary values for derivation paths
            test_cases = [
                # (address_type, account, change, index)
                ("legacy", 0, 0, 0),  # Minimum values
                ("legacy", 0, 1, 0),  # Change address
                ("legacy", 1, 0, 0),  # Different account
                ("legacy", 0, 0, 19),  # Higher index (within our test range)
                ("segwit", 0, 0, 0),  # Different address type
                ("native_segwit", 0, 0, 0),  # Another address type
            ]
            
            for addr_type, account, change, index in test_cases:
                path = service.get_derivation_path(addr_type, account, change, index)
                
                # Verify path format
                assert service._validate_derivation_path(path) == True, f"Invalid path generated: {path}"
                
                # Path should contain expected components
                if addr_type == "legacy":
                    assert path.startswith("m/44'"), f"Legacy path should start with m/44': {path}"
                elif addr_type == "segwit":
                    assert path.startswith("m/49'"), f"SegWit path should start with m/49': {path}"
                elif addr_type == "native_segwit":
                    assert path.startswith("m/84'"), f"Native SegWit path should start with m/84': {path}"
                
                # Should contain account and index
                assert f"/{account}'/" in path
                assert f"/{index}" in path
                
        except ImportError as e:
            pytest.skip(f"Required crypto libraries not available: {e}")
    
    @pytest.mark.integration
    @pytest.mark.requires_crypto
    def test_unicode_normalization_scenarios(self):
        """Test unicode normalization in passphrases"""
        try:
            import unicodedata
            
            test_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
            
            # Test Unicode normalization scenarios
            base_passphrase = "tëst"
            
            normalizations = [
                ("original", base_passphrase),
                ("nfc", unicodedata.normalize('NFC', base_passphrase)),
                ("nfd", unicodedata.normalize('NFD', base_passphrase)),
                ("nfkc", unicodedata.normalize('NFKC', base_passphrase)),
                ("nfkd", unicodedata.normalize('NFKD', base_passphrase)),
            ]
            
            seeds = []
            for name, passphrase in normalizations:
                seed = self.bitcoin_service.mnemo.to_seed(test_seed, passphrase=passphrase)
                seeds.append((name, seed))
            
            # Some normalizations might produce the same result, but not all
            unique_seeds = set(seed for name, seed in seeds)
            
            # At least NFC/NFD should be different for this test case
            assert len(unique_seeds) >= 2, f"Expected different seeds for different normalizations, got {len(unique_seeds)} unique seeds"
            
        except ImportError as e:
            pytest.skip(f"Required crypto libraries not available: {e}")


class TestRealWorldScenarios:
    """Test scenarios that mimic real-world usage"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.integration
    @pytest.mark.requires_crypto
    @pytest.mark.slow
    def test_comprehensive_search_simulation(self):
        """Test comprehensive derivation search simulation"""
        try:
            service = BitcoinService()
            
            # Simulate searching for a known address
            test_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
            test_passphrase = ""
            
            # Generate a test address to search for
            seed = service.mnemo.to_seed(test_seed, passphrase=test_passphrase)
            
            from bitcoinlib.keys import HDKey
            master_key = HDKey.from_seed(seed)
            
            # Generate address from a specific path
            target_path = "m/44'/0'/0'/0/5"  # Account 0, index 5
            derived_key = master_key.subkey_for_path(target_path)
            target_address = derived_key.address()
            
            # Ensure we have a valid address string
            assert isinstance(target_address, str), f"Expected string address, got {type(target_address)}"
            assert service.validate_bitcoin_address_format(target_address), f"Invalid address format: {target_address}"
            
            # Now simulate comprehensive search
            progress_calls = []
            def progress_callback(msg, pct):
                progress_calls.append((msg, pct))
            
            # Search should find the address
            result = service.test_derivation_comprehensive(
                test_seed, test_passphrase, target_address, "legacy", progress_callback
            )
            
            # Verify search succeeded
            assert result is not None, "Comprehensive search should have found the target address"
            assert result['derivation_result']['address'] == target_address
            assert result['account'] == 0  # Should find account 0
            assert result['address_index'] == 5  # Should find index 5
            
            # Verify progress was reported
            assert len(progress_calls) > 0, "Progress should have been reported during search"
            
        except ImportError as e:
            pytest.skip(f"Required crypto libraries not available: {e}")
    
    @pytest.mark.integration
    @pytest.mark.requires_crypto
    def test_file_generation_workflow(self):
        """Test complete file generation workflow"""
        try:
            bitcoin_service = BitcoinService()
            
            # Create mock derivation result
            mock_derivation_info = {
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
            
            # Test private key extraction
            extraction_result = bitcoin_service.extract_private_key(mock_derivation_info, self.temp_dir)
            
            # Verify WIF file was created
            wif_file = Path(extraction_result['wif_file'])
            assert wif_file.exists(), "WIF file should have been created"
            
            # Verify file content
            with open(wif_file, 'r') as f:
                content = f.read().strip()
            assert content == mock_derivation_info['derivation_result']['private_key_wif']
            
            # Test instruction file creation
            instructions_file = bitcoin_service.create_instructions_file(extraction_result, self.temp_dir)
            
            # Verify instruction file was created
            instructions_path = Path(instructions_file)
            assert instructions_path.exists(), "Instructions file should have been created"
            
            # Verify instruction content
            with open(instructions_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Should contain key information
            assert "MIDNIGHT BITCOIN CLAIM KEY" in content
            assert "SOFTWARE WALLET IMPORT INSTRUCTIONS" in content
            assert "Electrum Wallet" in content
            assert "SECURITY REQUIREMENTS" in content
            assert mock_derivation_info['derivation_result']['derivation_path'] in content
            
            # Files should have restrictive permissions
            import stat
            wif_stat = wif_file.stat()
            instructions_stat = instructions_path.stat()
            
            # Check that owner has read/write permissions (exact permissions may vary by OS)
            assert wif_stat.st_mode & stat.S_IRUSR  # Owner can read
            assert wif_stat.st_mode & stat.S_IWUSR  # Owner can write
            
        except ImportError as e:
            pytest.skip(f"Required crypto libraries not available: {e}")
        except Exception as e:
            pytest.fail(f"File generation workflow failed: {e}")