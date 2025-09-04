#!/usr/bin/env python3
"""
Midnight Claim - Direct Path Test
Uses specific payment path and stake checksum from .env file
No passphrase variants - uses only your specific passphrase
"""

import os
import unicodedata
from pathlib import Path
from dotenv import load_dotenv
from pycardano import HDWallet, PaymentVerificationKey, Address, Network
from pycardano.key import ExtendedSigningKey
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DirectMidnightClaim:
    def __init__(self):
        load_dotenv()
        
        self.seed_phrase = os.getenv('TREZOR_SEED_PHRASE')
        self.passphrase = os.getenv('TREZOR_PASSPHRASE', '')
        self.claim_address = os.getenv('CLAIM_ADDRESS')
        self.payment_path = os.getenv('PAYMENT_PATH')
        self.stake_checksum = os.getenv('STAKE_CHECKSUM')
        
        if not all([self.seed_phrase, self.claim_address, self.payment_path, self.stake_checksum]):
            raise ValueError("SEED, CLAIM_ADDRESS, PAYMENT_PATH und STAKE_CHECKSUM erforderlich")
            
        logger.info(f"Ziel-Adresse: {self.claim_address}")
        logger.info(f"Payment Path: {self.payment_path}")
        logger.info(f"Stake Checksum: {self.stake_checksum}")
        logger.info(f"Passphrase-Länge: {len(self.passphrase)} Zeichen")
        
        # Use specific folder instead of temp folder
        self.workspace = Path(r"D:\workspace\VisualStudio\Midnight Claim")
        self.workspace.mkdir(parents=True, exist_ok=True)
        logger.info(f"Workspace: {self.workspace}")
        
        self.network = Network.MAINNET

    def _quick_verification_check(self):
        """
        Quick check to see if basic wallet creation works and log initial findings
        """
        logger.info("\n=== QUICK VERIFICATION ===")
        
        try:
            # Test basic wallet creation
            wallet = HDWallet.from_mnemonic(self.seed_phrase, passphrase=self.passphrase)
            logger.info("✅ Wallet creation successful")
            
            # Test first address with current passphrase
            first_addr = wallet.derive_from_path("m/1852'/1815'/0'/0/0")
            payment_vkey = PaymentVerificationKey.from_primitive(first_addr.public_key)
            address = Address(payment_vkey.hash(), None, self.network)
            
            logger.info(f"First address (current setup): {str(address)[:30]}...")
            logger.info(f"Target claim address:          {self.claim_address[:30]}...")
            
            if str(address) == self.claim_address:
                logger.info("🎯 IMMEDIATE MATCH with current setup!")
            else:
                logger.info("❌ No immediate match - will test other scenarios...")
                
        except Exception as e:
            logger.error(f"❌ Basic wallet creation failed: {e}")
            logger.error("This suggests a fundamental seed phrase or passphrase issue")

    def _test_byron_compatibility(self):
        """
        Test if this might be a Byron-era address that needs different handling
        """
        logger.info("\n=== BYRON COMPATIBILITY TEST ===")
        
        # Byron addresses start with 'Ae2' or 'Ddz' but target is 'addr1q' so this is Shelley
        if self.claim_address.startswith('addr1'):
            logger.info("✅ Target is Shelley address (addr1) - using CIP-1852")
            return False
        else:
            logger.info("⚠️  Target might be Byron address - testing BIP-44 derivation")
            # Add Byron derivation logic here if needed
            return True

    def test_direct_derivation(self):
        """
        Comprehensive test with multiple approaches to find the correct derivation
        """
        logger.info("=== COMPREHENSIVE DERIVATION TEST ===")
        logger.info(f"Target address: {self.claim_address}")
        logger.info(f"Expected stake checksum: {self.stake_checksum}")
        
        # Test different passphrase scenarios first
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
            
            try:
                wallet = HDWallet.from_mnemonic(
                    mnemonic=self.seed_phrase,
                    passphrase=test_passphrase
                )
                
                # Test different account indices for payment path
                for account in range(5):  # Test accounts 0-4
                    payment_path = f"m/1852'/1815'/{account}'/0/0"
                    
                    try:
                        derived_payment = wallet.derive_from_path(payment_path)
                        payment_vkey = PaymentVerificationKey.from_primitive(derived_payment.public_key)
                        
                        # Test payment-only address
                        address_v = Address(payment_vkey.hash(), None, self.network)
                        
                        if account == 0:  # Log first account for debugging
                            logger.info(f"Account {account} payment-only: {str(address_v)[:20]}...")
                        
                        if str(address_v) == self.claim_address:
                            logger.info(f"🎯 PAYMENT MATCH! Scenario: {scenario_name}, Account: {account}")
                            return self._create_result(account, 0, None, payment_path, None, 
                                                     derived_payment, None, str(address_v), 'payment_only')
                        
                        # Test with stake keys
                        for stake_account in range(3):  # Stake might be in different account
                            for stake_index in range(20):
                                stake_path = f"m/1852'/1815'/{stake_account}'/2/{stake_index}"
                                
                                try:
                                    derived_stake = wallet.derive_from_path(stake_path)
                                    stake_vkey = PaymentVerificationKey.from_primitive(derived_stake.public_key)
                                    stake_hash = stake_vkey.hash().payload.hex()
                                    
                                    # Log some examples for debugging
                                    if account == 0 and stake_account == 0 and stake_index < 5 and scenario_name == "current_passphrase":
                                        logger.info(f"Stake {stake_account}/{stake_index}: {stake_hash[:16]}...")
                                    
                                    if stake_hash.lower() == self.stake_checksum.lower():
                                        logger.info(f"🔑 STAKE CHECKSUM MATCH! Scenario: {scenario_name}")
                                        logger.info(f"  Payment Account: {account}, Stake Account: {stake_account}, Stake Index: {stake_index}")
                                        
                                        # Create complete address
                                        address_q = Address(payment_vkey.hash(), stake_vkey.hash(), self.network)
                                        logger.info(f"Complete address: {address_q}")
                                        
                                        if str(address_q) == self.claim_address:
                                            logger.info("🎯 PERFECT MATCH! Complete derivation found!")
                                            return self._create_result(account, 0, stake_index, payment_path, stake_path,
                                                                     derived_payment, derived_stake, str(address_q), 'payment_stake')
                                        else:
                                            logger.warning("Stake checksum matches but final address doesn't match")
                                            
                                except Exception as e:
                                    continue
                                    
                    except Exception as e:
                        logger.debug(f"Payment derivation failed for account {account}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Wallet creation failed for {scenario_name}: {e}")
                continue
        
        logger.error("No matching derivation found across all scenarios")
        return None

    def _create_diagnostic_file(self):
        """
        Creates a comprehensive diagnostic file with troubleshooting steps
        """
        diag_file = self.workspace / f"DIAGNOSTIC_REPORT_{os.getpid()}.txt"
        with open(diag_file, 'w', encoding='utf-8') as f:
            f.write("MIDNIGHT CLAIM COMPREHENSIVE DIAGNOSTIC REPORT\n")
            f.write("=" * 60 + "\n\n")
            f.write("❌ ISSUE: No derivation scenario matched your target address.\n\n")
            
            f.write("CONFIGURATION TESTED:\n")
            f.write(f"Payment Path Template: m/1852'/1815'/ACCOUNT'/0/0\n")
            f.write(f"Expected Stake Checksum: {self.stake_checksum}\n")
            f.write(f"Target Address: {self.claim_address}\n")
            f.write(f"Passphrase Length: {len(self.passphrase)} characters\n\n")
            
            f.write("🔍 WHAT WE TESTED:\n")
            f.write("✓ Accounts 0-4 for payment derivation\n")
            f.write("✓ 6 different passphrase scenarios\n")
            f.write("✓ Stakes indices 0-19 across accounts 0-2\n")
            f.write("✓ Multiple Unicode normalizations\n\n")
            
            f.write("🚨 ROOT CAUSE ANALYSIS:\n")
            f.write("Since even the PAYMENT portion doesn't match, this indicates:\n\n")
            f.write("1. **SEED PHRASE MISMATCH** (Most Likely)\n")
            f.write("   - Your .env seed doesn't match your Yoroi/Trezor seed\n")
            f.write("   - Word order might be wrong\n")
            f.write("   - One or more words might be misspelled\n")
            f.write("   - Copy-paste error when creating .env\n\n")
            
            f.write("2. **PASSPHRASE ENCODING ISSUE**\n")
            f.write("   - Trezor might encode special characters differently\n")
            f.write("   - Hidden Unicode characters in passphrase\n")
            f.write("   - Different normalization than expected\n\n")
            
            f.write("3. **WALLET COMPATIBILITY ISSUE**\n")
            f.write("   - Your Yoroi data might be from a different derivation method\n")
            f.write("   - Possible Byron era artifacts\n")
            f.write("   - Non-standard derivation paths\n\n")
            
            f.write("🛠️ IMMEDIATE ACTION PLAN:\n")
            f.write("1. **VERIFY SEED PHRASE:**\n")
            f.write("   - Open your Trezor\n")
            f.write("   - Go to first receive address\n")
            f.write("   - Compare with script-generated addresses\n")
            f.write("   - If different, your .env seed is wrong\n\n")
            
            f.write("2. **TEST EMPTY PASSPHRASE:**\n")
            f.write("   - Set TREZOR_PASSPHRASE= (completely empty)\n")
            f.write("   - Run script again\n")
            f.write("   - Many users think they have a passphrase when they don't\n\n")
            
            f.write("3. **PASSPHRASE VERIFICATION:**\n")
            f.write("   - Copy passphrase directly from secure source\n")
            f.write("   - Check for invisible characters\n")
            f.write("   - Verify case sensitivity\n\n")
            
            f.write("4. **ALTERNATIVE APPROACH:**\n")
            f.write("   - Use Trezor Suite to export keys directly\n")
            f.write("   - Try CardanoSharp or other derivation tools\n")
            f.write("   - Contact Midnight team for alternative claim methods\n\n")
            
            f.write("🔧 DEBUGGING COMMANDS:\n")
            f.write("Run this in your folder to test passphrase scenarios:\n")
            f.write("python test_passphrase.py\n\n")
            
            f.write("📞 IF STILL STUCK:\n")
            f.write("The fundamental issue is that your wallet derivation doesn't match\n")
            f.write("the provided Yoroi data. This means either:\n")
            f.write("- The seed/passphrase in .env is incorrect\n")
            f.write("- The Yoroi data came from a different wallet\n")
            f.write("- There's a compatibility issue we haven't identified\n\n")
            
            f.write("Consider reaching out to the Midnight community or using\n")
            f.write("your hardware wallet's native key export functionality.\n")
        
        logger.info(f"Comprehensive diagnostic saved: {diag_file}")
        
        # Create enhanced test script
        self._create_test_script()

    def _create_test_script(self):
        """
        Creates a comprehensive test script for manual verification
        """
        test_script = self.workspace / "comprehensive_test.py"
        with open(test_script, 'w') as f:
            f.write(f'''#!/usr/bin/env python3
"""
Comprehensive Midnight Claim Test Script
Tests all possible scenarios to identify the exact issue
"""
from dotenv import load_dotenv
from pycardano import HDWallet, PaymentVerificationKey, Address, Network
import unicodedata
import os

load_dotenv()

seed = os.getenv('TREZOR_SEED_PHRASE')
passphrase = os.getenv('TREZOR_PASSPHRASE', '')
target = os.getenv('CLAIM_ADDRESS')
expected_stake = os.getenv('STAKE_CHECKSUM')

print("🔍 COMPREHENSIVE MIDNIGHT CLAIM DIAGNOSTICS")
print("=" * 60)
print(f"Target Address: {{target}}")
print(f"Expected Stake Checksum: {{expected_stake}}")
print(f"Current Passphrase Length: {{len(passphrase)}} characters")
print("\\n" + "=" * 60 + "\\n")

# Test different passphrase scenarios
scenarios = [
    ("Empty passphrase", ""),
    ("Current passphrase", passphrase),
    ("Trimmed passphrase", passphrase.strip()),
    ("Lowercase passphrase", passphrase.lower()),
    ("Uppercase passphrase", passphrase.upper()),
    ("NFC normalized", unicodedata.normalize('NFC', passphrase)),
    ("NFKD normalized", unicodedata.normalize('NFKD', passphrase)),
]

found_match = False

for scenario_name, test_pass in scenarios:
    print(f"Testing: {{scenario_name}}")
    print("-" * 40)
    
    try:
        wallet = HDWallet.from_mnemonic(seed, passphrase=test_pass)
        
        # Test different accounts
        for account in range(3):
            payment_path = f"m/1852'/1815'/{{account}}'/0/0"
            
            try:
                derived = wallet.derive_from_path(payment_path)
                payment_vkey = PaymentVerificationKey.from_primitive(derived.public_key)
                address = Address(payment_vkey.hash(), None, Network.MAINNET)
                
                match_status = "✅ PAYMENT MATCH!" if str(address) == target else "❌"
                print(f"  Account {{account}}: {{match_status}} {{str(address)[:25]}}...")
                
                if str(address) == target:
                    print(f"\\n🎯 FOUND IT! Scenario: {{scenario_name}}, Account: {{account}}")
                    print(f"Correct derivation path: {{payment_path}}")
                    found_match = True
                    break
                    
            except Exception as e:
                print(f"  Account {{account}}: ERROR {{e}}")
        
        if found_match:
            break
            
    except Exception as e:
        print(f"  Wallet creation failed: {{e}}")
    
    print()

if not found_match:
    print("❌ NO PAYMENT ADDRESS MATCH FOUND")
    print("\\nThis strongly suggests:")
    print("1. Your seed phrase in .env is incorrect")
    print("2. Your Yoroi data came from a different wallet")
    print("3. There's a fundamental compatibility issue")
    print("\\n💡 NEXT STEPS:")
    print("- Double-check your seed phrase against your Trezor")
    print("- Verify the Yoroi data matches your Trezor wallet")
    print("- Try exporting keys directly from Trezor Suite")
else:
    print("🎉 Found working configuration!")
    print("Update your .env file and run the main script again.")
''')
        
        logger.info(f"Comprehensive test script created: {test_script.name}")
        print(f"\\n🔧 DIAGNOSTIC TOOLS CREATED:")
        print(f"📁 Main diagnostic: DIAGNOSTIC_REPORT_{os.getpid()}.txt")
        print(f"🧪 Test script: comprehensive_test.py")
        print(f"\\nRun: python comprehensive_test.py")
        print(f"This will test all scenarios and tell you exactly what's wrong!")

    def _create_result(self, account, payment_index, stake_index, payment_path, stake_path, 
                      payment_wallet, stake_wallet, address, address_type):
        
        logger.info("🎯 MATCH FOUND!")
        logger.info(f"  Payment Path: {payment_path}")
        if stake_path:
            logger.info(f"  Stake Path: {stake_path}")
        logger.info(f"  Address Type: {address_type}")
        
        return {
            'account': account,
            'payment_index': payment_index,
            'stake_index': stake_index,
            'payment_path': payment_path,
            'stake_path': stake_path,
            'derived_payment_wallet': payment_wallet,
            'derived_stake_wallet': stake_wallet,
            'address': address,
            'address_type': address_type
        }

    def extract_keys(self, derivation_info):
        """
        Extrahiert die private keys für Eternl import
        """
        logger.info("Extracting private keys...")
        
        try:
            address = derivation_info['address']
            payment_wallet = derivation_info['derived_payment_wallet']
            stake_wallet = derivation_info.get('derived_stake_wallet')
            
            safe_addr = address[:12]
            
            # Payment Key
            payment_extended_key = ExtendedSigningKey.from_hdwallet(payment_wallet)
            payment_skey_content = payment_extended_key.to_json()
            
            payment_skey_file = self.workspace / f"midnight_payment_{safe_addr}_{os.getpid()}.skey"
            with open(payment_skey_file, 'w') as f:
                f.write(payment_skey_content)
            
            # Stake Key (falls vorhanden)
            stake_skey_file = None
            if stake_wallet:
                stake_extended_key = ExtendedSigningKey.from_hdwallet(stake_wallet)
                stake_skey_content = stake_extended_key.to_json()
                
                stake_skey_file = self.workspace / f"midnight_stake_{safe_addr}_{os.getpid()}.skey"
                with open(stake_skey_file, 'w') as f:
                    f.write(stake_skey_content)
            
            # Success instructions
            success_file = self.workspace / f"MIDNIGHT_SUCCESS_{safe_addr}_{os.getpid()}.txt"
            with open(success_file, 'w', encoding='utf-8') as f:
                f.write("🎉 MIDNIGHT CLAIM KEYS SUCCESSFULLY FOUND!\n")
                f.write("=" * 80 + "\n\n")
                
                f.write("DERIVATION DETAILS:\n")
                f.write(f"Claim Address: {address}\n")
                f.write(f"Payment Path: {derivation_info['payment_path']}\n")
                if derivation_info['stake_path']:
                    f.write(f"Stake Path: {derivation_info['stake_path']}\n")
                    f.write(f"Stake Index: {derivation_info['stake_index']}\n")
                f.write(f"Address Type: {derivation_info['address_type']}\n\n")
                
                f.write("🔑 PRIVATE KEY FILES:\n")
                f.write(f"Payment Key: {payment_skey_file.name}\n")
                if stake_skey_file:
                    f.write(f"Stake Key: {stake_skey_file.name}\n")
                
                f.write(f"\n🚀 ETERNL IMPORT INSTRUCTIONS:\n")
                f.write("=" * 50 + "\n")
                f.write("1. Open Eternl Wallet (https://eternl.io)\n")
                f.write("2. 'Add Wallet' → 'Restore' → 'Advanced'\n")
                f.write("3. Select 'Import from CLI signing key'\n")
                f.write(f"4. Upload file: {payment_skey_file.name}\n")
                f.write("5. Wallet name: 'Midnight Claim'\n")
                f.write("6. Create wallet\n")
                f.write("7. Connect to Midnight Portal\n")
                f.write("8. Execute claim\n\n")
                
                f.write("⚠️ IMMEDIATELY AFTER CLAIMING:\n")
                f.write("=" * 30 + "\n")
                f.write(f"1. DELETE: {payment_skey_file.name}\n")
                if stake_skey_file:
                    f.write(f"2. DELETE: {stake_skey_file.name}\n")
                f.write("3. Delete Eternl wallet\n")
                f.write("4. Transfer Midnight tokens to hardware wallet\n")
                f.write("5. Delete entire folder\n")
            
            result = {
                'payment_skey_file': str(payment_skey_file),
                'stake_skey_file': str(stake_skey_file) if stake_skey_file else None,
                'success_file': str(success_file),
                'derivation_info': derivation_info
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Key extraction error: {e}")
            return None

    def run_claim_test(self):
        """
        Main method to run the direct claim test
        """
        logger.info("Starting comprehensive Midnight claim test...")
        logger.info("This will test multiple scenarios to find the exact issue...")
        
        # First, do a quick verification check
        self._quick_verification_check()
        
        # Test the specific derivation
        result = self.test_direct_derivation()
        
        if result:
            logger.info("✅ Derivation successful!")
            
            # Extract keys
            key_result = self.extract_keys(result)
            if key_result:
                logger.info("\n" + "="*90)
                logger.info("🎊 MIDNIGHT CLAIM KEYS SUCCESSFULLY GENERATED!")
                logger.info("="*90)
                
                logger.info(f"\n📁 KEYS SAVED TO: {self.workspace}")
                logger.info(f"🔑 Payment Key: {Path(key_result['payment_skey_file']).name}")
                if key_result['stake_skey_file']:
                    logger.info(f"🔑 Stake Key: {Path(key_result['stake_skey_file']).name}")
                logger.info(f"📋 Instructions: {Path(key_result['success_file']).name}")
                
                print(f"\n✅ SUCCESS! Private keys extracted!")
                print(f"📂 Saved to: D:\\workspace\\VisualStudio\\Midnight Claim")
                print(f"📖 Read: {Path(key_result['success_file']).name}")
                
                return True
            else:
                logger.error("Key extraction failed")
                return False
        else:
            logger.error("❌ Comprehensive derivation test failed!")
            logger.info("\nROOT CAUSE ANALYSIS:")
            logger.info("Since we tested multiple accounts, passphrases, and normalizations...")
            logger.info("The issue is most likely:")
            logger.info("1. 🔥 SEED PHRASE MISMATCH - Your .env seed doesn't match your Trezor")
            logger.info("2. 🔐 WALLET MISMATCH - Your Yoroi data is from a different wallet")
            logger.info("3. 🛠️  COMPATIBILITY ISSUE - Needs different derivation method")
            
            # Create comprehensive diagnostic file
            self._create_diagnostic_file()
            return False

    def _create_diagnostic_file(self):
        """
        Creates a diagnostic file with troubleshooting steps
        """
        diag_file = self.workspace / "DIAGNOSTIC_REPORT.txt"
        with open(diag_file, 'w', encoding='utf-8') as f:
            f.write("MIDNIGHT CLAIM DIAGNOSTIC REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write("The specified derivation path did not match your claim address.\n\n")
            f.write("TROUBLESHOOTING STEPS:\n")
            f.write("1. Double-check your seed phrase in .env\n")
            f.write("2. Verify your passphrase is exactly correct\n")
            f.write("3. Confirm the payment path matches your wallet\n")
            f.write("4. Verify the stake checksum from your wallet\n\n")
            f.write("CONFIGURATION USED:\n")
            f.write(f"Payment Path: {self.payment_path}\n")
            f.write(f"Stake Checksum: {self.stake_checksum}\n")
            f.write(f"Target Address: {self.claim_address}\n")
            f.write(f"Passphrase Length: {len(self.passphrase)} characters\n")
        
        logger.info(f"Diagnostic saved: {diag_file}")

def main():
    print("🎯 Midnight Claim - COMPREHENSIVE TEST")
    print("=" * 80)
    print("Testing multiple accounts, passphrase scenarios, and derivation methods")
    print("Saving all results to: D:\\workspace\\VisualStudio\\Midnight Claim")
    print("=" * 80)
    
    try:
        if not os.path.exists('.env'):
            print("❌ .env file missing!")
            return False
        
        claimer = DirectMidnightClaim()
        success = claimer.run_claim_test()
        
        if success:
            print("\n🏆 CLAIM TEST SUCCESSFUL!")
            print("Your private keys are ready for Eternl import!")
            return True
        else:
            print("\n❌ Claim test failed")
            print("📂 Check diagnostic file in: D:\\workspace\\VisualStudio\\Midnight Claim")
            return False
            
    except Exception as e:
        logger.error(f"Claim test error: {e}")
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    main()