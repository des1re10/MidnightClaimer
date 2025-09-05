# ₿ Midnight Token Claim for Bitcoin Addresses (Trezor Users)

**Extract Bitcoin private keys from Trezor wallets to claim Midnight tokens via software wallets**

This tool helps Trezor users extract the correct Bitcoin private keys needed to claim Midnight (NIGHT) tokens from eligible Bitcoin addresses. It works with **both passphrase-protected and standard Trezor wallets**.

## ⚠️ CRITICAL SECURITY WARNING

- **This method requires exposing your hardware wallet seed phrase and passphrase**
- **NEVER use this on your primary wallet with funds**
- **RECOMMENDED: Create a NEW Trezor wallet, transfer funds there first**
- **Use your OLD eligible Bitcoin address in this script for claiming**
- **Only use on a secure, isolated computer**
- **Delete all generated files immediately after claiming**
- **Never share your seed phrase or private keys**

## 🔒 Recommended Security Strategy

**CRITICAL: This method requires exposing your seed phrase, so follow this approach:**

### Before Starting:
1. **Create a NEW Trezor wallet** (generate new seed) 
2. **Transfer ALL Bitcoin** from your old wallet to the new wallet
3. **Keep your OLD wallet** for this claim process only
4. **Use your OLD eligible Bitcoin address** in the script (the one with Midnight claim rights)

### 🚨 CRITICAL: Where to Send Claimed Tokens

- **NEVER use addresses from your OLD wallet for receiving claimed tokens**
- **ALWAYS use a fresh address from your NEW secure wallet**
- **The OLD wallet is compromised once you expose its seed phrase**
- **Any tokens sent to OLD wallet addresses are at risk**

### Why This Approach:
- ✅ Your Bitcoin funds are safe in the NEW wallet
- ✅ Your OLD wallet seed is only used for claiming authorization
- ✅ Claimed tokens go directly to your secure NEW wallet
- ✅ If anything goes wrong during claiming, your funds are protected
- ✅ You can abandon the OLD wallet completely after claiming

### After Claiming:
- **Claimed tokens should already be in your NEW secure wallet**
- **Double-check you used NEW wallet address for receiving**
- Abandon the OLD wallet completely
- Delete all exposed seed phrase materials

## 🎯 What This Solves

Midnight token claims from Bitcoin addresses require importing private keys into software wallets, but Trezor users can't easily extract these keys. This tool:

- ✅ Derives correct Bitcoin private keys from your Trezor seed
- ✅ Works with passphrase-protected wallets
- ✅ Supports all Bitcoin address types (Legacy, SegWit, Native SegWit)
- ✅ Tests multiple derivation scenarios automatically
- ✅ Generates WIF format private keys for software wallet import
- ✅ Provides step-by-step claim instructions

## 📋 Requirements

### Software Requirements
- **Python 3.8+** with pip
- **Software Bitcoin wallet** (Electrum, Sparrow, or Bitcoin Core)
- **Browser** for Midnight Portal access

### Hardware Requirements
- **Trezor hardware wallet** (Model T or One)
- **Your Trezor seed phrase** (12 or 24 words)
- **Passphrase** (if you use one, otherwise leave empty)

### Bitcoin Information Needed
- **Eligible Bitcoin address** from Midnight Portal
- **Bitcoin address type** (Legacy/SegWit/Native SegWit)

## ⚡ Quick Start

### 1. Download Files
Download these files to a secure folder:
- `midnight_claim_bitcoin.py` (main script)
- `requirements_bitcoin.txt` (dependencies)
- `.env.example_bitcoin` (configuration template)

### 2. Install Dependencies
```bash
pip install -r requirements_bitcoin.txt
```

### 3. Setup Environment
Copy the template and create your configuration:
```bash
cp .env.example_bitcoin .env
```

Then edit `.env` with your actual Trezor information:
```env
# Replace with your actual seed phrase (12 or 24 words)
TREZOR_SEED_PHRASE=word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12

# Replace with your actual passphrase (or leave empty if none)
TREZOR_PASSPHRASE=YourActualPassphrase

# Replace with your eligible Bitcoin address from Midnight Portal
BITCOIN_CLAIM_ADDRESS=1A1zP5eP6**************************
```

### 4. Run the Script
```bash
python midnight_claim_bitcoin.py
```

### 5. Import to Software Wallet
The script generates WIF (Wallet Import Format) private keys that can be imported into any Bitcoin software wallet.

## 📍 How to Get Required Information

### Getting Your Eligible Bitcoin Address
1. Visit [Midnight Portal](https://midnight.network)
2. Connect your wallet or check eligibility
3. Navigate to Bitcoin token claim section
4. Copy the displayed eligible Bitcoin address

### Understanding Bitcoin Address Types

#### Legacy Addresses (P2PKH)
- **Format**: Start with `1`
- **Example**: `1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa`
- **Derivation**: `m/44'/0'/0'/0/0`
- **Note**: Oldest format, highest fees

#### SegWit Addresses (P2SH-P2WPKH)
- **Format**: Start with `3`
- **Example**: `3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy`
- **Derivation**: `m/49'/0'/0'/0/0`
- **Note**: Wrapped SegWit, medium fees

#### Native SegWit Addresses (P2WPKH)
- **Format**: Start with `bc1`
- **Example**: `bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4`
- **Derivation**: `m/84'/0'/0'/0/0`
- **Note**: Modern format, lowest fees

The script automatically detects your address type and tests appropriate derivation paths.

## 📖 Example Successful Output

When the script works correctly, you'll see output like this:

```
🎯 Bitcoin Midnight Claim Tool
================================================================================
Testing Bitcoin derivation scenarios for Midnight token claiming
Workspace: D:\workspace\VisualStudio\Midnight Bitcoin Claim
================================================================================

✅ Seed phrase valid (12 words)

--- Testing passphrase scenario: current_passphrase ---
  native_segwit_bip84[0]: bc1qw508d6qejxtd...

🎯 MATCH FOUND!
  Passphrase scenario: current_passphrase
  Derivation path: m/84'/0'/0'/0/0
  Address type: native_segwit
  Address: bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4

✅ Matching derivation found!
Extracting private key...

==========================================================================================
🎊 BITCOIN MIDNIGHT CLAIM KEY SUCCESSFULLY GENERATED!
==========================================================================================

📁 KEY SAVED TO: D:\workspace\VisualStudio\Midnight Bitcoin Claim
🔑 WIF File: bitcoin_midnight_key_bc1qw508_12345.wif
📋 Instructions: BITCOIN_SUCCESS_bc1qw508_12345.txt

✅ SUCCESS! Bitcoin private key extracted!
📂 Saved to: D:\workspace\VisualStudio\Midnight Bitcoin Claim
📖 Read instructions: BITCOIN_SUCCESS_bc1qw508_12345.txt

🏆 BITCOIN CLAIM PREPARATION SUCCESSFUL!
Your Bitcoin private key is ready for wallet import!
```

## 💾 Software Wallet Import Process

### Option 1: Electrum Wallet (Recommended)

#### 1. Install Electrum
- Download from [electrum.org](https://electrum.org)
- Verify signature and install

#### 2. Import Private Key
1. Open Electrum
2. **File** → **New/Restore**
3. Choose **"Import Bitcoin addresses or private keys"**
4. Paste your WIF private key from the `.wif` file
5. **Next** → **Create**
6. Wallet is ready for claiming

### Option 2: Sparrow Wallet

#### 1. Install Sparrow
- Download from [sparrowwallet.com](https://sparrowwallet.com)
- Install and launch

#### 2. Import Private Key
1. **File** → **New Wallet**
2. Choose **"Imported"**
3. **Script Type**: Choose based on your address type:
   - Legacy: P2PKH
   - SegWit: P2SH-P2WPKH
   - Native SegWit: P2WPKH
4. Paste WIF private key
5. **Create Wallet**

### Option 3: Bitcoin Core (Advanced)

#### 1. Install Bitcoin Core
- Download from [bitcoin.org](https://bitcoin.org)
- Sync blockchain (may take days)

#### 2. Import Private Key
1. Open Bitcoin Core console
2. Run: `importprivkey "YOUR_WIF_KEY" "midnight_claim"`
3. Wait for rescan to complete

## 🌙 Claiming Process

### 1. Connect Wallet to Midnight Portal
1. Open your software wallet
2. Navigate to [Midnight Portal](https://midnight.network)
3. Connect your imported wallet
4. Verify the correct Bitcoin address is displayed

### 2. Execute Claim
1. Navigate to Bitcoin token claim section
2. Follow portal instructions
3. Sign the claim transaction in your software wallet
4. Confirm transaction
5. Wait for confirmation

### 3. Secure Cleanup (CRITICAL!)

🚨 **IMMEDIATELY after successful claiming:**
1. **Delete** all `.wif` files from your computer
2. **Delete** the software wallet you created
3. **Transfer** claimed tokens to your NEW secure hardware wallet
4. **Delete** entire project folder
5. **Clear** browser cache/history
6. **Abandon** the OLD wallet completely

## 🔧 Troubleshooting

### For Wallets WITHOUT Passphrase
If you don't use a passphrase on your Trezor:
```env
TREZOR_PASSPHRASE=
```
Leave it completely empty - the script will test this scenario automatically.

### Common Issues

**"No address match found"**
- ✅ Script automatically tests multiple derivation scenarios
- ✅ Verify your seed phrase is exactly correct
- ✅ Try with empty passphrase if you're unsure
- ✅ Check if you're using a different account/index

**"Wallet creation failed"**
- Check seed phrase format (12 or 24 words, space-separated)
- Verify no extra spaces or special characters
- Ensure passphrase encoding is correct

**"Software wallet won't import WIF"**
- Verify the WIF format is correct (should start with 5, K, or L)
- Try a different software wallet
- Check that the wallet supports your address type

**"Portal doesn't recognize address"**
- Ensure you're using the exact eligible address from the portal
- Verify your derived address matches the eligible one
- Contact Midnight support if address eligibility is unclear

**"Permission denied"**
- Run terminal/command prompt as administrator
- Ensure Python has write permissions to the folder

## 🔐 Security Best Practices

1. **Use offline computer** for key generation
2. **Create NEW wallet first** and transfer funds there
3. **Never share** seed phrases or private keys
4. **Delete all files** immediately after successful claim
5. **Use hardware wallet** for long-term storage
6. **Double-check** all addresses before sending transactions
7. **Abandon OLD wallet** after claiming is complete
8. **Verify software wallet downloads** from official sources only

## 📝 Important Notes

### Bitcoin Address Derivation Paths
- **Legacy (P2PKH)**: `m/44'/0'/account'/0/index`
- **SegWit (P2SH-P2WPKH)**: `m/49'/0'/account'/0/index`
- **Native SegWit (P2WPKH)**: `m/84'/0'/account'/0/index`

### Does This Work Without Passphrase?
**YES!** The script automatically tests multiple scenarios:
- With your provided passphrase
- With empty passphrase
- With various passphrase normalizations

### Seed Phrase Length Support
- **12-word seeds**: Fully supported
- **24-word seeds**: Fully supported
- Both are tested automatically

### Multiple Address Testing
The script automatically tests:
- Multiple account numbers (0, 1, 2, etc.)
- Multiple address indices (0-19 for each account)
- All passphrase scenarios
- Proper derivation paths for detected address types

## ✅ Tested Configurations

This tool has been tested with:

### Address Types:
- ✅ **Legacy addresses** (1...) - P2PKH
- ✅ **SegWit addresses** (3...) - P2SH-P2WPKH
- ✅ **Native SegWit addresses** (bc1...) - P2WPKH

### Software Wallets:
- ✅ **Electrum** - Recommended for ease of use
- ✅ **Sparrow Wallet** - Good for advanced users
- ✅ **Bitcoin Core** - Full node option

### Hardware:
- ✅ **Trezor Model T** with passphrase protection
- ✅ **Trezor One** with and without passphrase
- ✅ **12-word and 24-word seeds**

## 💝 Support This Project

If this tool helped you successfully claim your Midnight tokens, consider supporting the project! 

*Donation addresses are available in the main README file.*

## 🆘 Support

- **Script Issues**: Create GitHub issue with error details
- **Midnight Claims**: Contact Midnight support team
- **Bitcoin Wallet Problems**: Consult wallet documentation
- **General Bitcoin Questions**: Bitcoin community forums

## ⚖️ Disclaimer

- **This tool is provided as-is**
- **Authors not responsible for lost funds**
- **Always verify outputs independently**
- **Use only for legitimate token claims**
- **Delete all private keys after use**
- **This method exposes your seed phrase - use recommended security strategy**

---

**🎯 Successfully claim your Midnight tokens from Bitcoin addresses safely!**

*Remember: Security first - create new wallet, use old eligible address, delete everything after claiming!*