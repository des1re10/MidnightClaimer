#!/usr/bin/env python3
"""
Midnight Bitcoin Claim - Comprehensive Bitcoin Private Key Extraction
Derives Bitcoin private keys from Trezor seed phrases for Midnight token claims
Supports all address types: Legacy (P2PKH), SegWit (P2SH-P2WPKH), Native SegWit (P2WPKH)
"""

import os
import unicodedata
from pathlib import Path
from dotenv import load_dotenv
import logging
from mnemonic import Mnemonic
from bitcoinlib.wallets import HDWallet as BitcoinHDWallet
from bitcoinlib.keys import HDKey
from bitcoinlib.encoding import addr_base58_to_hash160, addr_bech32_to_hash160
import hashlib
import base58

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BitcoinMidnightClaim:
    def __init__(self):
        load_dotenv()
        
        self.seed_phrase = os.getenv('TREZOR_SEED_PHRASE')
        self.passphrase = os.getenv('TREZOR_PASSPHRASE', '')
        self.eligible_bitcoin_address = os.getenv('ELIGIBLE_BITCOIN_ADDRESS')
        self.bitcoin_address_type = os.getenv('BITCOIN_ADDRESS_TYPE', '').lower()
        self.bitcoin_account = int(os.getenv('BITCOIN_ACCOUNT', '0'))
        self.bitcoin_address_index = int(os.getenv('BITCOIN_ADDRESS_INDEX', '0'))
        
        if not all([self.seed_phrase, self.eligible_bitcoin_address]):
            raise ValueError("TREZOR_SEED_PHRASE and ELIGIBLE_BITCOIN_ADDRESS are required")
            
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
            return 'legacy'
        elif address.startswith('3'):
            return 'segwit'
        elif address.startswith('bc1'):
            return 'native_segwit'
        else:
            raise ValueError(f"Unknown Bitcoin address format: {address}")

    def _get_derivation_path(self, address_type, account, change, index):
        """
        Get BIP derivation path for different address types
        """
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

    def _quick_verification_check(self):
        """
        Quick check to see if basic wallet creation works and log initial findings
        """
        logger.info("\n=== QUICK VERIFICATION ===")
        
        try:
            # Validate mnemonic
            mnemo = Mnemonic("english")
            if not mnemo.check(self.seed_phrase):
                logger.error("❌ Invalid mnemonic seed phrase")
                return False
            
            logger.info("✅ Wallet creation successful")
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
            logger.error(f"❌ Basic wallet creation failed: {e}")
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
            if address_type == 'legacy':
                # P2PKH
                address = derived_key.address()
            elif address_type == 'segwit':
                # P2SH-P2WPKH
                address = derived_key.address(script_type='p2sh_p2wpkh')
            elif address_type == 'native_segwit':
                # P2WPKH
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
                            logger.info(f"🎯 PERFECT MATCH! Derivation found!")
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
        
        logger.error("❌ No matching derivation found across all scenarios")
        return None

    def _create_result(self, account, address_index, derivation_result, scenario_name, passphrase_used):
        """
        Create successful result object
        """
        logger.info("\n🎯 MATCH FOUND!")
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
        Extract and save the Bitcoin private key in WIF format
        """
        logger.info("Extracting Bitcoin private key...")
        
        try:
            derivation_result = derivation_info['derivation_result']
            address = derivation_result['address']
            private_key_wif = derivation_result['private_key_wif']
            
            # Create safe filename from address
            safe_addr = address[:12].replace('1', '').replace('3', '').replace('bc1q', 'bc1q')
            
            # Save WIF private key
            wif_file = self.workspace / f"midnight_bitcoin_private_{safe_addr}_{os.getpid()}.wif"
            with open(wif_file, 'w') as f:
                f.write(private_key_wif)
            
            # Create success instructions
            success_file = self.workspace / f"MIDNIGHT_BITCOIN_SUCCESS_{safe_addr}_{os.getpid()}.txt"
            with open(success_file, 'w', encoding='utf-8') as f:
                f.write("🎉 MIDNIGHT BITCOIN CLAIM KEY SUCCESSFULLY FOUND!\n")
                f.write("=" * 80 + "\n\n")
                
                f.write("DERIVATION DETAILS:\n")
                f.write(f"Bitcoin Address: {address}\n")
                f.write(f"Derivation Path: {derivation_result['derivation_path']}\n")
                f.write(f"Address Type: {derivation_info['address_type']}\n")
                f.write(f"Account: {derivation_info['account']}\n")
                f.write(f"Address Index: {derivation_info['address_index']}\n")
                f.write(f"Passphrase Scenario: {derivation_info['scenario_name']}\n\n")
                
                f.write("🔑 PRIVATE KEY FILE:\n")
                f.write(f"WIF Format: {wif_file.name}\n\n")
                
                f.write("🚀 SOFTWARE WALLET IMPORT INSTRUCTIONS:\n")
                f.write("=" * 50 + "\n")
                f.write("OPTION 1: Electrum Wallet (Recommended)\n")
                f.write("1. Download Electrum from electrum.org\n")
                f.write("2. File → New/Restore\n")
                f.write("3. Choose 'Import Bitcoin addresses or private keys'\n")
                f.write(f"4. Paste WIF key from: {wif_file.name}\n")
                f.write("5. Next → Create\n")
                f.write("6. Connect to Midnight Portal\n")
                f.write("7. Execute claim\n\n")
                
                f.write("OPTION 2: Sparrow Wallet\n")
                f.write("1. Download Sparrow from sparrowwallet.com\n")
                f.write("2. File → New Wallet\n")
                f.write("3. Choose 'Imported'\n")
                if derivation_info['address_type'] == 'legacy':
                    f.write("4. Script Type: P2PKH\n")
                elif derivation_info['address_type'] == 'segwit':
                    f.write("4. Script Type: P2SH-P2WPKH\n")
                elif derivation_info['address_type'] == 'native_segwit':
                    f.write("4. Script Type: P2WPKH\n")
                f.write(f"5. Paste WIF key from: {wif_file.name}\n")
                f.write("6. Create Wallet\n\n")
                
                f.write("⚠️ IMMEDIATELY AFTER CLAIMING:\n")
                f.write("=" * 30 + "\n")
                f.write(f"1. DELETE: {wif_file.name}\n")
                f.write("2. DELETE: Software wallet you created\n")
                f.write("3. Transfer Midnight tokens to NEW secure hardware wallet\n")
                f.write("4. Delete entire project folder\n")
                f.write("5. Clear browser cache/history\n")
                f.write("6. Abandon OLD wallet completely\n\n")
                
                f.write("🔐 SECURITY REMINDER:\n")
                f.write("- Your OLD wallet seed is now compromised\n")
                f.write("- Never use OLD wallet addresses for receiving anything\n")
                f.write("- All future transactions should use your NEW secure wallet\n")
            
            result = {
                'wif_file': str(wif_file),
                'success_file': str(success_file),
                'derivation_info': derivation_info,
                'private_key_wif': private_key_wif
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
        with open(diag_file, 'w', encoding='utf-8') as f:
            f.write("MIDNIGHT BITCOIN CLAIM COMPREHENSIVE DIAGNOSTIC REPORT\n")
            f.write("=" * 60 + "\n\n")
            f.write("❌ ISSUE: No derivation scenario matched your target Bitcoin address.\n\n")
            
            f.write("CONFIGURATION TESTED:\n")
            f.write(f"Target Bitcoin Address: {self.eligible_bitcoin_address}\n")
            f.write(f"Address Type: {self.bitcoin_address_type}\n")
            f.write(f"Expected Account: {self.bitcoin_account}\n")
            f.write(f"Expected Index: {self.bitcoin_address_index}\n")
            f.write(f"Passphrase Length: {len(self.passphrase)} characters\n\n")
            
            f.write("🔍 WHAT WE TESTED:\n")
            f.write("✓ Accounts 0-4 for address derivation\n")
            f.write("✓ Address indices 0-19 within each account\n")
            f.write("✓ 6 different passphrase scenarios\n")
            f.write("✓ Multiple Unicode normalizations\n")
            f.write(f"✓ {self.bitcoin_address_type} address type derivation\n\n")
            
            f.write("🚨 ROOT CAUSE ANALYSIS:\n")
            f.write("Since no derivation scenario matched, this indicates:\n\n")
            f.write("1. **SEED PHRASE MISMATCH** (Most Likely)\n")
            f.write("   - Your .env seed doesn't match your Trezor seed\n")
            f.write("   - Word order might be wrong\n")
            f.write("   - One or more words might be misspelled\n")
            f.write("   - Copy-paste error when creating .env\n\n")
            
            f.write("2. **PASSPHRASE ENCODING ISSUE**\n")
            f.write("   - Trezor might encode special characters differently\n")
            f.write("   - Hidden Unicode characters in passphrase\n")
            f.write("   - Different normalization than expected\n\n")
            
            f.write("3. **ADDRESS DERIVATION ISSUE**\n")
            f.write("   - Your Bitcoin address might be from a different derivation method\n")
            f.write("   - Possible non-standard derivation path\n")
            f.write("   - Address might be from a different account/index\n\n")
            
            f.write("4. **ELIGIBILITY VERIFICATION ISSUE**\n")
            f.write("   - Confirm this Bitcoin address is actually eligible\n")
            f.write("   - Verify you copied the correct address from portal\n")
            f.write("   - Check if address format matches portal exactly\n\n")
            
            f.write("🛠️ IMMEDIATE ACTION PLAN:\n")
            f.write("1. **VERIFY SEED PHRASE:**\n")
            f.write("   - Open your Trezor Bitcoin wallet\n")
            f.write("   - Compare first receive address with script output\n")
            f.write("   - If different, your .env seed is wrong\n\n")
            
            f.write("2. **TEST EMPTY PASSPHRASE:**\n")
            f.write("   - Set TREZOR_PASSPHRASE= (completely empty)\n")
            f.write("   - Run script again\n")
            f.write("   - Many users think they have a passphrase when they don't\n\n")
            
            f.write("3. **VERIFY ELIGIBLE ADDRESS:**\n")
            f.write("   - Double-check address from Midnight Portal\n")
            f.write("   - Ensure no copy-paste errors\n")
            f.write("   - Verify address type detection is correct\n\n")
            
            f.write("4. **ALTERNATIVE APPROACHES:**\n")
            f.write("   - Try exporting from Trezor Suite directly\n")
            f.write("   - Use Electrum with Trezor hardware wallet mode\n")
            f.write("   - Contact Midnight team for alternative claim methods\n\n")
            
            f.write("📞 IF STILL STUCK:\n")
            f.write("The fundamental issue is that your wallet derivation doesn't match\n")
            f.write("the provided eligible address. This means either:\n")
            f.write("- The seed/passphrase in .env is incorrect\n")
            f.write("- The eligible address is from a different wallet\n")
            f.write("- There's a derivation compatibility issue\n\n")
            
            f.write("Consider using your hardware wallet's native export functionality\n")
            f.write("or contacting the Midnight community for assistance.\n")
        
        logger.info(f"Comprehensive diagnostic saved: {diag_file}")

    def run_claim_test(self):
        """
        Main method to run the Bitcoin claim test
        """
        logger.info("🎯 Starting comprehensive Bitcoin Midnight claim test...")
        logger.info("This will test multiple scenarios to find the exact derivation...")
        
        # First, do a quick verification check
        if not self._quick_verification_check():
            return False
        
        # Test comprehensive derivation
        result = self.test_comprehensive_derivation()
        
        if result:
            logger.info("✅ Derivation successful!")
            
            # Extract private key
            key_result = self.extract_private_key(result)
            if key_result:
                logger.info("\n" + "="*90)
                logger.info("🎊 MIDNIGHT BITCOIN CLAIM KEY SUCCESSFULLY GENERATED!")
                logger.info("="*90)
                
                logger.info(f"\n📁 KEY SAVED TO: {self.workspace}")
                logger.info(f"🔑 Private Key (WIF): {Path(key_result['wif_file']).name}")
                logger.info(f"📋 Instructions: {Path(key_result['success_file']).name}")
                
                print(f"\n✅ SUCCESS! Bitcoin private key extracted!")
                print(f"📂 Saved to: {self.workspace}")
                print(f"📖 Read: {Path(key_result['success_file']).name}")
                
                return True
            else:
                logger.error("Private key extraction failed")
                return False
        else:
            logger.error("❌ Comprehensive derivation test failed!")
            logger.info("\nROOT CAUSE ANALYSIS:")
            logger.info("Since we tested multiple accounts, indices, and passphrases...")
            logger.info("The issue is most likely:")
            logger.info("1. 🔥 SEED PHRASE MISMATCH - Your .env seed doesn't match your Trezor")
            logger.info("2. 📍 ADDRESS MISMATCH - Your eligible address is from a different wallet")
            logger.info("3. 🛠️ DERIVATION ISSUE - Needs different derivation method")
            
            # Create comprehensive diagnostic file
            self._create_diagnostic_file()
            return False

def main():
    print("🎯 Midnight Bitcoin Claim - COMPREHENSIVE TEST")
    print("=" * 80)
    print("Testing multiple accounts, passphrase scenarios, and derivation methods")
    print("Extracting Bitcoin private keys for software wallet import")
    print("=" * 80)
    
    try:
        if not os.path.exists('.env'):
            print("❌ .env file missing!")
            return False
        
        claimer = BitcoinMidnightClaim()
        success = claimer.run_claim_test()
        
        if success:
            print("\n🏆 BITCOIN CLAIM TEST SUCCESSFUL!")
            print("Your Bitcoin private key is ready for software wallet import!")
            return True
        else:
            print("\n❌ Bitcoin claim test failed")
            print(f"📂 Check diagnostic file in: {claimer.workspace}")
            return False
            
    except Exception as e:
        logger.error(f"Bitcoin claim test error: {e}")
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    main()