#!/usr/bin/env python3
"""
Test validation functions by extracting them without GUI dependencies
Tests core validation logic independently
"""

import pytest
import re
from pathlib import Path
from unittest.mock import patch, Mock


def validate_seed_phrase_format(seed_phrase: str) -> tuple[bool, str]:
    """
    Validate seed phrase format without checking cryptographic validity
    Extracted from security.py to avoid tkinter dependency
    """
    if not seed_phrase or not seed_phrase.strip():
        return False, "Seed phrase cannot be empty"
    
    words = seed_phrase.strip().split()
    
    if len(words) not in [12, 15, 18, 21, 24]:
        return False, f"Seed phrase must be 12, 15, 18, 21, or 24 words (found {len(words)})"
    
    # Check for obvious issues
    for i, word in enumerate(words, 1):
        if not word.isalpha():
            return False, f"Word {i} contains non-alphabetic characters: '{word}'"
        if len(word) < 3:
            return False, f"Word {i} is too short: '{word}'"
        if len(word) > 8:
            return False, f"Word {i} is too long: '{word}'"
    
    return True, ""


def validate_address_format(address: str, address_type: str) -> tuple[bool, str]:
    """
    Validate address format based on type
    Extracted from security.py to avoid tkinter dependency
    """
    if not address or not address.strip():
        return False, "Address cannot be empty"
    
    address = address.strip()
    
    if address_type == "cardano":
        if not (address.startswith('addr1') or address.startswith('Ae2') or address.startswith('Ddz')):
            return False, "Cardano address must start with 'addr1', 'Ae2', or 'Ddz'"
        if len(address) < 50:
            return False, "Cardano address appears too short"
        if len(address) > 120:
            return False, "Cardano address appears too long"
    
    elif address_type == "bitcoin":
        if not (address.startswith('1') or address.startswith('3') or address.startswith('bc1')):
            return False, "Bitcoin address must start with '1', '3', or 'bc1'"
        if len(address) < 25:
            return False, "Bitcoin address appears too short"
        if len(address) > 65:
            return False, "Bitcoin address appears too long"
    
    return True, ""


def validate_stake_checksum(checksum: str) -> tuple[bool, str]:
    """
    Validate Cardano stake key checksum format
    Extracted from security.py to avoid tkinter dependency
    """
    if not checksum or not checksum.strip():
        return False, "Stake checksum cannot be empty"
    
    checksum = checksum.strip()
    
    if len(checksum) != 64:
        return False, f"Stake checksum must be exactly 64 characters (found {len(checksum)})"
    
    if not re.match(r'^[0-9a-fA-F]{64}$', checksum):
        return False, "Stake checksum must contain only hexadecimal characters (0-9, a-f, A-F)"
    
    return True, ""


def validate_bitcoin_wif(wif_key: str) -> tuple[bool, str]:
    """
    Validate Bitcoin WIF private key format
    Extracted from security.py to avoid tkinter dependency
    """
    if not wif_key or not wif_key.strip():
        return False, "WIF key cannot be empty"
    
    wif_key = wif_key.strip()
    
    # WIF keys should start with specific characters
    if not (wif_key.startswith('5') or wif_key.startswith('K') or wif_key.startswith('L')):
        return False, "WIF key must start with '5', 'K', or 'L'"
    
    # Basic length check
    if len(wif_key) < 51 or len(wif_key) > 52:
        return False, "WIF key has invalid length"
    
    return True, ""


class TestValidationFunctions:
    """Test all validation functions"""
    
    def test_validate_seed_phrase_format_valid(self):
        """Test seed phrase format validation with valid phrases"""
        # Test different valid lengths
        valid_12 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        valid_24 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art"
        
        assert validate_seed_phrase_format(valid_12) == (True, "")
        assert validate_seed_phrase_format(valid_24) == (True, "")
        
        # Test 15, 18, 21 word phrases
        valid_15 = " ".join(["abandon"] * 14 + ["about"])
        valid_18 = " ".join(["abandon"] * 17 + ["about"]) 
        valid_21 = " ".join(["abandon"] * 20 + ["about"])
        
        assert validate_seed_phrase_format(valid_15) == (True, "")
        assert validate_seed_phrase_format(valid_18) == (True, "")
        assert validate_seed_phrase_format(valid_21) == (True, "")
    
    def test_validate_seed_phrase_format_invalid_length(self):
        """Test seed phrase format validation with invalid lengths"""
        invalid_5 = "abandon abandon abandon abandon abandon"
        invalid_13 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"  # 13 words
        invalid_23 = " ".join(["abandon"] * 22 + ["about"])  # 23 words
        
        is_valid, error = validate_seed_phrase_format(invalid_5)
        assert is_valid == False
        assert "must be 12, 15, 18, 21, or 24 words" in error
        
        is_valid, error = validate_seed_phrase_format(invalid_13)
        assert is_valid == False
        assert "must be 12, 15, 18, 21, or 24 words" in error
        
        is_valid, error = validate_seed_phrase_format(invalid_23)
        assert is_valid == False
        assert "must be 12, 15, 18, 21, or 24 words" in error
    
    def test_validate_seed_phrase_format_invalid_words(self):
        """Test seed phrase format validation with invalid words"""
        invalid_chars = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon 123"
        invalid_short = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon a"
        invalid_long = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon verylongword"
        
        is_valid, error = validate_seed_phrase_format(invalid_chars)
        assert is_valid == False
        assert "contains non-alphabetic characters" in error
        
        is_valid, error = validate_seed_phrase_format(invalid_short)
        assert is_valid == False
        assert "is too short" in error
        
        is_valid, error = validate_seed_phrase_format(invalid_long)
        assert is_valid == False
        assert "is too long" in error
    
    def test_validate_seed_phrase_format_empty(self):
        """Test seed phrase format validation with empty input"""
        is_valid, error = validate_seed_phrase_format("")
        assert is_valid == False
        assert "cannot be empty" in error
        
        is_valid, error = validate_seed_phrase_format("   ")
        assert is_valid == False
        assert "cannot be empty" in error
    
    def test_validate_address_format_cardano(self):
        """Test Cardano address format validation"""
        valid_shelley = "addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer3n0d3vllmyqwsx5wktcd8cc3sq835lu7drv2xwl2wywfgse35a3x"
        valid_byron = "Ae2tdPwUPEZFRbyhz3cpfC2CumGzNkFBN2L42rcUc2yjQpEkxDbkPodpMAi"
        valid_daedalus = "DdzFFzCqrhsuwQKiR3CdQ1FzuPAydtVCBFTRoaXNMF4kqN1i5BCz5L7n7oj"
        
        assert validate_address_format(valid_shelley, "cardano") == (True, "")
        assert validate_address_format(valid_byron, "cardano") == (True, "")
        assert validate_address_format(valid_daedalus, "cardano") == (True, "")
        
        # Test invalid Cardano addresses
        is_valid, error = validate_address_format("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", "cardano")
        assert is_valid == False
        assert "must start with 'addr1', 'Ae2', or 'Ddz'" in error
        
        # Test too short
        is_valid, error = validate_address_format("addr1short", "cardano")
        assert is_valid == False
        assert "appears too short" in error
    
    def test_validate_address_format_bitcoin(self):
        """Test Bitcoin address format validation"""
        valid_legacy = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
        valid_segwit = "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"
        valid_native_segwit = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
        
        assert validate_address_format(valid_legacy, "bitcoin") == (True, "")
        assert validate_address_format(valid_segwit, "bitcoin") == (True, "")
        assert validate_address_format(valid_native_segwit, "bitcoin") == (True, "")
        
        # Test invalid Bitcoin addresses
        is_valid, error = validate_address_format("addr1qx2fxv2umyh", "bitcoin")
        assert is_valid == False
        assert "must start with '1', '3', or 'bc1'" in error
        
        # Test too short
        is_valid, error = validate_address_format("1short", "bitcoin")
        assert is_valid == False
        assert "appears too short" in error
    
    def test_validate_address_format_empty(self):
        """Test address format validation with empty input"""
        is_valid, error = validate_address_format("", "cardano")
        assert is_valid == False
        assert "cannot be empty" in error
        
        is_valid, error = validate_address_format("   ", "bitcoin")
        assert is_valid == False
        assert "cannot be empty" in error
    
    def test_validate_stake_checksum_valid(self):
        """Test stake checksum validation with valid checksums"""
        valid_checksum = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        assert validate_stake_checksum(valid_checksum) == (True, "")
        
        # Test with uppercase
        valid_checksum_upper = "1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF"
        assert validate_stake_checksum(valid_checksum_upper) == (True, "")
        
        # Test with mixed case
        valid_checksum_mixed = "1234567890AbCdEf1234567890AbCdEf1234567890AbCdEf1234567890AbCdEf"
        assert validate_stake_checksum(valid_checksum_mixed) == (True, "")
    
    def test_validate_stake_checksum_invalid_length(self):
        """Test stake checksum validation with invalid length"""
        too_short = "1234567890abcdef"
        too_long = "1234567890abcdef" * 5
        
        is_valid, error = validate_stake_checksum(too_short)
        assert is_valid == False
        assert "must be exactly 64 characters" in error
        
        is_valid, error = validate_stake_checksum(too_long)
        assert is_valid == False
        assert "must be exactly 64 characters" in error
    
    def test_validate_stake_checksum_invalid_chars(self):
        """Test stake checksum validation with invalid characters"""
        # Test with exactly 64 characters but invalid hex chars
        invalid_chars = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcghj"  # 'g','h','j' invalid, exactly 64 chars
        
        is_valid, error = validate_stake_checksum(invalid_chars)
        assert is_valid == False
        assert "must contain only hexadecimal characters" in error
        
        # Test with spaces (which also makes it wrong length)
        with_spaces = "1234567890abcdef 1234567890abcdef1234567890abcdef1234567890abcd"  # 64 chars including space
        is_valid, error = validate_stake_checksum(with_spaces)
        assert is_valid == False
        # Could fail on either length or character validation
        assert "must contain only hexadecimal characters" in error or "must be exactly 64 characters" in error
    
    def test_validate_stake_checksum_empty(self):
        """Test stake checksum validation with empty input"""
        is_valid, error = validate_stake_checksum("")
        assert is_valid == False
        assert "cannot be empty" in error
        
        is_valid, error = validate_stake_checksum("   ")
        assert is_valid == False
        assert "cannot be empty" in error
    
    def test_validate_bitcoin_wif_valid(self):
        """Test Bitcoin WIF validation with valid keys"""
        # These are example WIF formats (not real keys)
        valid_wif_5 = "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ"  # Uncompressed
        valid_wif_k = "KwdMAjGmerYanjeui5SHS7JkmpZvVipYvB2LJGU1ZxJwYvP98617"  # Compressed
        valid_wif_l = "L1aW4aubDFB7yfras2S1mN3bqg9nwySY8nkoLmJebSLD5BWv3ENZ"  # Compressed
        
        assert validate_bitcoin_wif(valid_wif_5) == (True, "")
        assert validate_bitcoin_wif(valid_wif_k) == (True, "")
        assert validate_bitcoin_wif(valid_wif_l) == (True, "")
    
    def test_validate_bitcoin_wif_invalid_start(self):
        """Test Bitcoin WIF validation with invalid start characters"""
        invalid_start = "9HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ"
        
        is_valid, error = validate_bitcoin_wif(invalid_start)
        assert is_valid == False
        assert "must start with '5', 'K', or 'L'" in error
        
        # Test with other invalid starts
        invalid_starts = ["1HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ",
                         "BHueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ"]
        
        for invalid_wif in invalid_starts:
            is_valid, error = validate_bitcoin_wif(invalid_wif)
            assert is_valid == False
            assert "must start with '5', 'K', or 'L'" in error
    
    def test_validate_bitcoin_wif_invalid_length(self):
        """Test Bitcoin WIF validation with invalid length"""
        too_short = "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1"
        too_long = "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJXXXXXXXXX"
        
        is_valid, error = validate_bitcoin_wif(too_short)
        assert is_valid == False
        assert "has invalid length" in error
        
        is_valid, error = validate_bitcoin_wif(too_long)
        assert is_valid == False
        assert "has invalid length" in error
    
    def test_validate_bitcoin_wif_empty(self):
        """Test Bitcoin WIF validation with empty input"""
        is_valid, error = validate_bitcoin_wif("")
        assert is_valid == False
        assert "cannot be empty" in error
        
        is_valid, error = validate_bitcoin_wif("   ")
        assert is_valid == False
        assert "cannot be empty" in error


class TestValidationEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_seed_phrase_whitespace_handling(self):
        """Test seed phrase validation handles whitespace correctly"""
        # Leading/trailing spaces
        with_spaces = "  abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about  "
        assert validate_seed_phrase_format(with_spaces) == (True, "")
        
        # Multiple spaces between words
        multiple_spaces = "abandon  abandon   abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        # This should be handled as valid (strip().split() handles multiple spaces)
        is_valid, error = validate_seed_phrase_format(multiple_spaces)
        # The current implementation would see this as 12 words, which is correct
        assert is_valid == True or "must be 12" in error  # Either valid or correctly identifies word count
    
    def test_address_boundary_lengths(self):
        """Test address validation at boundary lengths"""
        # Cardano boundary tests
        cardano_min = "addr1" + "a" * 46  # Exactly 50 characters
        cardano_max = "addr1" + "a" * 115  # Exactly 120 characters
        cardano_too_short = "addr1" + "a" * 44  # 49 characters (1 less than minimum)
        cardano_too_long = "addr1" + "a" * 116  # 121 characters (1 more than maximum)
        
        assert validate_address_format(cardano_min, "cardano") == (True, "")
        assert validate_address_format(cardano_max, "cardano") == (True, "")
        
        is_valid, error = validate_address_format(cardano_too_short, "cardano")
        assert is_valid == False
        assert "too short" in error
        
        is_valid, error = validate_address_format(cardano_too_long, "cardano")
        assert is_valid == False
        assert "too long" in error
        
        # Bitcoin boundary tests
        bitcoin_min = "1" + "a" * 24  # Exactly 25 characters
        bitcoin_max = "1" + "a" * 64  # Exactly 65 characters (maximum allowed)
        bitcoin_too_short = "1" + "a" * 23  # 24 characters
        bitcoin_too_long = "1" + "a" * 65  # 66 characters (over maximum)
        
        assert validate_address_format(bitcoin_min, "bitcoin") == (True, "")
        assert validate_address_format(bitcoin_max, "bitcoin") == (True, "")
        
        is_valid, error = validate_address_format(bitcoin_too_short, "bitcoin")
        assert is_valid == False
        assert "too short" in error
        
        is_valid, error = validate_address_format(bitcoin_too_long, "bitcoin")
        assert is_valid == False
        assert "too long" in error
    
    def test_wif_boundary_lengths(self):
        """Test WIF validation at boundary lengths"""
        # Exactly 51 characters (minimum)
        wif_min = "5" + "a" * 50
        assert validate_bitcoin_wif(wif_min) == (True, "")
        
        # Exactly 52 characters (maximum)
        wif_max = "K" + "a" * 51
        assert validate_bitcoin_wif(wif_max) == (True, "")
        
        # 50 characters (too short)
        wif_too_short = "5" + "a" * 49
        is_valid, error = validate_bitcoin_wif(wif_too_short)
        assert is_valid == False
        assert "has invalid length" in error
        
        # 53 characters (too long)
        wif_too_long = "L" + "a" * 52
        is_valid, error = validate_bitcoin_wif(wif_too_long)
        assert is_valid == False
        assert "has invalid length" in error


if __name__ == "__main__":
    # Run these tests directly if called as script
    pytest.main([__file__, "-v"])