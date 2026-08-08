#!/usr/bin/env python3
"""
Convert PyCardano keys to Cardano CLI format for Eternl
"""

import json
import os
import stat
from pathlib import Path


def write_secret_json(path: Path, value: dict) -> None:
    """Create a new signing-key file and verify owner-only POSIX permissions."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        if os.name == "posix":
            os.fchmod(descriptor, 0o600)
            mode = stat.S_IMODE(os.fstat(descriptor).st_mode)
            if mode != 0o600:
                raise PermissionError(f"Secret file mode is {mode:o}, expected 600")
        with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
            descriptor = -1
            json.dump(value, handle, indent=2)
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        path.unlink(missing_ok=True)
        raise


def secure_workspace(path: Path) -> None:
    """Verify the conversion workspace where POSIX permissions are available."""
    if not path.is_dir():
        raise FileNotFoundError(f"Claim workspace does not exist: {path}")
    if os.name == "posix":
        os.chmod(path, 0o700)
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode != 0o700:
            raise PermissionError(f"Claim workspace mode is {mode:o}, expected 700")
    else:
        print("⚠️ Windows ACLs are not managed; verify CLAIM_WORKSPACE is private")


def convert_to_cli_format():
    """Convert existing PyCardano keys to CLI format"""

    workspace = Path(os.getenv('CLAIM_WORKSPACE', "./cardano_claim_output"))
    secure_workspace(workspace)
    
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

    created_secret_files = []
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
        
        write_secret_json(cli_payment_file, cli_payment)
        created_secret_files.append(cli_payment_file)
        write_secret_json(cli_stake_file, cli_stake)
        created_secret_files.append(cli_stake_file)
        
        print(f"✅ CLI format keys created:")
        print(f"📁 {cli_payment_file.name}")
        print(f"📁 {cli_stake_file.name}")
        
        return True
        
    except Exception as e:
        for created_file in created_secret_files:
            created_file.unlink(missing_ok=True)
        print(f"❌ Conversion failed: {e}")
        return False

if __name__ == "__main__":
    convert_to_cli_format()
