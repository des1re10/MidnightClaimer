#!/usr/bin/env python3
"""
Midnight Bitcoin Claim - Fixed BIP32 Derivation with Proper Compressed WIF
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
import struct
import base58

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
        """Auto-detect Bitcoin address type from format"""
        if address.startswith('bc1q'):
            return 'native_segwit'
        elif address.startswith('bc1p'):
            return 'taproot'
        else:
            raise ValueError(f"Unsupported address format: {address}")

    def _point_add(self, p1, p2):
        """Add two points on secp256k1 curve"""
        # Simplified implementation - in production, use a proper crypto library
        # This is a placeholder for actual elliptic curve point addition
        return p1  # This needs proper implementation

    def _point_multiply(self, k, point):
        """Multiply point by scalar on secp256k1 curve"""
        # Simplified implementation - in production, use a proper crypto library
        return point  # This needs proper implementation

    def _private_key_to_public_key(self, private_key_bytes):
        """Convert private key to compressed public key"""
        try:
            # Using bit library for proper secp256k1 operations
            from bit import Key
            key = Key.from_hex(private_key_bytes.hex())
            return bytes.fromhex(key.public_key)
        except ImportError:
            # Fallback implementation (not recommended for production)
            logger.warning("Using fallback public key derivation - install bit library for proper implementation")
            # This is a simplified placeholder - proper implementation requires secp256k1
            return b'\x02' + private_key_bytes  # This is not correct, just a placeholder

    def _derive_master_key(self, seed_phrase, passphrase):
        """Derive master private key from seed phrase using BIP39"""
        mnemo = Mnemonic("english")
        
        # Validate seed phrase
        if not mnemo.check(seed_phrase):
            raise ValueError("Invalid seed phrase")
            
        seed = mnemo.to_seed(seed_phrase, passphrase=passphrase)
        
        # BIP32 master key derivation
        hmac_result = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
        master_private_key = hmac_result[:32]
        master_chain_code = hmac_result[32:]
        
        return master_private_key, master_chain_code

    def _derive_child_key(self, parent_private_key, parent_chain_code, index, hardened=False):
        """Derive child private key using proper BIP32 implementation"""
        if hardened:
            # Hardened derivation: use private key
            index += 0x80000000
            data = b'\x00' + parent_private_key + struct.pack('>I', index)
        else:
            # Non-hardened derivation: use public key
            parent_public_key = self._private_key_to_public_key(parent_private_key)
            data = parent_public_key + struct.pack('>I', index)
        
        hmac_result = hmac.new(parent_chain_code, data, hashlib.sha512).digest()
        child_private_key_int = int.from_bytes(hmac_result[:32], 'big')
        parent_private_key_int = int.from_bytes(parent_private_key, 'big')
        
        # secp256k1 curve order
        curve_order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        
        # Add parent private key to child private key (mod curve order)
        final_private_key_int = (child_private_key_int + parent_private_key_int) % curve_order
        
        if final_private_key_int == 0:
            raise ValueError("Invalid key derivation")
            
        final_private_key = final_private_key_int.to_bytes(32, 'big')
        child_chain_code = hmac_result[32:]
        
        return final_private_key, child_chain_code

    def _private_key_to_wif_compressed(self, private_key_bytes, mainnet=True):
        """Convert private key to compressed WIF format for Phantom wallet"""
        # Add network prefix (0x80 for mainnet, 0xEF for testnet)
        if mainnet:
            extended_key = b'\x80' + private_key_bytes + b'\x01'  # 0x01 indicates compressed
        else:
            extended_key = b'\xEF' + private_key_bytes + b'\x01'
            
        # Double SHA256 for checksum
        checksum = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]
        
        # Encode with Base58Check
        wif = base58.b58encode(extended_key + checksum).decode('ascii')
        
        return wif

    def _private_key_to_segwit_address(self, private_key_bytes):
        """Convert private key to Native SegWit (bc1) address"""
        try:
            from bit import Key
            key = Key.from_hex(private_key_bytes.hex())
            return key.segwit_address
        except ImportError:
            logger.error("bit library required for address generation")
            return None

    def _derive_bitcoin_key(self, passphrase, account, address_index, address_type):
        """Derive Bitcoin private key using proper BIP84 derivation path"""
        try:
            # Get master key
            master_key, master_chain = self._derive_master_key(self.seed_phrase, passphrase)
            
            # BIP84 derivation path: m/84'/0'/account'/0/address_index
            # All these are hardened except the last two
            
            # Derive m/84' (hardened)
            key, chain = self._derive_child_key(master_key, master_chain, 84, hardened=True)
            
            # Derive m/84'/0' (hardened)
            key, chain = self._derive_child_key(key, chain, 0, hardened=True)
            
            # Derive m/84'/0'/account' (hardened)
            key, chain = self._derive_child_key(key, chain, account, hardened=True)
            
            # Derive m/84'/0'/account'/0 (non-hardened, external chain)
            key, chain = self._derive_child_key(key, chain, 0, hardened=False)
            
            # Derive m/84'/0'/account'/0/address_index (non-hardened)
            final_key, final_chain = self._derive_child_key(key, chain, address_index, hardened=False)
            
            # Convert to formats
            private_key_hex = final_key.hex()
            private_key_wif_compressed = self._private_key_to_wif_compressed(final_key, mainnet=True)
            segwit_address = self._private_key_to_segwit_address(final_key)
            
            derivation_path = f"m/84'/0'/{account}'/0/{address_index}"
            
            logger.debug(f"Derived address: {segwit_address}")
            logger.debug(f"WIF (compressed): {private_key_wif_compressed}")
            
            return {
                'address': segwit_address,
                'private_key_wif': private_key_wif_compressed,
                'private_key_hex': private_key_hex,
                'derivation_path': derivation_path
            }
            
        except Exception as e:
            logger.debug(f"Key derivation failed: {e}")
            return None

    def test_comprehensive_derivation(self):
        """Comprehensive test with multiple approaches to find the correct derivation"""
        logger.info("🎯 Bitcoin Midnight Claim Tool")
        logger.info("=" * 80)
        logger.info("Testing Bitcoin derivation scenarios for Midnight token claiming")
        logger.info(f"Workspace: {self.workspace}")
        logger.info("=" * 80)
        
        # Validate seed phrase first
        try:
            mnemo = Mnemonic("english")
            if mnemo.check(self.seed_phrase):
                word_count = len(self.seed_phrase.split())
                logger.info(f"✅ Seed phrase valid ({word_count} words)")
            else:
                logger.error("❌ Invalid seed phrase - check your .env file")
                return None
        except Exception as e:
            logger.error(f"Seed phrase validation error: {e}")
            return None
        
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
            logger.info(f"\n--- Testing passphrase scenario: {scenario_name} ---")
            
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
                        
                        if result and result['address']:
                            # Show first few addresses for debugging
                            if account == 0 and address_index < 3 and scenario_name == "current_passphrase":
                                addr_type = self.bitcoin_address_type.replace('_', ' ').title()
                                logger.info(f"  {addr_type.lower().replace(' ', '_')}_bip84[{address_index}]: {result['address']}")
                            
                            # Check for match
                            if result['address'] == self.eligible_bitcoin_address:
                                logger.info(f"\n🎯 MATCH FOUND!")
                                logger.info(f"  Passphrase scenario: {scenario_name}")
                                logger.info(f"  Derivation path: {result['derivation_path']}")
                                logger.info(f"  Address type: {self.bitcoin_address_type}")
                                logger.info(f"  Address: {result['address']}")
                                
                                return self._create_result(
                                    account, address_index, result, scenario_name, test_passphrase
                                )
                            
                    except Exception as e:
                        logger.debug(f"Derivation failed for account {account}, index {address_index}: {e}")
                        continue
        
        logger.error("❌ No matching derivation found across all scenarios")
        logger.error("Please check:")
        logger.error("  - Seed phrase is exactly correct")
        logger.error("  - Passphrase is exactly correct (including spaces/case)")
        logger.error("  - Bitcoin address is from the same wallet")
        logger.error("  - Address is Native SegWit (bc1q...)")
        return None

    def _create_result(self, account, address_index, derivation_result, scenario_name, passphrase_used):
        """Create successful result object"""
        logger.info("\n✅ Matching derivation found!")
        logger.info("Extracting private key...")
        
        return {
            'account': account,
            'address_index': address_index,
            'derivation_result': derivation_result,
            'scenario_name': scenario_name,
            'passphrase_used': passphrase_used,
            'address_type': self.bitcoin_address_type
        }

    def extract_private_key(self, derivation_info):
        """Extract and save the Bitcoin private key in compressed WIF format for Phantom Wallet"""
        logger.info("Extracting Bitcoin private key for Phantom Wallet...")
        
        try:
            derivation_result = derivation_info['derivation_result']
            address = derivation_result['address']
            private_key_wif = derivation_result['private_key_wif']
            private_key_hex = derivation_result['private_key_hex']
            
            # Verify WIF format for Phantom (should start with K or L for compressed mainnet keys)
            if not (private_key_wif.startswith('K') or private_key_wif.startswith('L')):
                logger.warning(f"WIF format may not be compatible with Phantom: starts with {private_key_wif[0]}")
            else:
                logger.info(f"✅ WIF format compatible with Phantom: starts with {private_key_wif[0]}")
            
            # Create safe filename from address
            safe_addr = address[:12].replace('bc1q', '').replace('bc1p', '')
            timestamp = int(__import__('time').time())
            
            # Define file paths
            wif_file = self.workspace / f"bitcoin_midnight_key_{safe_addr}_{timestamp}.wif"
            instructions_file = self.workspace / f"BITCOIN_SUCCESS_{safe_addr}_{timestamp}.txt"
            
            # Write WIF file (main file for Phantom)
            try:
                with open(wif_file, 'w') as f:
                    f.write(private_key_wif)
                logger.info(f"🔑 WIF File: {wif_file.name}")
            except Exception as e:
                logger.error(f"Failed to write WIF file: {e}")
                return None
            
            # Write detailed instructions
            try:
                with open(instructions_file, 'w') as f:
                    f.write("🎉 MIDNIGHT BITCOIN CLAIM - SUCCESS!\n")
                    f.write("=" * 80 + "\n\n")
                    f.write("DERIVATION DETAILS:\n")
                    f.write(f"Bitcoin Address: {address}\n")
                    f.write(f"Derivation Path: {derivation_result['derivation_path']}\n")
                    f.write(f"Address Type: {derivation_info['address_type']}\n")
                    f.write(f"Passphrase Scenario: {derivation_info['scenario_name']}\n\n")
                    
                    f.write("PRIVATE KEY (COMPRESSED WIF FORMAT):\n")
                    f.write(f"{private_key_wif}\n\n")
                    
                    f.write("PHANTOM WALLET IMPORT INSTRUCTIONS:\n")
                    f.write("=" * 50 + "\n")
                    f.write("1. Install Phantom Wallet Extension:\n")
                    f.write("   - Visit https://phantom.app\n")
                    f.write("   - Install browser extension\n\n")
                    
                    f.write("2. Import Private Key to Phantom:\n")
                    f.write("   - Open Phantom extension\n")
                    f.write("   - Click wallet icon (top right)\n")
                    f.write("   - Select 'Add/Connect Wallet'\n")
                    f.write("   - Choose 'Import Private Key'\n")
                    f.write("   - Select 'Bitcoin' as blockchain\n")
                    f.write(f"   - Paste this WIF key: {private_key_wif}\n")
                    f.write("   - Name wallet: 'Midnight Claim'\n")
                    f.write("   - Confirm import\n\n")
                    
                    f.write("3. Connect to Midnight Portal:\n")
                    f.write("   - Navigate to https://midnight.network\n")
                    f.write("   - Click 'Connect Wallet'\n")
                    f.write("   - Select 'Phantom'\n")
                    f.write("   - Authorize connection\n")
                    f.write(f"   - Verify address: {address}\n\n")
                    
                    f.write("4. Execute Claim:\n")
                    f.write("   - Follow portal claim instructions\n")
                    f.write("   - Sign transaction in Phantom\n")
                    f.write("   - Wait for confirmation\n\n")
                    
                    f.write("🚨 CRITICAL SECURITY STEPS:\n")
                    f.write("=" * 50 + "\n")
                    f.write("IMMEDIATELY after successful claiming:\n")
                    f.write("1. DELETE this .wif file\n")
                    f.write("2. REMOVE imported wallet from Phantom\n")
                    f.write("3. TRANSFER claimed tokens to NEW secure wallet\n")
                    f.write("4. DELETE entire project folder\n")
                    f.write("5. CLEAR browser cache/history\n")
                    f.write("6. ABANDON the OLD wallet completely\n\n")
                    
                    f.write("⚠️  SECURITY REMINDER:\n")
                    f.write("- This OLD wallet is compromised after exposing seed phrase\n")
                    f.write("- NEVER send tokens to OLD wallet addresses\n")
                    f.write("- ALWAYS use NEW secure wallet for receiving tokens\n")
                    
                logger.info(f"📋 Instructions: {instructions_file.name}")
            except Exception as e:
                logger.error(f"Failed to write instructions: {e}")
            
            result = {
                'wif_file': str(wif_file),
                'instructions_file': str(instructions_file),
                'derivation_info': derivation_info,
                'wif_compressed': private_key_wif,
                'address': address
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Private key extraction error: {e}")
            return None

    def run_claim_test(self):
        """Main method to run the Bitcoin claim test"""
        print("🎯 Bitcoin Midnight Claim Tool")
        print("=" * 80)
        print("Testing Bitcoin derivation scenarios for Midnight token claiming")
        print(f"Workspace: {self.workspace}")
        print("=" * 80)
        
        # Test comprehensive derivation
        result = self.test_comprehensive_derivation()
        
        if result:
            logger.info("✅ Derivation successful!")
            
            # Extract private key
            key_result = self.extract_private_key(result)
            if key_result:
                print("\n" + "="*90)
                print("🎊 BITCOIN MIDNIGHT CLAIM KEY SUCCESSFULLY GENERATED!")
                print("="*90)
                
                print(f"\n📁 KEY SAVED TO: {self.workspace}")
                print(f"🔑 WIF File: {Path(key_result['wif_file']).name}")
                print(f"📋 Instructions: {Path(key_result['instructions_file']).name}")
                
                print(f"\n✅ SUCCESS! Bitcoin private key extracted!")
                print(f"📂 Saved to: {self.workspace}")
                print(f"📖 Read instructions: {Path(key_result['instructions_file']).name}")
                
                print("\n🏆 BITCOIN CLAIM PREPARATION SUCCESSFUL!")
                print("Your Bitcoin private key is ready for Phantom wallet import!")
                
                return True
            else:
                logger.error("❌ Private key extraction failed")
                return False
        else:
            logger.error("❌ Comprehensive derivation test failed!")
            logger.info("Check your seed phrase and passphrase in .env file")
            return False

def main():
    print("🎯 Bitcoin Midnight Claim Tool")
    print("=" * 80)
    print("Deriving Bitcoin private keys for Phantom Wallet import")
    print("LIMITATION: Only works with Native SegWit (bc1) addresses")
    print("=" * 80)
    
    try:
        if not os.path.exists('.env'):
            print("❌ ERROR: .env file missing!")
            print("Please copy .env.example_bitcoin to .env and fill in your details")
            return False
        
        claimer = BitcoinMidnightClaim()
        success = claimer.run_claim_test()
        
        if success:
            print("\n🎉 BITCOIN CLAIM PREPARATION SUCCESSFUL!")
            print("Your Bitcoin private key is ready for Phantom Wallet import!")
            return True
        else:
            print("\n❌ Bitcoin claim test failed")
            print("Check your seed phrase and passphrase in .env file")
            return False
            
    except Exception as e:
        logger.error(f"Bitcoin claim test error: {e}")
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    main()