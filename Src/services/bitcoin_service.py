#!/usr/bin/env python3
"""
Bitcoin Service Layer for MidnightClaimer GUI
Extracted from midnight_claim_bitcoin.py for use in GUI application
"""

import os
import unicodedata
import logging
from pathlib import Path
from typing import Optional, Dict, Callable
from mnemonic import Mnemonic
from bitcoinlib.keys import HDKey

logger = logging.getLogger(__name__)

class BitcoinService:
    """Service class for Bitcoin key derivation and validation"""
    
    def __init__(self):
        self.mnemo = Mnemonic("english")
    
    def validate_seed_phrase(self, seed_phrase: str) -> bool:
        """Validate mnemonic seed phrase"""
        try:
            return self.mnemo.check(seed_phrase.strip())
        except Exception:
            return False
    
    def detect_address_type(self, address: str) -> str:
        """Auto-detect Bitcoin address type from format"""
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
            return f"m/44'/0'/{account}'/{change}/{index}"
        elif address_type == 'segwit':
            return f"m/49'/0'/{account}'/{change}/{index}"
        elif address_type == 'native_segwit':
            return f"m/84'/0'/{account}'/{change}/{index}"
        else:
            raise ValueError(f"Unsupported address type: {address_type}")
    
    def derive_bitcoin_key(self, seed_phrase: str, passphrase: str, account: int, 
                          address_index: int, address_type: str) -> Optional[Dict]:
        """Derive Bitcoin private key for given parameters"""
        try:
            # Create seed from mnemonic
            seed = self.mnemo.to_seed(seed_phrase, passphrase=passphrase)
            
            # Create master key
            master_key = HDKey.from_seed(seed)
            
            # Get derivation path
            derivation_path = self.get_derivation_path(address_type, account, 0, address_index)
            
            # Derive key
            derived_key = master_key.subkey_for_path(derivation_path)
            
            # Generate address based on type
            if address_type == 'legacy':
                address = derived_key.address()
            elif address_type == 'segwit':
                address = derived_key.address(script_type='p2sh_p2wpkh')
            elif address_type == 'native_segwit':
                address = derived_key.address(script_type='p2wpkh')
            else:
                raise ValueError(f"Unsupported address type: {address_type}")
            
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
        
        Args:
            seed_phrase: The mnemonic seed phrase
            passphrase: The passphrase (can be empty)
            eligible_address: Target Bitcoin address to match
            address_type: Bitcoin address type (legacy, segwit, native_segwit)
            progress_callback: Function to call with progress updates (message, percentage)
            
        Returns:
            Dictionary with derivation details if successful, None otherwise
        """
        if progress_callback:
            progress_callback("Starting comprehensive Bitcoin derivation test...", 0)
        
        # Passphrase scenarios to test
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
                            
                            return {
                                'account': account,
                                'address_index': address_index,
                                'derivation_result': result,
                                'scenario_name': scenario_name,
                                'passphrase_used': test_passphrase,
                                'address_type': address_type
                            }
                        
                    except Exception as e:
                        logger.debug(f"Derivation failed for account {account}, index {address_index}: {e}")
                        continue
        
        if progress_callback:
            progress_callback("No matching derivation found", 100)
        return None
    
    def extract_private_key(self, derivation_info: Dict, output_dir: Path) -> Dict[str, str]:
        """
        Extract and save the Bitcoin private key in WIF format
        
        Returns:
            Dictionary with file paths and key information
        """
        try:
            derivation_result = derivation_info['derivation_result']
            address = derivation_result['address']
            private_key_wif = derivation_result['private_key_wif']
            
            # Create safe filename from address
            safe_addr = address[:12].replace('1', '').replace('3', '').replace('bc1q', 'bc1q')
            process_id = os.getpid()
            
            # Save WIF private key
            wif_file = output_dir / f"midnight_bitcoin_private_{safe_addr}_{process_id}.wif"
            with open(wif_file, 'w') as f:
                f.write(private_key_wif)
            
            return {
                'wif_file': str(wif_file),
                'address': address,
                'private_key_wif': private_key_wif,
                'derivation_info': derivation_info
            }
            
        except Exception as e:
            logger.error(f"Private key extraction error: {e}")
            raise
    
    def create_instructions_file(self, key_info: Dict, output_dir: Path) -> str:
        """Create instruction file for user"""
        address = key_info['address']
        safe_addr = address[:12].replace('1', '').replace('3', '').replace('bc1q', 'bc1q')
        process_id = os.getpid()
        
        instructions_file = output_dir / f"BITCOIN_INSTRUCTIONS_{safe_addr}_{process_id}.txt"
        
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write("🎉 MIDNIGHT BITCOIN CLAIM KEY SUCCESSFULLY GENERATED!\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("DERIVATION DETAILS:\n")
            f.write(f"Bitcoin Address: {address}\n")
            f.write(f"Derivation Path: {key_info['derivation_info']['derivation_result']['derivation_path']}\n")
            f.write(f"Address Type: {key_info['derivation_info']['address_type']}\n")
            f.write(f"Account: {key_info['derivation_info']['account']}\n")
            f.write(f"Address Index: {key_info['derivation_info']['address_index']}\n\n")
            
            f.write("🔑 PRIVATE KEY FILE:\n")
            f.write(f"WIF Format: {Path(key_info['wif_file']).name}\n\n")
            
            f.write("🚀 SOFTWARE WALLET IMPORT INSTRUCTIONS:\n")
            f.write("=" * 50 + "\n")
            f.write("OPTION 1: Electrum Wallet (Recommended)\n")
            f.write("1. Download Electrum from electrum.org\n")
            f.write("2. File → New/Restore\n")
            f.write("3. Choose 'Import Bitcoin addresses or private keys'\n")
            f.write(f"4. Paste WIF key from: {Path(key_info['wif_file']).name}\n")
            f.write("5. Next → Create\n")
            f.write("6. Connect to Midnight Portal\n")
            f.write("7. Execute claim\n\n")
            
            f.write("OPTION 2: Sparrow Wallet\n")
            f.write("1. Download Sparrow from sparrowwallet.com\n")
            f.write("2. File → New Wallet\n")
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
            
            f.write("⚠️ IMMEDIATELY AFTER CLAIMING:\n")
            f.write("=" * 30 + "\n")
            f.write(f"1. DELETE: {Path(key_info['wif_file']).name}\n")
            f.write("2. DELETE: Software wallet you created\n")
            f.write("3. Transfer Midnight tokens to NEW secure hardware wallet\n")
            f.write("4. Delete entire project folder\n")
            f.write("5. Clear browser cache/history\n")
            f.write("6. Abandon OLD wallet completely\n\n")
            
            f.write("🔐 SECURITY REMINDER:\n")
            f.write("- Your OLD wallet seed is now compromised\n")
            f.write("- Never use OLD wallet addresses for receiving anything\n")
            f.write("- All future transactions should use your NEW secure wallet\n")
        
        return str(instructions_file)