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

logger = logging.getLogger(__name__)

class CardanoService:
    """Service class for Cardano key derivation and validation"""
    
    def __init__(self):
        self.network = Network.MAINNET
        self.mnemo = Mnemonic("english")
        
    def validate_seed_phrase(self, seed_phrase: str) -> bool:
        """Validate mnemonic seed phrase"""
        try:
            return self.mnemo.check(seed_phrase.strip())
        except Exception:
            return False
    
    def detect_address_type(self, address: str) -> str:
        """Detect Cardano address type"""
        if address.startswith('addr1'):
            return 'shelley'
        elif address.startswith('Ae2') or address.startswith('Ddz'):
            return 'byron'
        else:
            return 'unknown'
    
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
                wallet = HDWallet.from_mnemonic(
                    mnemonic=seed_phrase,
                    passphrase=test_passphrase
                )
                
                # Test different account indices for payment path
                for account in range(5):
                    payment_path = f"m/1852'/1815'/{account}'/0/0"
                    
                    try:
                        derived_payment = wallet.derive_from_path(payment_path)
                        payment_vkey = PaymentVerificationKey.from_primitive(derived_payment.public_key)
                        
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
                                    derived_stake = wallet.derive_from_path(stake_path)
                                    stake_vkey = PaymentVerificationKey.from_primitive(derived_stake.public_key)
                                    stake_hash = stake_vkey.hash().payload.hex()
                                    
                                    if stake_hash.lower() == stake_checksum.lower():
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
                                        
                                except Exception:
                                    continue
                                    
                    except Exception:
                        current_combination += 3 * 20  # Skip this account's stake combinations
                        continue
                        
            except Exception:
                current_combination += 5 * 3 * 20  # Skip this scenario's combinations
                continue
        
        if progress_callback:
            progress_callback("No matching derivation found", 100)
        return None
    
    def _create_result(self, account: int, payment_index: int, stake_index: Optional[int],
                      payment_path: str, stake_path: Optional[str],
                      payment_wallet, stake_wallet, address: str, address_type: str,
                      scenario_name: str, passphrase_used: str) -> Dict:
        """Create result dictionary"""
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
            
            safe_addr = address[:12]
            process_id = os.getpid()
            
            # Payment Key
            payment_extended_key = ExtendedSigningKey.from_hdwallet(payment_wallet)
            payment_skey_content = payment_extended_key.to_json()
            
            payment_skey_file = output_dir / f"midnight_payment_{safe_addr}_{process_id}.skey"
            with open(payment_skey_file, 'w') as f:
                f.write(payment_skey_content)
            
            # Stake Key (if present)
            stake_skey_file = None
            if stake_wallet:
                stake_extended_key = ExtendedSigningKey.from_hdwallet(stake_wallet)
                stake_skey_content = stake_extended_key.to_json()
                
                stake_skey_file = output_dir / f"midnight_stake_{safe_addr}_{process_id}.skey"
                with open(stake_skey_file, 'w') as f:
                    f.write(stake_skey_content)
            
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
            f.write("🎉 MIDNIGHT CARDANO CLAIM KEYS SUCCESSFULLY GENERATED!\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("DERIVATION DETAILS:\n")
            f.write(f"Claim Address: {key_info['address']}\n")
            f.write(f"Payment Path: {key_info['derivation_info']['payment_path']}\n")
            if key_info['derivation_info']['stake_path']:
                f.write(f"Stake Path: {key_info['derivation_info']['stake_path']}\n")
            f.write(f"Address Type: {key_info['derivation_info']['address_type']}\n\n")
            
            f.write("🔑 PRIVATE KEY FILES:\n")
            f.write(f"Payment Key: {Path(key_info['payment_key_file']).name}\n")
            if key_info['stake_key_file']:
                f.write(f"Stake Key: {Path(key_info['stake_key_file']).name}\n")
            f.write("\n")
            
            f.write("🚀 ETERNL IMPORT INSTRUCTIONS:\n")
            f.write("=" * 50 + "\n")
            f.write("1. Open Eternl Wallet (https://eternl.io)\n")
            f.write("2. 'Add Wallet' → 'Restore' → 'Advanced'\n")
            f.write("3. Select 'Import from CLI signing key'\n")
            f.write(f"4. Upload file: {Path(key_info['payment_key_file']).name}\n")
            f.write("5. Wallet name: 'Midnight Claim'\n")
            f.write("6. Create wallet\n")
            f.write("7. Connect to Midnight Portal\n")
            f.write("8. Execute claim\n\n")
            
            f.write("⚠️ IMMEDIATELY AFTER CLAIMING:\n")
            f.write("=" * 30 + "\n")
            f.write(f"1. DELETE: {Path(key_info['payment_key_file']).name}\n")
            if key_info['stake_key_file']:
                f.write(f"2. DELETE: {Path(key_info['stake_key_file']).name}\n")
            f.write("3. Delete Eternl wallet\n")
            f.write("4. Transfer Midnight tokens to hardware wallet\n")
            f.write("5. Delete entire folder\n")
        
        return str(instructions_file)