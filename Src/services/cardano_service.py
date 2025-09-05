#!/usr/bin/env python3
"""
Cardano Service Layer for MidnightClaimer GUI
Extracted from midnight_claim_cardano.py for use in GUI application
"""

import os
import unicodedata
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple, List, Callable
from pycardano import HDWallet, PaymentVerificationKey, Address, Network
from pycardano.key import ExtendedSigningKey
from mnemonic import Mnemonic
import re

logger = logging.getLogger(__name__)

class CardanoService:
    """Service class for Cardano key derivation and validation"""
    
    def __init__(self):
        self.network = Network.MAINNET
        self.mnemo = Mnemonic("english")
        
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
    
    def validate_cardano_address_format(self, address: str) -> bool:
        """Validate Cardano address format"""
        try:
            if not address or not address.strip():
                return False
            
            address = address.strip()
            
            # Shelley addresses (addr1)
            if address.startswith('addr1'):
                if len(address) < 50 or len(address) > 120:
                    return False
                # Basic bech32 format check for addr1
                try:
                    # addr1 addresses should contain only valid bech32 characters
                    if not all(c in 'qpzry9x8gf2tvdw0s3jn54khce6mua7l' for c in address[5:]):
                        return False
                    return True
                except:
                    return False
            
            # Byron addresses (Ae2, Ddz)
            elif address.startswith('Ae2') or address.startswith('Ddz'):
                if len(address) < 50 or len(address) > 120:
                    return False
                # Byron addresses use base58 encoding
                try:
                    import base58
                    base58.b58decode(address)
                    return True
                except:
                    # If base58 library not available, do basic validation
                    # Byron addresses should contain alphanumeric characters
                    if not all(c.isalnum() for c in address):
                        return False
                    return True
            else:
                return False
                
        except Exception as e:
            logger.debug(f"Address format validation failed: {e}")
            return False
    
    def validate_stake_checksum(self, checksum: str) -> bool:
        """Validate stake key checksum format"""
        try:
            if not checksum or not checksum.strip():
                return False
            
            checksum = checksum.strip()
            
            # Must be exactly 64 hex characters
            if len(checksum) != 64:
                return False
            
            # Must contain only hex characters
            if not re.match(r'^[0-9a-fA-F]{64}$', checksum):
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Stake checksum validation failed: {e}")
            return False
    
    def detect_address_type(self, address: str) -> str:
        """Detect Cardano address type"""
        if not self.validate_cardano_address_format(address):
            raise ValueError(f"Invalid Cardano address format: {address}")
            
        if address.startswith('addr1'):
            return 'shelley'
        elif address.startswith('Ae2') or address.startswith('Ddz'):
            return 'byron'
        else:
            return 'unknown'
    
    def _validate_derivation_path(self, path: str) -> bool:
        """Validate Cardano derivation path format"""
        try:
            # Should match pattern: m/1852'/1815'/account'/change/index
            pattern = r"^m/1852'/1815'/\d+'/[0-2]/\d+$"
            return bool(re.match(pattern, path))
        except:
            return False
    
    def _create_cardano_wallet(self, seed_phrase: str, passphrase: str) -> Optional[HDWallet]:
        """Create Cardano HDWallet with validation"""
        try:
            if not self.validate_seed_phrase(seed_phrase):
                logger.debug("Invalid seed phrase for wallet creation")
                return None
            
            wallet = HDWallet.from_mnemonic(
                mnemonic=seed_phrase,
                passphrase=passphrase
            )
            
            # Validate wallet was created successfully
            if not wallet:
                logger.debug("Failed to create HDWallet")
                return None
            
            # Test basic derivation to ensure wallet is functional
            try:
                test_path = "m/1852'/1815'/0'/0/0"
                test_derived = wallet.derive_from_path(test_path)
                if not test_derived:
                    logger.debug("Wallet failed basic derivation test")
                    return None
            except Exception as e:
                logger.debug(f"Wallet derivation test failed: {e}")
                return None
            
            return wallet
            
        except Exception as e:
            logger.debug(f"Wallet creation failed: {e}")
            return None
    
    def test_derivation_comprehensive(
        self,
        seed_phrase: str,
        passphrase: str,
        claim_address: str,
        stake_checksum: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Optional[Dict]:
        """
        Comprehensive derivation test with progress updates
        
        Args:
            seed_phrase: The mnemonic seed phrase
            passphrase: The passphrase (can be empty)
            claim_address: Target address to match
            stake_checksum: Expected stake key checksum
            progress_callback: Function to call with progress updates (message, percentage)
            
        Returns:
            Dictionary with derivation details if successful, None otherwise
        """
        if progress_callback:
            progress_callback("Starting comprehensive derivation test...", 0)
        
        # Validate inputs first
        if not self.validate_seed_phrase(seed_phrase):
            if progress_callback:
                progress_callback("Invalid seed phrase format", 100)
            logger.error("Invalid seed phrase provided")
            return None
        
        if not self.validate_cardano_address_format(claim_address):
            if progress_callback:
                progress_callback("Invalid target address format", 100)
            logger.error(f"Invalid target address format: {claim_address}")
            return None
        
        if not self.validate_stake_checksum(stake_checksum):
            if progress_callback:
                progress_callback("Invalid stake checksum format", 100)
            logger.error(f"Invalid stake checksum format: {stake_checksum}")
            return None
        
        # Passphrase scenarios to test
        passphrase_scenarios = [
            ("current_passphrase", passphrase),
            ("empty_passphrase", ""),
            ("trimmed_passphrase", passphrase.strip()),
            ("lowercase_passphrase", passphrase.lower()),
            ("nfc_normalized", unicodedata.normalize('NFC', passphrase)),
            ("nfkd_normalized", unicodedata.normalize('NFKD', passphrase)),
        ]
        
        total_combinations = len(passphrase_scenarios) * 5 * 3 * 20  # scenarios * accounts * stake_accounts * stake_indices
        current_combination = 0
        
        for scenario_name, test_passphrase in passphrase_scenarios:
            if progress_callback:
                progress_callback(f"Testing {scenario_name}...", int(current_combination / total_combinations * 100))
            
            try:
                wallet = self._create_cardano_wallet(seed_phrase, test_passphrase)
                if not wallet:
                    current_combination += 5 * 3 * 20  # Skip this scenario's combinations
                    continue
                
                # Test different account indices for payment path
                for account in range(5):
                    payment_path = f"m/1852'/1815'/{account}'/0/0"
                    
                    try:
                        # Validate path format
                        if not self._validate_derivation_path(payment_path):
                            logger.debug(f"Invalid payment path format: {payment_path}")
                            current_combination += 3 * 20  # Skip this account's combinations
                            continue
                        
                        derived_payment = wallet.derive_from_path(payment_path)
                        if not derived_payment:
                            current_combination += 3 * 20  # Skip this account's combinations
                            continue
                        
                        payment_vkey = PaymentVerificationKey.from_primitive(derived_payment.public_key)
                        if not payment_vkey:
                            current_combination += 3 * 20  # Skip this account's combinations
                            continue
                        
                        # Test payment-only address
                        address_v = Address(payment_vkey.hash(), None, self.network)
                        
                        if str(address_v) == claim_address:
                            if progress_callback:
                                progress_callback("Payment match found!", 100)
                            return self._create_result(
                                account, 0, None, payment_path, None,
                                derived_payment, None, str(address_v), 'payment_only',
                                scenario_name, test_passphrase
                            )
                        
                        # Test with stake keys
                        for stake_account in range(3):
                            for stake_index in range(20):
                                current_combination += 1
                                
                                if current_combination % 50 == 0 and progress_callback:
                                    progress_callback(
                                        f"Testing account {account}, stake {stake_account}/{stake_index}...",
                                        int(current_combination / total_combinations * 100)
                                    )
                                
                                stake_path = f"m/1852'/1815'/{stake_account}'/2/{stake_index}"
                                
                                try:
                                    # Validate stake path format
                                    if not self._validate_derivation_path(stake_path):
                                        logger.debug(f"Invalid stake path format: {stake_path}")
                                        continue
                                    
                                    derived_stake = wallet.derive_from_path(stake_path)
                                    if not derived_stake:
                                        continue
                                    
                                    stake_vkey = PaymentVerificationKey.from_primitive(derived_stake.public_key)
                                    if not stake_vkey:
                                        continue
                                    
                                    stake_hash = stake_vkey.hash().payload.hex()
                                    
                                    # Validate stake hash format
                                    if not stake_hash or len(stake_hash) != 56:  # 28 bytes = 56 hex chars
                                        continue
                                    
                                    if stake_hash.lower() == stake_checksum.lower():
                                        if progress_callback:
                                            progress_callback("Stake checksum match found!", 75)
                                        
                                        # Create complete address
                                        address_q = Address(payment_vkey.hash(), stake_vkey.hash(), self.network)
                                        
                                        if str(address_q) == claim_address:
                                            if progress_callback:
                                                progress_callback("Perfect match found!", 100)
                                            return self._create_result(
                                                account, 0, stake_index, payment_path, stake_path,
                                                derived_payment, derived_stake, str(address_q), 'payment_stake',
                                                scenario_name, test_passphrase
                                            )
                                        else:
                                            logger.warning("Stake checksum matches but final address doesn't match")
                                            
                                except Exception as e:
                                    logger.debug(f"Stake derivation failed for {stake_path}: {e}")
                                    continue
                                    
                    except Exception as e:
                        logger.debug(f"Payment derivation failed for account {account}: {e}")
                        current_combination += 3 * 20  # Skip this account's stake combinations
                        continue
                        
            except Exception as e:
                logger.error(f"Wallet creation failed for {scenario_name}: {e}")
                current_combination += 5 * 3 * 20  # Skip this scenario's combinations
                continue
        
        if progress_callback:
            progress_callback("No matching derivation found", 100)
        return None
    
    def _create_result(self, account: int, payment_index: int, stake_index: Optional[int],
                      payment_path: str, stake_path: Optional[str],
                      payment_wallet, stake_wallet, address: str, address_type: str,
                      scenario_name: str, passphrase_used: str) -> Dict:
        """Create result dictionary with validation"""
        
        # Validate inputs
        if account < 0 or payment_index < 0:
            raise ValueError("Account and payment index must be non-negative")
        
        if stake_index is not None and stake_index < 0:
            raise ValueError("Stake index must be non-negative")
        
        if not self._validate_derivation_path(payment_path):
            raise ValueError(f"Invalid payment path: {payment_path}")
        
        if stake_path and not self._validate_derivation_path(stake_path):
            raise ValueError(f"Invalid stake path: {stake_path}")
        
        if not self.validate_cardano_address_format(address):
            raise ValueError(f"Invalid address: {address}")
        
        logger.info("Cardano derivation match found!")
        logger.info(f"  Payment Path: {payment_path}")
        if stake_path:
            logger.info(f"  Stake Path: {stake_path}")
        logger.info(f"  Address Type: {address_type}")
        logger.info(f"  Scenario: {scenario_name}")
        
        return {
            'account': account,
            'payment_index': payment_index,
            'stake_index': stake_index,
            'payment_path': payment_path,
            'stake_path': stake_path,
            'derived_payment_wallet': payment_wallet,
            'derived_stake_wallet': stake_wallet,
            'address': address,
            'address_type': address_type,
            'scenario_name': scenario_name,
            'passphrase_used': passphrase_used
        }
    
    def extract_keys(self, derivation_info: Dict, output_dir: Path) -> Dict[str, str]:
        """
        Extract private keys and save to files
        
        Returns:
            Dictionary with file paths and key information
        """
        try:
            address = derivation_info['address']
            payment_wallet = derivation_info['derived_payment_wallet']
            stake_wallet = derivation_info.get('derived_stake_wallet')
            
            # Validate address
            if not self.validate_cardano_address_format(address):
                raise ValueError(f"Invalid address for key extraction: {address}")
            
            safe_addr = address[:12]
            process_id = os.getpid()
            
            # Payment Key
            try:
                payment_extended_key = ExtendedSigningKey.from_hdwallet(payment_wallet)
                if not payment_extended_key:
                    raise ValueError("Failed to create payment extended key")
                
                payment_skey_content = payment_extended_key.to_json()
                if not payment_skey_content:
                    raise ValueError("Failed to generate payment key JSON")
                
                payment_skey_file = output_dir / f"midnight_payment_{safe_addr}_{process_id}.skey"
                with open(payment_skey_file, 'w') as f:
                    f.write(payment_skey_content)
                
                # Set restrictive permissions
                os.chmod(payment_skey_file, 0o600)
                
            except Exception as e:
                logger.error(f"Payment key extraction failed: {e}")
                raise ValueError(f"Payment key extraction failed: {e}")
            
            # Stake Key (if present)
            stake_skey_file = None
            if stake_wallet:
                try:
                    stake_extended_key = ExtendedSigningKey.from_hdwallet(stake_wallet)
                    if not stake_extended_key:
                        raise ValueError("Failed to create stake extended key")
                    
                    stake_skey_content = stake_extended_key.to_json()
                    if not stake_skey_content:
                        raise ValueError("Failed to generate stake key JSON")
                    
                    stake_skey_file = output_dir / f"midnight_stake_{safe_addr}_{process_id}.skey"
                    with open(stake_skey_file, 'w') as f:
                        f.write(stake_skey_content)
                    
                    # Set restrictive permissions
                    os.chmod(stake_skey_file, 0o600)
                    
                except Exception as e:
                    logger.error(f"Stake key extraction failed: {e}")
                    raise ValueError(f"Stake key extraction failed: {e}")
            
            return {
                'payment_key_file': str(payment_skey_file),
                'stake_key_file': str(stake_skey_file) if stake_skey_file else None,
                'address': address,
                'derivation_info': derivation_info
            }
            
        except Exception as e:
            logger.error(f"Key extraction error: {e}")
            raise
    
    def create_instructions_file(self, key_info: Dict, output_dir: Path) -> str:
        """Create instruction file for user"""
        safe_addr = key_info['address'][:12]
        process_id = os.getpid()
        
        instructions_file = output_dir / f"CARDANO_INSTRUCTIONS_{safe_addr}_{process_id}.txt"
        
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write("MIDNIGHT CARDANO CLAIM KEYS SUCCESSFULLY GENERATED!\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("DERIVATION DETAILS:\n")
            f.write(f"Claim Address: {key_info['address']}\n")
            f.write(f"Payment Path: {key_info['derivation_info']['payment_path']}\n")
            if key_info['derivation_info']['stake_path']:
                f.write(f"Stake Path: {key_info['derivation_info']['stake_path']}\n")
            f.write(f"Address Type: {key_info['derivation_info']['address_type']}\n")
            f.write(f"Scenario Used: {key_info['derivation_info']['scenario_name']}\n\n")
            
            f.write("PRIVATE KEY FILES:\n")
            f.write(f"Payment Key: {Path(key_info['payment_key_file']).name}\n")
            if key_info['stake_key_file']:
                f.write(f"Stake Key: {Path(key_info['stake_key_file']).name}\n")
            f.write("\n")
            
            f.write("ETERNL IMPORT INSTRUCTIONS:\n")
            f.write("=" * 50 + "\n")
            f.write("1. Open Eternl Wallet (https://eternl.io)\n")
            f.write("2. 'Add Wallet' → 'Restore' → 'Advanced'\n")
            f.write("3. Select 'Import from CLI signing key'\n")
            f.write(f"4. Upload file: {Path(key_info['payment_key_file']).name}\n")
            if key_info['stake_key_file']:
                f.write(f"5. Upload stake key: {Path(key_info['stake_key_file']).name}\n")
                f.write("6. Wallet name: 'Midnight Claim'\n")
                f.write("7. Create wallet\n")
            else:
                f.write("5. Skip stake key (payment-only wallet)\n")
                f.write("6. Wallet name: 'Midnight Claim'\n")
                f.write("7. Create wallet\n")
            f.write("8. Connect to Midnight Portal\n")
            f.write("9. Execute claim\n\n")
            
            f.write("SECURITY REQUIREMENTS - IMMEDIATELY AFTER CLAIMING:\n")
            f.write("=" * 50 + "\n")
            f.write(f"1. DELETE: {Path(key_info['payment_key_file']).name}\n")
            if key_info['stake_key_file']:
                f.write(f"2. DELETE: {Path(key_info['stake_key_file']).name}\n")
            f.write("3. Delete Eternl wallet\n")
            f.write("4. Transfer Midnight tokens to NEW secure hardware wallet\n")
            f.write("5. Delete entire project folder\n")
            f.write("6. Clear browser cache/history\n")
            f.write("7. Restart computer to clear memory\n")
            f.write("8. Abandon OLD wallet completely\n\n")
            
            f.write("SECURITY REMINDER:\n")
            f.write("- Your OLD wallet seed is now compromised\n")
            f.write("- Never use OLD wallet addresses for receiving anything\n")
            f.write("- All future transactions should use your NEW secure wallet\n")
        
        # Set restrictive permissions on instructions file
        os.chmod(instructions_file, 0o600)
        
        return str(instructions_file)