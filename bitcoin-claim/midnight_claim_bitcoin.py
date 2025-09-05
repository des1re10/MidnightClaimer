#!/usr/bin/env python3
"""
Midnight Bitcoin Claim - Phantom Wallet Bitcoin Private Key Extraction
Derives Bitcoin private keys from Trezor seed phrases for Midnight token claims
LIMITATION: Only works with Native SegWit (bc1) addresses for Phantom Wallet import
"""

import os
import unicodedata
from pathlib import Path
from dotenv import load_dotenv
import logging
from mnemonic import Mnemonic
from bitcoinlib.keys import HDKey

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BitcoinMidnightClaim:
    def __init__(self):
        load_dotenv()
        
        self.seed_phrase = os.getenv('TREZOR_SEED_PHRASE')
        self.passphrase = os.getenv('TREZOR_PASSPHRASE', '')
        self.eligible_bitcoin_address = os.getenv('BITCOIN_CLAIM_ADDRESS')  # Updated env var name
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
        if address.startswith('1'):
            logger.error("Legacy addresses (1...) are not supported by Phantom Wallet")
            raise ValueError("Legacy addresses not supported")
        elif address.startswith('3'):
            logger.error("SegWit addresses (3...) are not supported by Phantom Wallet")
            raise ValueError("SegWit addresses not supported")
        elif address.startswith('bc1q'):
            return 'native_segwit'
        elif address.startswith('bc1p'):
            return 'taproot'
        else:
            raise ValueError(f"Unknown Bitcoin address format: {address}")

    def _get_derivation_path(self, address_type, account, change, index):
        """
        Get BIP derivation path for different address types
        """
        if address_type == 'native_segwit':
            # BIP84: m/84'/0'/account'/change/index
            return f"m/84'/0'/{account}'/{change}/{index}"
        elif address_type == 'taproot':
            # BIP86: m/86'/0'/account'/change/index
            return f"m/86'/0'/{account}'/{change}/{index}"
        else:
            raise ValueError(f"Unsupported address type for Phantom: {address_type}")

    def _quick_verification_check(self):
        """
        Quick check to see if basic wallet creation works and log initial findings
        """
        logger.info("\n=== QUICK VERIFICATION ===")
        
        try:
            # Validate mnemonic
            mnemo = Mnemonic("english")
            if not mnemo.check(self.seed_phrase):
                logger.error("Invalid mnemonic seed phrase")
                return False
            
            logger.info("Wallet creation successful")
            logger.info(f"Address type detected: {self.bitcoin_address_type}")
            
            # Get derivation path for current setup
            derivation_path = self._get_derivation_path(
                self.bitcoin_address_type, 
                self.bitcoin_account, 
                0,  # External addresses (change=0)
                self.bitcoin_address_index
            )
            logger.info(f"Derivation path: {derivation_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Basic wallet creation failed: {e}")
            logger.error("This suggests a fundamental seed phrase or setup issue")
            return False

    def _derive_bitcoin_key(self, passphrase, account, address_index, address_type):
        """
        Derive Bitcoin private key for given parameters
        """
        try:
            # Create HDWallet from mnemonic
            mnemo = Mnemonic("english")
            seed = mnemo.to_seed(self.seed_phrase, passphrase=passphrase)
            
            # Create master key
            master_key = HDKey.from_seed(seed)
            
            # Get derivation path
            derivation_path = self._get_derivation_path(address_type, account, 0, address_index)
            
            # Derive key
            derived_key = master_key.subkey_for_path(derivation_path)
            
            # Generate address based on type
            if address_type == 'native_segwit':
                # P2WPKH
                address = derived_key.address(script_type='p2wpkh')
            elif address_type == 'taproot':
                # P2TR
                address = derived_key.address(script_type='p2tr')
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
            derived_key = derivation_result['derived_key']
            
            # Create safe filename from address
            safe_addr = address[:12].replace('bc1q', '').replace('bc1p', '')
            
            # Generate multiple formats for Phantom compatibility
            wif_compressed = private_key_wif
            
            # Try to get uncompressed WIF
            try:
                wif_uncompressed = derived_key.wif(compressed=False)
            except:
                wif_uncompressed = "Error generating uncompressed WIF"
            
            hex_format = private_key_hex
            
            # Define file paths
            hex_file = self.workspace / f"hex_key_{safe_addr}.txt"
            wif_file = self.workspace / f"wif_key_{safe_addr}.txt"
            instructions_file = self.workspace / f"instructions_{safe_addr}.txt"
            
            # Write hex file (most important)
            try:
                with open(hex_file, 'w') as f:
                    f.write(hex_format)
                logger.info(f"Hex file saved: {hex_file}")
            except Exception as e:
                logger.error(f"Failed to write hex file: {e}")
            
            # Write WIF file
            try:
                with open(wif_file, 'w') as f:
                    f.write(wif_compressed)
                logger.info(f"WIF file saved: {wif_file}")
            except Exception as e:
                logger.error(f"Failed to write WIF file: {e}")
            
            # Write simple instructions
            try:
                with open(instructions_file, 'w') as f:
                    f.write("MIDNIGHT BITCOIN CLAIM - PHANTOM WALLET IMPORT\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"Bitcoin Address: {address}\n")
                    f.write(f"Derivation Path: {derivation_result['derivation_path']}\n\n")
                    f.write("INSTRUCTIONS:\n")
                    f.write("1. Try HEX format first in Phantom\n")
                    f.write(f"   File: {hex_file.name}\n")
                    f.write(f"   Key: {hex_format}\n\n")
                    f.write("2. If HEX fails, try WIF format\n")
                    f.write(f"   File: {wif_file.name}\n")
                    f.write(f"   Key: {wif_compressed}\n\n")
                    f.write("PHANTOM STEPS:\n")
                    f.write("- Open Phantom extension\n")
                    f.write("- Add/Connect Wallet > Import Private Key\n")
                    f.write("- Select Bitcoin blockchain\n")
                    f.write("- Paste key from file above\n\n")
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
                'hex_format': hex_format,
                'wif_compressed': wif_compressed
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Private key extraction error: {e}")
            return None

    def _create_diagnostic_file(self):
        """
        Create diagnostic file for troubleshooting
        """
        diag_file = self.workspace / f"BITCOIN_DIAGNOSTIC_REPORT_{os.getpid()}.txt"
        try:
            with open(diag_file, 'w') as f:
                f.write("MIDNIGHT BITCOIN CLAIM COMPREHENSIVE DIAGNOSTIC REPORT\n")
                f.write("=" * 60 + "\n\n")
                f.write("ISSUE: No derivation scenario matched your target Bitcoin address.\n\n")
                
                f.write("CONFIGURATION TESTED:\n")
                f.write(f"Target Bitcoin Address: {self.eligible_bitcoin_address}\n")
                f.write(f"Address Type: {self.bitcoin_address_type}\n")
                f.write(f"Expected Account: {self.bitcoin_account}\n")
                f.write(f"Expected Index: {self.bitcoin_address_index}\n")
                f.write(f"Passphrase Length: {len(self.passphrase)} characters\n\n")
                
                f.write("WHAT WE TESTED:\n")
                f.write("- Accounts 0-4 for address derivation\n")
                f.write("- Address indices 0-19 within each account\n")
                f.write("- 6 different passphrase scenarios\n")
                f.write("- Multiple Unicode normalizations\n\n")
                
                f.write("ROOT CAUSE ANALYSIS:\n")
                f.write("Since no derivation scenario matched, this indicates:\n\n")
                f.write("1. SEED PHRASE MISMATCH (Most Likely)\n")
                f.write("   - Your .env seed doesn't match your Trezor seed\n")
                f.write("   - Word order might be wrong\n")
                f.write("   - One or more words might be misspelled\n\n")
                
                f.write("2. PASSPHRASE ENCODING ISSUE\n")
                f.write("   - Trezor might encode special characters differently\n")
                f.write("   - Hidden Unicode characters in passphrase\n\n")
                
                f.write("3. ADDRESS DERIVATION ISSUE\n")
                f.write("   - Your Bitcoin address might be from different derivation\n")
                f.write("   - Possible non-standard derivation path\n\n")
                
                f.write("IMMEDIATE ACTION PLAN:\n")
                f.write("1. Verify seed phrase against your Trezor\n")
                f.write("2. Test with empty passphrase (many users think they have one)\n")
                f.write("3. Double-check address from Midnight Portal\n")
                f.write("4. Contact Midnight support for alternatives\n")
            
            logger.info(f"Comprehensive diagnostic saved: {diag_file}")
        except Exception as e:
            logger.error(f"Failed to write diagnostic file: {e}")

    def run_claim_test(self):
        """
        Main method to run the Bitcoin claim test
        """
        logger.info("Starting comprehensive Bitcoin Midnight claim test...")
        logger.info("This will test multiple scenarios to find the exact derivation...")
        logger.info("Generating keys for Phantom Wallet import only...")
        
        # First, do a quick verification check
        if not self._quick_verification_check():
            return False
        
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
                logger.info(f"Hex Format: {Path(key_result['hex_file']).name}")
                logger.info(f"WIF Format: {Path(key_result['wif_file']).name}")
                logger.info(f"Instructions: {Path(key_result['instructions_file']).name}")
                
                print(f"\nSUCCESS! Bitcoin private key extracted!")
                print(f"Saved to: {self.workspace}")
                print(f"Ready for Phantom Wallet import!")
                print(f"Start with HEX format: {Path(key_result['hex_file']).name}")
                
                return True
            else:
                logger.error("Private key extraction failed")
                return False
        else:
            logger.error("Comprehensive derivation test failed!")
            logger.info("\nROOT CAUSE ANALYSIS:")
            logger.info("Since we tested multiple accounts, indices, and passphrases...")
            logger.info("The issue is most likely:")
            logger.info("1. SEED PHRASE MISMATCH - Your .env seed doesn't match your Trezor")
            logger.info("2. ADDRESS MISMATCH - Your eligible address is from a different wallet")
            logger.info("3. DERIVATION ISSUE - Needs different derivation method")
            
            # Create comprehensive diagnostic file
            self._create_diagnostic_file()
            return False

def main():
    print("Midnight Bitcoin Claim - PHANTOM WALLET ONLY")
    print("=" * 80)
    print("Testing multiple accounts, passphrase scenarios, and derivation methods")
    print("Extracting Bitcoin private keys for Phantom Wallet import")
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
            return True
        else:
            print("\nBitcoin claim test failed")
            print(f"Check diagnostic file in: {claimer.workspace}")
            return False
            
    except Exception as e:
        logger.error(f"Bitcoin claim test error: {e}")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    main()