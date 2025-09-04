#!/usr/bin/env python3
"""
Convert PyCardano keys to Cardano CLI format for Eternl
"""

import json
import os
from pathlib import Path

def convert_to_cli_format():
    """Convert existing PyCardano keys to CLI format"""
    
    workspace = Path(r"D:\workspace\VisualStudio\Midnight Claim")
    
    # Find existing key files
    payment_file = None
    stake_file = None
    
    for file in workspace.glob("midnight_payment_*.skey"):
        payment_file = file
        break
    
    for file in workspace.glob("midnight_stake_*.skey"):
        stake_file = file
        break
    
    if not payment_file or not stake_file:
        print("❌ Existing key files not found!")
        return False
    
    print(f"🔄 Converting keys to CLI format...")
    print(f"Payment: {payment_file.name}")
    print(f"Stake: {stake_file.name}")
    
    try:
        # Read PyCardano keys
        with open(payment_file, 'r') as f:
            payment_data = json.load(f)
        
        with open(stake_file, 'r') as f:
            stake_data = json.load(f)
        
        # Convert to CLI format
        cli_payment = {
            "type": "PaymentExtendedSigningKeyShelley_ed25519_bip32",
            "description": "Payment Signing Key",
            "cborHex": payment_data.get('cborHex', '')
        }
        
        cli_stake = {
            "type": "StakeExtendedSigningKeyShelley_ed25519_bip32", 
            "description": "Stake Signing Key",
            "cborHex": stake_data.get('cborHex', '')
        }
        
        # Save CLI format keys
        cli_payment_file = workspace / "midnight_payment_cli.skey"
        cli_stake_file = workspace / "midnight_stake_cli.skey"
        
        with open(cli_payment_file, 'w') as f:
            json.dump(cli_payment, f, indent=2)
        
        with open(cli_stake_file, 'w') as f:
            json.dump(cli_stake, f, indent=2)
        
        print(f"✅ CLI format keys created:")
        print(f"📁 {cli_payment_file.name}")
        print(f"📁 {cli_stake_file.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return False

if __name__ == "__main__":
    convert_to_cli_format()