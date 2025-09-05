#!/usr/bin/env python3
"""
Bitcoin Service Layer for MidnightClaimer GUI
Extracted and enhanced from midnight_claim_bitcoin.py for use in GUI application
"""

import os
import unicodedata
import logging
from pathlib import Path
from typing import Optional, Dict, Callable
from mnemonic import Mnemonic
from bitcoinlib.keys import HDKey
import hashlib
import base58
import re

logger = logging.getLogger(__name__)

class BitcoinService:
    """Service class for Bitcoin key derivation and validation"""
    
    def __init__(self):
        self.mnemo = Mnemonic("english")
        # Use consistent workspace path matching working script
        self.workspace_base = Path(r"D:\workspace\VisualStudio\Midnight Claim")
    
    def validate_seed_phrase(self, seed_phrase: str) -> bool:
        """Validate mnemonic seed phrase"""
        try:
            if not seed_phrase or not seed_phrase.strip():
                return False
            
            # Check word count first
            words = seed_phrase.strip().split()
            if len(words) not in [12, 15, 18, 21, 24]:
                return False
            
            return self.mnemo.check(seed_phrase.strip())
        except Exception as e:
            logger.debug(f"Seed phrase validation failed: {e}")
            return False
    
    def validate_bitcoin_address_format(self, address: str) -> bool:
        """Validate Bitcoin address format with proper validation"""
        try:
            if not address or not address.strip():
                return False
            
            address = address.strip()
            
            # Legacy addresses (P2PKH) - start with '1'
            if address.startswith('1'):
                if len(address) < 25 or len(address) > 34:
                    return False
                try:
                    # Validate base58 encoding and checksum
                    decoded = base58.b58decode_check(address)
                    # P2PKH should have 21 bytes (1 byte version + 20 bytes hash)
                    if len(decoded) != 21:
                        return False
                    # Version byte should be 0x00 for mainnet P2PKH
                    if decoded[0] != 0x00:
                        return False
                    return True
                except Exception:
                    return False
            
            # P2SH addresses - start with '3'
            elif address.startswith('3'):
                if len(address) < 25 or len(address) > 34:
                    return False
                try:
                    # Validate base58 encoding and checksum
                    decoded = base58.b58decode_check(address)
                    # P2SH should have 21 bytes (1 byte version + 20 bytes hash)
                    if len(decoded) != 21:
                        return False
                    # Version byte should be 0x05 for mainnet P2SH
                    if decoded[0] != 0x05:
                        return False
                    return True
                except Exception:
                    return False
            
            # Bech32 addresses (Native SegWit) - start with 'bc1'
            elif address.startswith('bc1'):
                if len(address) < 39 or len(address) > 59:
                    return False
                try:
                    # Basic bech32 format validation
                    # Should only contain valid bech32 characters
                    bech32_chars = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
                    
                    # Check if all characters after 'bc1' are valid bech32
                    data_part = address[3:]  # Remove 'bc1' prefix
                    if not all(c in bech32_chars for c in data_part):
                        return False
                    
                    # Additional validation could be added here for full bech32 decode
                    # For now, this basic check should suffice for format validation
                    return True
                except Exception:
                    return False
            else:
                return False
                
        except Exception as e:
            logger.debug(f"Address format validation failed: {e}")
            return False
    
    def detect_address_type(self, address: str) -> str:
        """Auto-detect Bitcoin address type from format"""
        if not self.validate_bitcoin_address_format(address):
            raise ValueError(f"Invalid Bitcoin address format: {address}")
            
        if address.startswith('1'):
            return 'legacy'
        elif address.startswith('3'):
            return 'segwit'
        elif address.startswith('bc1'):
            return 'native_segwit'
        else:
            raise ValueError(f"Unknown Bitcoin address format: {address}")
    
    def get_derivation_path(self, address_type: str, account: int, change: int, index: int) -> str:
        """Get BIP derivation path for different address types"""
        if address_type == 'legacy':
            # BIP44: m/44'/0'/account'/change/index
            return f"m/44'/0'/{account}'/{change}/{index}"
        elif address_type == 'segwit':
            # BIP49: m/49'/0'/account'/change/index
            return f"m/49'/0'/{account}'/{change}/{index}"
        elif address_type == 'native_segwit':
            # BIP84: m/84'/0'/account'/change/index
            return f"m/84'/0'/{account}'/{change}/{index}"
        else:
            raise ValueError(f"Unsupported address type: {address_type}")
    
    def _validate_derivation_path(self, path: str) -> bool:
        """Validate Bitcoin derivation path format"""
        try:
            # Should match pattern: m/purpose'/coin'/account'/change/index
            # Where purpose is 44, 49, or 84 for Bitcoin
            pattern = r"^m/(44|49|84)'/0'/\d+'/[0-1]/\d+$"
            return bool(re.match(pattern, path))
        except:
            return False
    
    def _validate_derived_key(self, derived_key) -> bool:
        """Validate that a derived key is properly formed"""
        try:
            # Check if private key exists and is valid length
            if not hasattr(derived_key, 'private_hex') or not derived_key.private_hex:
                return False
            
            # Private key should be 64 hex characters (32 bytes)
            if len(derived_key.private_hex) != 64:
                return False
            
            # Check if it's valid hex
            try:
                int(derived_key.private_hex, 16)
            except ValueError:
                return False
            
            # Check if WIF can be generated
            if not hasattr(derived_key, 'wif') or not derived_key.wif():
                return False
            
            # Validate WIF format
            wif = derived_key.wif()
            if not self._validate_wif_format(wif):
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Key validation failed: {e}")
            return False
    
    def _validate_wif_format(self, wif_key: str) -> bool:
        """Validate WIF private key format"""
        try:
            if not wif_key or not wif_key.strip():
                return False
            
            wif_key = wif_key.strip()
            
            # WIF keys should start with specific characters
            if not (wif_key.startswith('5') or wif_key.startswith('K') or wif_key.startswith('L')):
                return False
            
            # Basic length check
            if len(wif_key) < 51 or len(wif_key) > 52:
                return False
            
            # Validate base58 encoding
            try:
                base58.b58decode_check(wif_key)
                return True
            except Exception:
                return False
                
        except Exception as e:
            logger.debug(f"WIF validation failed: {e}")
            return False
    
    def derive_bitcoin_key(self, seed_phrase: str, passphrase: str, account: int, 
                          address_index: int, address_type: str) -> Optional[Dict]:
        """Derive Bitcoin private key for given parameters with comprehensive validation"""
        try:
            # Validate inputs first
            if not self.validate_seed_phrase(seed_phrase):
                logger.debug("Invalid seed phrase provided")
                return None
            
            if account < 0 or account > 100:  # Reasonable limits
                logger.debug(f"Account number out of range: {account}")
                return None
                
            if address_index < 0 or address_index > 1000:  # Reasonable limits
                logger.debug(f"Address index out of range: {address_index}")
                return None
            
            if address_type not in ['legacy', 'segwit', 'native_segwit']:
                logger.debug(f"Invalid address type: {address_type}")
                return None
            
            # Create seed from mnemonic
            seed = self.mnemo.to_seed(seed_phrase, passphrase=passphrase)
            
            # Validate seed length
            if len(seed) != 64:  # Should be 512 bits (64 bytes)
                logger.debug(f"Invalid seed length: {len(seed)}")
                return None
            
            # Create master key
            master_key = HDKey.from_seed(seed)
            
            # Validate master key
            if not master_key or not hasattr(master_key, 'subkey_for_path'):
                logger.debug("Failed to create valid master key")
                return None
            
            # Get and validate derivation path
            derivation_path = self.get_derivation_path(address_type, account, 0, address_index)
            if not self._validate_derivation_path(derivation_path):
                logger.debug(f"Invalid derivation path: {derivation_path}")
                return None
            
            # Derive key
            derived_key = master_key.subkey_for_path(derivation_path)
            
            # Validate derived key
            if not self._validate_derived_key(derived_key):
                logger.debug(f"Invalid derived key for path: {derivation_path}")
                return None
            
            # Generate address based on type
            try:
                if address_type == 'legacy':
                    address = derived_key.address()
                elif address_type == 'segwit':
                    address = derived_key.address(script_type='p2sh_p2wpkh')
                elif address_type == 'native_segwit':
                    address = derived_key.address(script_type='p2wpkh')
                else:
                    logger.debug(f"Unsupported address type: {address_type}")
                    return None
            except Exception as e:
                logger.debug(f"Address generation failed: {e}")
                return None
            
            # Validate generated address
            if not self.validate_bitcoin_address_format(address):
                logger.debug(f"Generated invalid address: {address}")
                return None
            
            # Double-check address type matches expected
            try:
                detected_type = self.detect_address_type(address)
                if detected_type != address_type:
                    logger.debug(f"Address type mismatch: expected {address_type}, got {detected_type}")
                    return None
            except Exception as e:
                logger.debug(f"Address type verification failed: {e}")
                return None
            
            return {
                'address': address,
                'private_key_wif': derived_key.wif(),
                'private_key_hex': derived_key.private_hex,
                'derivation_path': derivation_path,
                'derived_key': derived_key
            }
            
        except Exception as e:
            logger.debug(f"Key derivation failed: {e}")
            return None
    
    def test_derivation_comprehensive(
        self,
        seed_phrase: str,
        passphrase: str,
        eligible_address: str,
        address_type: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Optional[Dict]:
        """
        Comprehensive derivation test with progress updates
        Based on the working midnight_claim_bitcoin.py logic
        """
        if progress_callback:
            progress_callback("Starting comprehensive Bitcoin derivation test...", 0)
        
        # Validate inputs first
        if not self.validate_seed_phrase(seed_phrase):
            if progress_callback:
                progress_callback("Invalid seed phrase format", 100)
            logger.error("Invalid seed phrase provided")
            return None
        
        if not self.validate_bitcoin_address_format(eligible_address):
            if progress_callback:
                progress_callback("Invalid target address format", 100)
            logger.error(f"Invalid target address format: {eligible_address}")
            return None
        
        # Verify address type matches target address
        try:
            detected_type = self.detect_address_type(eligible_address)
            if detected_type != address_type:
                logger.warning(f"Address type mismatch: detected {detected_type}, expected {address_type}")
                address_type = detected_type  # Use detected type
                if progress_callback:
                    progress_callback(f"Auto-corrected address type to: {address_type}", 10)
        except Exception as e:
            if progress_callback:
                progress_callback(f"Address type detection failed: {e}", 100)
            return None
        
        logger.info(f"Target Bitcoin address: {eligible_address}")
        logger.info(f"Address type: {address_type}")
        
        # Passphrase scenarios to test (matching working script)
        passphrase_scenarios = [
            ("current_passphrase", passphrase),
            ("empty_passphrase", ""),
            ("trimmed_passphrase", passphrase.strip()),
            ("lowercase_passphrase", passphrase.lower()),
            ("nfc_normalized", unicodedata.normalize('NFC', passphrase)),
            ("nfkd_normalized", unicodedata.normalize('NFKD', passphrase)),
        ]
        
        total_combinations = len(passphrase_scenarios) * 5 * 20  # scenarios * accounts * indices
        current_combination = 0
        
        for scenario_name, test_passphrase in passphrase_scenarios:
            if progress_callback:
                progress_callback(f"Testing {scenario_name}...", int(current_combination / total_combinations * 100))
            
            logger.info(f"--- Testing {scenario_name} ---")
            
            # Test different accounts (0-4)
            for account in range(5):
                # Test different address indices (0-19)
                for address_index in range(20):
                    current_combination += 1
                    
                    if current_combination % 25 == 0 and progress_callback:
                        progress_callback(
                            f"Testing account {account}, index {address_index}...",
                            int(current_combination / total_combinations * 100)
                        )
                    
                    try:
                        result = self.derive_bitcoin_key(
                            seed_phrase, test_passphrase, account, address_index, address_type
                        )
                        
                        if result and result['address'] == eligible_address:
                            if progress_callback:
                                progress_callback("Perfect match found!", 100)
                            
                            logger.info(f"PERFECT MATCH! Derivation found!")
                            logger.info(f"  Scenario: {scenario_name}")
                            logger.info(f"  Account: {account}, Index: {address_index}")
                            logger.info(f"  Derivation Path: {result['derivation_path']}")
                            logger.info(f"  Address: {result['address']}")
                            
                            return self._create_result(
                                account, address_index, result, scenario_name, test_passphrase, address_type
                            )
                        
                        # Log first few attempts for debugging
                        if account == 0 and address_index < 3 and scenario_name == "current_passphrase":
                            logger.info(f"Account {account}, Index {address_index}: {result['address'][:20] if result else 'Failed'}...")
                            
                    except Exception as e:
                        logger.debug(f"Derivation failed for account {account}, index {address_index}: {e}")
                        continue
        
        if progress_callback:
            progress_callback("No matching derivation found", 100)
        logger.error("No matching derivation found across all scenarios")
        return None
    
    def _create_result(self, account: int, address_index: int, derivation_result: Dict, 
                      scenario_name: str, passphrase_used: str, address_type: str) -> Dict:
        """Create successful result object with validation"""
        
        # Validate inputs
        if account < 0 or address_index < 0:
            raise ValueError("Account and address index must be non-negative")
        
        if not derivation_result or 'address' not in derivation_result:
            raise ValueError("Invalid derivation result")
        
        if not self.validate_bitcoin_address_format(derivation_result['address']):
            raise ValueError(f"Invalid address in result: {derivation_result['address']}")
        
        if not self._validate_wif_format(derivation_result['private_key_wif']):
            raise ValueError(f"Invalid WIF key in result: {derivation_result['private_key_wif']}")
        
        logger.info("MATCH FOUND!")
        logger.info(f"  Derivation Path: {derivation_result['derivation_path']}")
        logger.info(f"  Address Type: {address_type}")
        logger.info(f"  Account: {account}, Index: {address_index}")
        logger.info(f"  Scenario: {scenario_name}")
        
        return {
            'account': account,
            'address_index': address_index,
            'derivation_result': derivation_result,
            'scenario_name': scenario_name,
            'passphrase_used': passphrase_used,
            'address_type': address_type
        }
    
    def extract_private_key(self, derivation_info: Dict, output_dir: Path) -> Dict[str, str]:
        """
        Extract and save the Bitcoin private key in WIF format with comprehensive validation
        """
        try:
            # Ensure output directory exists with proper permissions
            output_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(output_dir, 0o700)
            
            derivation_result = derivation_info['derivation_result']
            address = derivation_result['address']
            private_key_wif = derivation_result['private_key_wif']
            
            # Validate inputs
            if not self.validate_bitcoin_address_format(address):
                raise ValueError(f"Invalid address for key extraction: {address}")
            
            if not self._validate_wif_format(private_key_wif):
                raise ValueError(f"Invalid WIF key for extraction: {private_key_wif}")
            
            logger.info("Extracting Bitcoin private key...")
            
            # Create safe filename from address
            safe_addr = address[:12].replace('1', '').replace('3', '').replace('bc1q', 'bc1q')
            process_id = os.getpid()
            
            # Save WIF private key
            wif_file = output_dir / f"midnight_bitcoin_private_{safe_addr}_{process_id}.wif"
            
            try:
                with open(wif_file, 'w') as f:
                    f.write(private_key_wif)
                
                # Set restrictive permissions on the file
                os.chmod(wif_file, 0o600)
                logger.info(f"WIF key saved: {wif_file.name}")
                
            except Exception as e:
                logger.error(f"Failed to save WIF file: {e}")
                raise ValueError(f"Failed to save WIF file: {e}")
            
            # Verify file was written correctly
            try:
                with open(wif_file, 'r') as f:
                    saved_wif = f.read().strip()
                if saved_wif != private_key_wif:
                    raise ValueError("WIF file verification failed - content mismatch")
            except Exception as e:
                logger.error(f"WIF file verification failed: {e}")
                raise ValueError(f"WIF file verification failed: {e}")
            
            result = {
                'wif_file': str(wif_file),
                'address': address,
                'private_key_wif': private_key_wif,
                'derivation_info': derivation_info
            }
            
            logger.info("Bitcoin private key extraction completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Private key extraction error: {e}")
            raise
    
    def create_instructions_file(self, key_info: Dict, output_dir: Path) -> str:
        """Create comprehensive instruction file for user"""
        address = key_info['address']
        safe_addr = address[:12].replace('1', '').replace('3', '').replace('bc1q', 'bc1q')
        process_id = os.getpid()
        
        instructions_file = output_dir / f"BITCOIN_INSTRUCTIONS_{safe_addr}_{process_id}.txt"
        
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write("MIDNIGHT BITCOIN CLAIM KEY SUCCESSFULLY GENERATED!\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("DERIVATION DETAILS:\n")
            f.write(f"Bitcoin Address: {address}\n")
            f.write(f"Derivation Path: {key_info['derivation_info']['derivation_result']['derivation_path']}\n")
            f.write(f"Address Type: {key_info['derivation_info']['address_type']}\n")
            f.write(f"Account: {key_info['derivation_info']['account']}\n")
            f.write(f"Address Index: {key_info['derivation_info']['address_index']}\n")
            f.write(f"Scenario Used: {key_info['derivation_info']['scenario_name']}\n\n")
            
            f.write("GENERATED FILES:\n")
            f.write("=" * 30 + "\n")
            f.write(f"WIF Private Key: {Path(key_info['wif_file']).name}\n\n")
            
            f.write("SOFTWARE WALLET IMPORT INSTRUCTIONS:\n")
            f.write("=" * 50 + "\n")
            f.write("OPTION 1: Electrum Wallet (Recommended)\n")
            f.write("1. Download Electrum from electrum.org\n")
            f.write("2. File -> New/Restore\n")
            f.write("3. Choose 'Import Bitcoin addresses or private keys'\n")
            f.write(f"4. Paste WIF key from: {Path(key_info['wif_file']).name}\n")
            f.write("5. Next -> Create\n")
            f.write("6. Connect to Midnight Portal\n")
            f.write("7. Execute claim\n\n")
            
            f.write("OPTION 2: Sparrow Wallet\n")
            f.write("1. Download Sparrow from sparrowwallet.com\n")
            f.write("2. File -> New Wallet\n")
            f.write("3. Choose 'Imported'\n")
            
            address_type = key_info['derivation_info']['address_type']
            if address_type == 'legacy':
                f.write("4. Script Type: P2PKH\n")
            elif address_type == 'segwit':
                f.write("4. Script Type: P2SH-P2WPKH\n")
            elif address_type == 'native_segwit':
                f.write("4. Script Type: P2WPKH\n")
            
            f.write(f"5. Paste WIF key from: {Path(key_info['wif_file']).name}\n")
            f.write("6. Create Wallet\n\n")
            
            f.write("OPTION 3: Bitcoin Core (Advanced)\n")
            f.write("1. Ensure Bitcoin Core is synced\n")
            f.write("2. Open Bitcoin Core console (Help -> Debug Window -> Console)\n")
            f.write("3. Run: importprivkey \"YOUR_WIF_KEY\" \"midnight_claim\"\n")
            f.write("4. Wait for rescan to complete\n\n")
            
            f.write("TROUBLESHOOTING:\n")
            f.write("=" * 30 + "\n")
            f.write("If wallet won't import WIF key:\n")
            f.write("- Verify the WIF format is correct (should start with 5, K, or L)\n")
            f.write("- Try a different software wallet\n")
            f.write("- Check that the wallet supports your address type\n")
            f.write("- Ensure you're using mainnet (not testnet) wallet\n\n")
            
            f.write("If Midnight Portal doesn't recognize address:\n")
            f.write("- Verify your derived address matches the eligible one exactly\n")
            f.write("- Contact Midnight support if address eligibility is unclear\n\n")
            
            f.write("SECURITY REQUIREMENTS - IMMEDIATELY AFTER CLAIMING:\n")
            f.write("=" * 50 + "\n")
            f.write(f"1. DELETE: {Path(key_info['wif_file']).name}\n")
            f.write("2. DELETE: Software wallet you created\n")
            f.write("3. Transfer Midnight tokens to NEW secure hardware wallet\n")
            f.write("4. Delete entire project folder\n")
            f.write("5. Clear browser cache/history\n")
            f.write("6. Restart computer to clear memory\n")
            f.write("7. Abandon OLD wallet completely\n\n")
            
            f.write("SECURITY REMINDER:\n")
            f.write("- Your OLD wallet seed is now compromised\n")
            f.write("- Never use OLD wallet addresses for receiving anything\n")
            f.write("- All future transactions should use your NEW secure wallet\n")
            f.write("- The WIF private key gives full control over this Bitcoin address\n")
            f.write("- Only use this for the Midnight claim, then delete immediately\n")
        
        # Set restrictive permissions on instructions file
        os.chmod(instructions_file, 0o600)
        
        logger.info(f"Instructions saved: {instructions_file.name}")
        return str(instructions_file)