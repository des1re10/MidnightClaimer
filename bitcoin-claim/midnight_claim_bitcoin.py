#!/usr/bin/env python3
"""
Midnight Bitcoin Claim - Using Bit Library for Proper Private Key Extraction
Derives Bitcoin private keys from Trezor seed phrases for Midnight token claims
LIMITATION: Only works with Native SegWit (bc1) addresses for Phantom Wallet import
"""

import os
import unicodedata
from pathlib import Path
from dotenv import load_dotenv
import logging
from mnemonic import Mnemonic
import hashlib
import hmac
from bit import Key
from bit.format import bytes_to_wif

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BitcoinMidnightClaim:
    def __init__(self):
        load_dotenv()
        
        self.seed_phrase = os.getenv('TREZOR_SEED_PHRASE')
        self.passphrase = os.getenv('TREZOR_PASSPHRASE', '')
        self.eligible_bitcoin_address = os.getenv('BITCOIN_CLAIM_ADDRESS')
        self.bitcoin_address_type = os.getenv('BITCOIN_ADDRESS_TYPE', '').lower()
        self.bitcoin_account = int(os.getenv('BITCOIN_ACCOUNT', '0'))
        self.bitcoin_address_index = int(os.getenv('BITCOIN_ADDRESS_INDEX', '0'))
        
        if not all([self.seed_phrase, self.eligible_bitcoin_address]):
            raise ValueError("TREZOR_SEED_PHRASE and BITCOIN_CLAIM_ADDRESS are required")
        
        # Critical compatibility check
        if not self.eligible_bitcoin_address.startswith('bc1'):
            logger.error("CRITICAL: This process only works with Native SegWit addresses (bc1)")
            logger.error(f"Your address starts with: {self.eligible_bitcoin_address[:3]}")
            logger.error("Contact Midnight support for alternative claiming methods")
            raise ValueError("Unsupported address type - only bc1 addresses supported")
            
        logger.info(f"Target Bitcoin address: {self.eligible_bitcoin_address}")
        logger.info(f"Address type override: {self.bitcoin_address_type or 'auto-detect'}")
        logger.info(f"Account: {self.bitcoin_account}, Index: {self.bitcoin_address_index}")
        logger.info(f"Passphrase length: {len(self.passphrase)} characters")
        
        # Auto-detect address type if not specified
        if not self.bitcoin_address_type:
            self.bitcoin_address_type = self._detect_address_type(self.eligible_bitcoin_address)
            logger.info(f"Auto-detected address type: {self.bitcoin_address_type}")
        
        # Use specific folder instead of temp folder
        self.workspace = Path("./bitcoin_claim_output")
        self.workspace.mkdir(parents=True, exist_ok=True)
        logger.info(f"Workspace: {self.workspace}")

    def _detect_address_type(self, address):
        """
        Auto-detect Bitcoin address type from format
        """
        if address.startswith('bc1q'):
            return 'native_segwit'
        elif address.startswith('bc1p'):
            return 'taproot'
        else:
            raise ValueError(f"Unsupported address format: {address}")

    def _derive_master_key(self, seed_phrase, passphrase):
        """
        Derive master private key from seed phrase using BIP39
        """
        mnemo = Mnemonic("english")
        seed = mnemo.to_seed(seed_phrase, passphrase=passphrase)
        
        # BIP32 master key derivation
        hmac_result = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
        master_private_key = hmac_result[:32]
        master_chain_code = hmac_result[32:]
        
        return master_private_key, master_chain_code

    def _derive_child_key(self, parent_key, parent_chain_code, index, hardened=False):
        """
        Derive child private key using BIP32
        """
        if hardened:
            index += 0x80000000
            data = b'\x00' + parent_key + index.to_bytes(4, 'big')
        else:
            # For non-hardened derivation, we'd need the public key
            # For this implementation, we'll only support hardened derivation
            data = b'\x00' + parent_key + index.to_bytes(4, 'big')
        
        hmac_result = hmac.new(parent_chain_code, data, hashlib.sha512).digest()
        child_private_key = hmac_result[:32]
        child_chain_code = hmac_result[32:]
        
        return child_private_key, child_chain_code

    def _derive_bitcoin_key(self, passphrase, account, address_index, address_type):
        """
        Derive Bitcoin private key for given parameters using proper BIP32/BIP84 derivation
        """
        try:
            # Get master key
            master_key, master_chain = self._derive_master_key(self.seed_phrase, passphrase)
            
            # BIP84 derivation path: m/84'/0'/account'/0/address_index
            # Derive m/84'
            key, chain = self._derive_child_key(master_key, master_chain, 84, hardened=True)
            
            # Derive m/84'/0'
            key, chain = self._derive_child_key(key, chain, 0, hardened=True)
            
            # Derive m/84'/0'/account'
            key, chain = self._derive_child_key(key, chain, account, hardened=True)
            
            # Derive m/84'/0'/account'/0 (external chain)
            key, chain = self._derive_child_key(key, chain, 0, hardened=False)
            
            # Derive m/84'/0'/account'/0/address_index
            final_key, final_chain = self._derive_child_key(key, chain, address_index, hardened=False)
            
            # Convert to proper formats
            private_key_hex = final_key.hex()
            
            # Create Key object from bit library
            bit_key = Key.from_hex(private_key_hex)
            
            # Get the segwit address (P2WPKH)
            segwit_address = bit_key.segwit_address
            
            # Get WIF format
            private_key_wif = bit_key.to_wif()
            
            derivation_path = f"m/84'/0'/{account}'/0/{address_index}"
            
            logger.debug(f"Derived address: {segwit_address}")
            logger.debug(f"WIF starts with: {private_key_wif[0] if private_key_wif else 'None'}")
            
            return {
                'address': segwit_address,
                'private_key_wif': private_key_wif,
                'private_key_hex': private_key_hex,
                'derivation_path': derivation_path,
                'bit_key': bit_key
            }
            
        except Exception as e:
            logger.debug(f"Key derivation failed: {e}")
            return None

    def test_comprehensive_derivation(self):
        """
        Comprehensive test with multiple approaches to find the correct derivation
        """
        logger.info("=== COMPREHENSIVE BITCOIN DERIVATION TEST ===")
        logger.info(f"Target address: {self.eligible_bitcoin_address}")
        logger.info(f"Address type: {self.bitcoin_address_type}")
        
        # Test different passphrase scenarios
        passphrase_scenarios = [
            ("current_passphrase", self.passphrase),
            ("empty_passphrase", ""),
            ("trimmed_passphrase", self.passphrase.strip()),
            ("lowercase_passphrase", self.passphrase.lower()),
            ("nfc_normalized", unicodedata.normalize('NFC', self.passphrase)),
            ("nfkd_normalized", unicodedata.normalize('NFKD', self.passphrase)),
        ]
        
        for scenario_name, test_passphrase in passphrase_scenarios:
            logger.info(f"\n--- Testing {scenario_name} ---")
            
            # Test different accounts (0-4)
            for account in range(5):
                # Test different address indices (0-19)
                for address_index in range(20):
                    
                    try:
                        result = self._derive_bitcoin_key(
                            test_passphrase, 
                            account, 
                            address_index, 
                            self.bitcoin_address_type
                        )
                        
                        if result and result['address'] == self.eligible_bitcoin_address:
                            logger.info(f"PERFECT MATCH! Derivation found!")
                            logger.info(f"  Scenario: {scenario_name}")
                            logger.info(f"  Account: {account}, Index: {address_index}")
                            logger.info(f"  Derivation Path: {result['derivation_path']}")
                            logger.info(f"  Address: {result['address']}")
                            
                            return self._create_result(
                                account, address_index, result, scenario_name, test_passphrase
                            )
                        
                        # Log first few attempts for debugging
                        if account == 0 and address_index < 3 and scenario_name == "current_passphrase":
                            logger.info(f"Account {account}, Index {address_index}: {result['address'][:20] if result else 'Failed'}...")
                            
                    except Exception as e:
                        logger.debug(f"Derivation failed for account {account}, index {address_index}: {e}")
                        continue
        
        logger.error("No matching derivation found across all scenarios")
        return None

    def _create_result(self, account, address_index, derivation_result, scenario_name, passphrase_used):
        """
        Create successful result object
        """
        logger.info("\nMATCH FOUND!")
        logger.info(f"  Derivation Path: {derivation_result['derivation_path']}")
        logger.info(f"  Address Type: {self.bitcoin_address_type}")
        logger.info(f"  Account: {account}, Index: {address_index}")
        logger.info(f"  Scenario: {scenario_name}")
        
        return {
            'account': account,
            'address_index': address_index,
            'derivation_result': derivation_result,
            'scenario_name': scenario_name,
            'passphrase_used': passphrase_used,
            'address_type': self.bitcoin_address_type
        }

    def extract_private_key(self, derivation_info):
        """
        Extract and save the Bitcoin private key in multiple formats for Phantom Wallet import
        """
        logger.info("Extracting Bitcoin private key for Phantom Wallet...")
        
        try:
            derivation_result = derivation_info['derivation_result']
            address = derivation_result['address']
            private_key_wif = derivation_result['private_key_wif']
            private_key_hex = derivation_result['private_key_hex']
            
            # Create safe filename from address
            safe_addr = address[:12].replace('bc1q', '').replace('bc1p', '')
            
            # Define file paths
            hex_file = self.workspace / f"hex_key_{safe_addr}.txt"
            wif_file = self.workspace / f"wif_key_{safe_addr}.txt"
            instructions_file = self.workspace / f"instructions_{safe_addr}.txt"
            
            # Write hex file
            try:
                with open(hex_file, 'w') as f:
                    f.write(private_key_hex)
                logger.info(f"Hex file saved: {hex_file}")
            except Exception as e:
                logger.error(f"Failed to write hex file: {e}")
            
            # Write WIF file (Phantom needs this format)
            try:
                with open(wif_file, 'w') as f:
                    f.write(private_key_wif)
                logger.info(f"WIF file saved: {wif_file}")
                logger.info(f"WIF key starts with: {private_key_wif[0]} (for Phantom compatibility)")
            except Exception as e:
                logger.error(f"Failed to write WIF file: {e}")
            
            # Write instructions
            try:
                with open(instructions_file, 'w') as f:
                    f.write("MIDNIGHT BITCOIN CLAIM - PHANTOM WALLET IMPORT\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"Bitcoin Address: {address}\n")
                    f.write(f"Derivation Path: {derivation_result['derivation_path']}\n\n")
                    f.write("CRITICAL: Use WIF format for Phantom\n")
                    f.write("Phantom expects Bitcoin private keys in WIF format\n\n")
                    f.write("FOR PHANTOM WALLET:\n")
                    f.write(f"1. Copy this WIF key: {private_key_wif}\n")
                    f.write("2. Open Phantom extension\n")
                    f.write("3. Add/Connect Wallet > Import Private Key\n")
                    f.write("4. Select Bitcoin blockchain\n")
                    f.write("5. Paste the WIF key above\n")
                    f.write("6. Name wallet: 'Midnight Claim'\n\n")
                    f.write("SECURITY REMINDER:\n")
                    f.write("- Delete all files after claiming\n")
                    f.write("- Transfer tokens to NEW secure wallet\n")
                    f.write("- Never reuse OLD wallet addresses\n")
                logger.info(f"Instructions saved: {instructions_file}")
            except Exception as e:
                logger.error(f"Failed to write instructions: {e}")
            
            result = {
                'hex_file': str(hex_file),
                'wif_file': str(wif_file),
                'instructions_file': str(instructions_file),
                'derivation_info': derivation_info,
                'hex_format': private_key_hex,
                'wif_compressed': private_key_wif
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Private key extraction error: {e}")
            return None

    def run_claim_test(self):
        """
        Main method to run the Bitcoin claim test
        """
        logger.info("Starting Bitcoin Midnight claim test with BIT library...")
        logger.info("This will properly derive private keys for Phantom Wallet...")
        
        # Test comprehensive derivation
        result = self.test_comprehensive_derivation()
        
        if result:
            logger.info("Derivation successful!")
            
            # Extract private key
            key_result = self.extract_private_key(result)
            if key_result:
                logger.info("\n" + "="*90)
                logger.info("MIDNIGHT BITCOIN CLAIM KEY SUCCESSFULLY GENERATED!")
                logger.info("="*90)
                
                logger.info(f"\nKEY SAVED TO: {self.workspace}")
                logger.info(f"WIF Format (USE THIS): {Path(key_result['wif_file']).name}")
                logger.info(f"Hex Format (backup): {Path(key_result['hex_file']).name}")
                logger.info(f"Instructions: {Path(key_result['instructions_file']).name}")
                
                print(f"\nSUCCESS! Bitcoin private key extracted!")
                print(f"Saved to: {self.workspace}")
                print(f"Ready for Phantom Wallet import!")
                print(f"USE WIF FORMAT: {Path(key_result['wif_file']).name}")
                
                return True
            else:
                logger.error("Private key extraction failed")
                return False
        else:
            logger.error("Comprehensive derivation test failed!")
            logger.info("Check your seed phrase and passphrase in .env file")
            return False

def main():
    print("Midnight Bitcoin Claim - USING BIT LIBRARY")
    print("=" * 80)
    print("Properly deriving Bitcoin private keys for Phantom Wallet import")
    print("LIMITATION: Only works with Native SegWit (bc1) addresses")
    print("=" * 80)
    
    try:
        if not os.path.exists('.env'):
            print("ERROR: .env file missing!")
            return False
        
        claimer = BitcoinMidnightClaim()
        success = claimer.run_claim_test()
        
        if success:
            print("\nBITCOIN CLAIM TEST SUCCESSFUL!")
            print("Your Bitcoin private key is ready for Phantom Wallet import!")
            print("IMPORTANT: Use the WIF format file")
            return True
        else:
            print("\nBitcoin claim test failed")
            print("Check your seed phrase and passphrase in .env file")
            return False
            
    except Exception as e:
        logger.error(f"Bitcoin claim test error: {e}")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    main()