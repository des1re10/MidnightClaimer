#!/usr/bin/env python3
"""
Midnight Bitcoin Claim - CORRECTED VERSION
Properly generates bc1 Native SegWit addresses
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

class BitcoinMidnightClaimCorrected:
    def __init__(self):
        load_dotenv()
        
        self.seed_phrase = os.getenv('TREZOR_SEED_PHRASE')
        self.passphrase = os.getenv('TREZOR_PASSPHRASE', '')
        self.eligible_bitcoin_address = os.getenv('BITCOIN_CLAIM_ADDRESS')
        
        if not all([self.seed_phrase, self.eligible_bitcoin_address]):
            raise ValueError("TREZOR_SEED_PHRASE and BITCOIN_CLAIM_ADDRESS are required")
        
        if not self.eligible_bitcoin_address.startswith('bc1'):
            raise ValueError("Only bc1 addresses supported")
            
        print(f"Target Bitcoin address: {self.eligible_bitcoin_address}")
        print(f"Passphrase configured: {'Yes' if self.passphrase else 'No'}")
        
        self.workspace = Path("./bitcoin_claim_output")
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _derive_master_key(self, seed_phrase, passphrase):
        """Derive master private key from seed phrase"""
        mnemo = Mnemonic("english")
        if not mnemo.check(seed_phrase):
            raise ValueError("Invalid seed phrase")
        seed = mnemo.to_seed(seed_phrase, passphrase=passphrase)
        hmac_result = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
        return hmac_result[:32], hmac_result[32:]

    def _point_multiply_g(self, private_key_int):
        """Multiply generator point G by private key to get public key point"""
        # secp256k1 generator point G (uncompressed)
        Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
        Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
        
        # secp256k1 curve parameters
        p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
        
        if private_key_int == 0:
            return None, None
        
        # Simple double-and-add algorithm (not optimized but works)
        def point_double(x, y):
            if y == 0:
                return None, None
            s = (3 * x * x * pow(2 * y, p - 2, p)) % p
            x3 = (s * s - 2 * x) % p
            y3 = (s * (x - x3) - y) % p
            return x3, y3
        
        def point_add(x1, y1, x2, y2):
            if x1 is None:
                return x2, y2
            if x2 is None:
                return x1, y1
            if x1 == x2:
                if y1 == y2:
                    return point_double(x1, y1)
                else:
                    return None, None
            s = ((y2 - y1) * pow(x2 - x1, p - 2, p)) % p
            x3 = (s * s - x1 - x2) % p
            y3 = (s * (x1 - x3) - y1) % p
            return x3, y3
        
        # Point multiplication using binary method
        result_x, result_y = None, None
        addend_x, addend_y = Gx, Gy
        
        while private_key_int:
            if private_key_int & 1:
                result_x, result_y = point_add(result_x, result_y, addend_x, addend_y)
            addend_x, addend_y = point_double(addend_x, addend_y)
            private_key_int >>= 1
        
        return result_x, result_y

    def _private_key_to_public_key(self, private_key_bytes):
        """Convert private key to compressed public key"""
        private_key_int = int.from_bytes(private_key_bytes, 'big')
        
        # Get public key point
        x, y = self._point_multiply_g(private_key_int)
        if x is None:
            raise ValueError("Invalid private key")
        
        # Create compressed public key
        if y % 2 == 0:
            return b'\x02' + x.to_bytes(32, 'big')
        else:
            return b'\x03' + x.to_bytes(32, 'big')

    def _derive_child_key(self, parent_private_key, parent_chain_code, index, hardened=False):
        """Derive child private key using proper BIP32"""
        if hardened:
            index += 0x80000000
            data = b'\x00' + parent_private_key + struct.pack('>I', index)
        else:
            # Non-hardened: use public key
            parent_public_key = self._private_key_to_public_key(parent_private_key)
            data = parent_public_key + struct.pack('>I', index)
        
        hmac_result = hmac.new(parent_chain_code, data, hashlib.sha512).digest()
        child_private_key_int = int.from_bytes(hmac_result[:32], 'big')
        parent_private_key_int = int.from_bytes(parent_private_key, 'big')
        
        curve_order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        final_private_key_int = (child_private_key_int + parent_private_key_int) % curve_order
        
        if final_private_key_int == 0:
            raise ValueError("Invalid key derivation")
            
        final_private_key = final_private_key_int.to_bytes(32, 'big')
        child_chain_code = hmac_result[32:]
        
        return final_private_key, child_chain_code

    def _hash160(self, data):
        """RIPEMD160(SHA256(data))"""
        sha256_hash = hashlib.sha256(data).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256_hash)
        return ripemd160.digest()

    def _bech32_polymod(self, values):
        """Bech32 polymod function"""
        GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
        chk = 1
        for value in values:
            top = chk >> 25
            chk = (chk & 0x1ffffff) << 5 ^ value
            for i in range(5):
                chk ^= GEN[i] if ((top >> i) & 1) else 0
        return chk

    def _bech32_hrp_expand(self, hrp):
        """Expand HRP for bech32"""
        return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

    def _bech32_verify_checksum(self, hrp, data):
        """Verify bech32 checksum"""
        return self._bech32_polymod(self._bech32_hrp_expand(hrp) + data) == 1

    def _bech32_create_checksum(self, hrp, data):
        """Create bech32 checksum"""
        values = self._bech32_hrp_expand(hrp) + data
        polymod = self._bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
        return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]

    def _convertbits(self, data, frombits, tobits, pad=True):
        """Convert between bit groups"""
        acc = 0
        bits = 0
        ret = []
        maxv = (1 << tobits) - 1
        max_acc = (1 << (frombits + tobits - 1)) - 1
        for value in data:
            if value < 0 or (value >> frombits):
                return None
            acc = ((acc << frombits) | value) & max_acc
            bits += frombits
            while bits >= tobits:
                bits -= tobits
                ret.append((acc >> bits) & maxv)
        if pad:
            if bits:
                ret.append((acc << (tobits - bits)) & maxv)
        elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
            return None
        return ret

    def _private_key_to_bc1_address(self, private_key_bytes):
        """Convert private key to bc1 Native SegWit address"""
        try:
            # Get compressed public key
            public_key = self._private_key_to_public_key(private_key_bytes)
            
            # Create public key hash (HASH160)
            pubkey_hash = self._hash160(public_key)
            
            # Convert to 5-bit groups for bech32
            conv = self._convertbits(pubkey_hash, 8, 5)
            if conv is None:
                raise ValueError("Failed to convert bits")
            
            # Witness version 0 for P2WPKH
            data = [0] + conv
            
            # Create checksum
            checksum = self._bech32_create_checksum('bc', data)
            
            # Combine and encode
            combined = data + checksum
            
            # Convert to characters
            charset = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
            result = 'bc1' + ''.join([charset[x] for x in combined])
            
            return result
            
        except Exception as e:
            return f"Error: {e}"

    def _private_key_to_wif_compressed(self, private_key_bytes):
        """Convert private key to compressed WIF format"""
        extended_key = b'\x80' + private_key_bytes + b'\x01'  # mainnet + compressed
        checksum = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]
        return base58.b58encode(extended_key + checksum).decode('ascii')

    def test_derivation_paths(self, passphrase, max_accounts=5, max_indices=20):
        """Test BIP84 derivation with proper bc1 address generation"""
        print(f"\n=== Testing BIP84 Native SegWit Derivation ===")
        
        try:
            master_key, master_chain = self._derive_master_key(self.seed_phrase, passphrase)
        except Exception as e:
            print(f"Failed to derive master key: {e}")
            return None
        
        try:
            # BIP84 path: m/84'/0'/account'/0/index
            # Derive m/84'
            key, chain = self._derive_child_key(master_key, master_chain, 84, hardened=True)
            # Derive m/84'/0'
            key, chain = self._derive_child_key(key, chain, 0, hardened=True)
            
            for account in range(max_accounts):
                # Derive m/84'/0'/account'
                acc_key, acc_chain = self._derive_child_key(key, chain, account, hardened=True)
                # Derive m/84'/0'/account'/0 (external chain)
                ext_key, ext_chain = self._derive_child_key(acc_key, acc_chain, 0, hardened=False)
                
                print(f"\nAccount {account}:")
                
                for index in range(min(max_indices, 10)):  # Show first 10 addresses
                    try:
                        # Derive final key
                        final_key, _ = self._derive_child_key(ext_key, ext_chain, index, hardened=False)
                        
                        # Generate bc1 address
                        bc1_address = self._private_key_to_bc1_address(final_key)
                        
                        print(f"  [{index:2d}] {bc1_address}")
                        
                        # Check for match
                        if bc1_address == self.eligible_bitcoin_address:
                            wif = self._private_key_to_wif_compressed(final_key)
                            
                            print(f"\n🎯 PERFECT MATCH FOUND!")
                            print(f"Account: {account}")
                            print(f"Index: {index}")
                            print(f"Path: m/84'/0'/{account}'/0/{index}")
                            print(f"Address: {bc1_address}")
                            
                            return {
                                'account': account,
                                'index': index,
                                'address': bc1_address,
                                'wif': wif,
                                'private_key_hex': final_key.hex(),
                                'derivation_path': f"m/84'/0'/{account}'/0/{index}"
                            }
                            
                    except Exception as e:
                        print(f"  [{index:2d}] Error: {e}")
                        
        except Exception as e:
            print(f"BIP84 derivation failed: {e}")
        
        return None

    def comprehensive_test(self):
        """Test multiple passphrase scenarios"""
        print("🔍 COMPREHENSIVE BC1 ADDRESS DERIVATION TEST")
        print("=" * 80)
        print(f"Target: {self.eligible_bitcoin_address}")
        print("=" * 80)
        
        # Validate seed phrase
        try:
            mnemo = Mnemonic("english")
            if mnemo.check(self.seed_phrase):
                word_count = len(self.seed_phrase.split())
                print(f"✅ Seed phrase valid ({word_count} words)")
            else:
                print("❌ Invalid seed phrase")
                return None
        except Exception as e:
            print(f"Seed validation error: {e}")
            return None
        
        # Test different passphrase scenarios
        passphrase_scenarios = [
            ("original", self.passphrase),
            ("empty", ""),
            ("trimmed", self.passphrase.strip()),
            ("lowercase", self.passphrase.lower()),
            ("uppercase", self.passphrase.upper()),
            ("nfc_normalized", unicodedata.normalize('NFC', self.passphrase)),
            ("nfd_normalized", unicodedata.normalize('NFD', self.passphrase)),
            ("nfkc_normalized", unicodedata.normalize('NFKC', self.passphrase)),
            ("nfkd_normalized", unicodedata.normalize('NFKD', self.passphrase)),
        ]
        
        for scenario_name, test_passphrase in passphrase_scenarios:
            print(f"\n{'='*20} Scenario: {scenario_name} {'='*20}")
            if scenario_name != "empty":
                print(f"Passphrase configured: Yes (length: {len(test_passphrase)})")
            else:
                print("Passphrase: (empty)")
            
            result = self.test_derivation_paths(test_passphrase)
            if result:
                print(f"\n🎉 SUCCESS! Match found with scenario: {scenario_name}")
                return result, scenario_name
        
        print("\n❌ No matches found in any scenario")
        print("\nDebugging suggestions:")
        print("1. Double-check seed phrase word order and spelling")
        print("2. Verify passphrase exact capitalization and spacing")
        print("3. Confirm target address is from this wallet")
        print("4. Check if address might be from a different account/derivation")
        return None

    def save_successful_result(self, result, scenario_name):
        """Save the successful derivation result"""
        timestamp = int(__import__('time').time())
        safe_addr = result['address'][:12].replace('bc1q', '')
        
        wif_file = self.workspace / f"bitcoin_key_{safe_addr}_{timestamp}.wif"
        info_file = self.workspace / f"SUCCESS_{safe_addr}_{timestamp}.txt"
        
        # Save WIF key
        with open(wif_file, 'w') as f:
            f.write(result['wif'])
        
        # Save detailed info
        with open(info_file, 'w') as f:
            f.write("🎉 MIDNIGHT BITCOIN CLAIM - MATCH FOUND!\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Target Address: {result['address']}\n")
            f.write(f"Derivation Path: {result['derivation_path']}\n")
            f.write(f"Passphrase Scenario: {scenario_name}\n")
            f.write(f"Account: {result['account']}\n")
            f.write(f"Address Index: {result['index']}\n\n")
            f.write("PRIVATE KEY (Compressed WIF - FOR PHANTOM WALLET):\n")
            f.write(f"{result['wif']}\n\n")
            f.write("PHANTOM WALLET IMPORT INSTRUCTIONS:\n")
            f.write("=" * 50 + "\n")
            f.write("1. Install Phantom Wallet browser extension\n")
            f.write("2. Open Phantom > Add/Connect Wallet\n")
            f.write("3. Select 'Import Private Key'\n")
            f.write("4. Choose 'Bitcoin' as blockchain\n")
            f.write("5. Paste the WIF key above\n")
            f.write("6. Complete import and verify address matches\n\n")
            f.write("MIDNIGHT PORTAL CLAIMING:\n")
            f.write("1. Go to midnight.network\n")
            f.write("2. Connect Phantom wallet\n")
            f.write("3. Verify correct address is shown\n")
            f.write("4. Follow claim process\n\n")
            f.write("🚨 SECURITY: DELETE ALL FILES AFTER CLAIMING!\n")
        
        print(f"\n📁 Files saved:")
        print(f"🔑 WIF Key: {wif_file.name}")
        print(f"📄 Details: {info_file.name}")
        
        return True

def main():
    print("🔍 Bitcoin BC1 Address Derivation Tool - CORRECTED VERSION")
    print("=" * 80)
    print("Now properly generates bc1 Native SegWit addresses")
    print("=" * 80)
    
    try:
        if not os.path.exists('.env'):
            print("❌ .env file missing!")
            return False
        
        tool = BitcoinMidnightClaimCorrected()
        result = tool.comprehensive_test()
        
        if result:
            match_result, scenario = result
            print(f"\n🎊 SUCCESS! Private key found for scenario: {scenario}")
            tool.save_successful_result(match_result, scenario)
            print("✅ Compressed WIF key ready for Phantom wallet import!")
            return True
        else:
            print("\n❌ No matching address found")
            print("Double-check your seed phrase and passphrase")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    main()