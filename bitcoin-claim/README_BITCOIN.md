# ₿ Midnight Token Claim for Bitcoin Addresses (Trezor Users)

**Extract Bitcoin private keys from Trezor wallets to claim Midnight tokens via Phantom Wallet**

This tool helps Trezor users extract Bitcoin private keys needed to claim Midnight (NIGHT) tokens from eligible Bitcoin addresses. **CRITICAL LIMITATION: This process ONLY works with Native SegWit (bc1) and Taproot Bitcoin addresses using Phantom Wallet.**

## ⚠️ CRITICAL COMPATIBILITY WARNING

**THIS PROCESS ONLY WORKS IF:**
- Your eligible Bitcoin address starts with `bc1` (Native SegWit) or is Taproot format
- You can use Phantom Wallet browser extension
- Phantom successfully imports your WIF private key

**THIS PROCESS WILL NOT WORK FOR:**
- Legacy addresses starting with `1`
- SegWit addresses starting with `3`
- Users who cannot install browser extensions

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

Midnight token claims from Bitcoin addresses require importing private keys into browser wallets, but Trezor users can't easily extract these keys. This tool:

- ✅ Derives correct Bitcoin private keys from your Trezor seed
- ✅ Works with passphrase-protected wallets
- ✅ Supports Native SegWit (bc1) and Taproot addresses ONLY
- ✅ Tests multiple derivation scenarios automatically
- ✅ Generates WIF format private keys for Phantom wallet import
- ✅ Provides step-by-step claim instructions

## 📋 Requirements

### Software Requirements
- **Python 3.8+** with pip
- **Phantom Wallet browser extension**
- **Browser** for Midnight Portal access

### Hardware Requirements
- **Trezor hardware wallet** (Model T or One)
- **Your Trezor seed phrase** (12 or 24 words)
- **Passphrase** (if you use one, otherwise leave empty)

### Bitcoin Information Needed
- **Eligible Bitcoin address** from Midnight Portal (MUST start with bc1 or be Taproot)
- **Bitcoin address type** (Native SegWit or Taproot ONLY)

## ⚡ Quick Start

### 1. Check Address Compatibility
**BEFORE PROCEEDING, verify your eligible Bitcoin address starts with `bc1`**

If your address starts with `1` or `3`, this process will NOT work. Contact Midnight support for alternative claiming methods.

### 2. Download Files
Download these files to a secure folder:
- `midnight_claim_bitcoin.py` (main script)
- `requirements_bitcoin.txt` (dependencies)
- `.env.example_bitcoin` (configuration template)

### 3. Install Dependencies
```bash
pip install -r requirements_bitcoin.txt
```

### 4. Setup Environment
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

# Replace with your eligible Bitcoin address from Midnight Portal (MUST start with bc1)
BITCOIN_CLAIM_ADDRESS=bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4
```

### 5. Run the Script
```bash
python midnight_claim_bitcoin.py
```

### 6. Import to Phantom Wallet
The script generates WIF (Wallet Import Format) private keys that can be imported into Phantom Wallet ONLY.

## 📖 Example Successful Output

When the script works correctly, you'll see output like this:

```
🎯 Bitcoin Midnight Claim Tool
================================================================================
Testing Bitcoin derivation scenarios for Midnight token claiming
Workspace: /your/secure/folder/bitcoin_claim_output
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

📁 KEY SAVED TO: /your/secure/folder/bitcoin_claim_output
🔑 WIF File: bitcoin_midnight_key_bc1qw508_12345.wif
📋 Instructions: BITCOIN_SUCCESS_bc1qw508_12345.txt

✅ SUCCESS! Bitcoin private key extracted!
📂 Saved to: /your/secure/folder/bitcoin_claim_output
📖 Read instructions: BITCOIN_SUCCESS_bc1qw508_12345.txt

🏆 BITCOIN CLAIM PREPARATION SUCCESSFUL!
Your Bitcoin private key is ready for Phantom wallet import!
```

## 👤 Phantom Wallet Import Process

### 1. Install Phantom Wallet
- Visit [phantom.app](https://phantom.app)
- Install browser extension
- Create or restore a wallet (you can use a temporary one)

### 2. Import Private Key to Phantom
1. Open Phantom extension
2. Click the **wallet icon** (top right)
3. Select **"Add/Connect Wallet"**
4. Choose **"Import Private Key"**
5. Select **"Bitcoin"** as the blockchain
6. Paste your WIF private key from the `.wif` file
7. Name the imported wallet (e.g., "Midnight Claim")
8. Confirm import

### 3. Connect to Midnight Portal
1. Navigate to [Midnight Portal](https://midnight.network)
2. Click **"Connect Wallet"**
3. Select **"Phantom"** from the wallet list
4. Authorize the connection
5. Verify the correct Bitcoin address is displayed

### 4. Execute Claim
1. Navigate to Bitcoin token claim section
2. Follow portal instructions
3. Sign the claim transaction in Phantom
4. Confirm transaction
5. Wait for confirmation

### 5. Secure Cleanup (CRITICAL!)

🚨 **IMMEDIATELY after successful claiming:**
1. **Delete** all `.wif` files from your computer
2. **Remove** the imported wallet from Phantom
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

**"Address doesn't start with bc1"**
- This process only works with Native SegWit addresses
- Contact Midnight support for alternative claiming methods
- Consider if you have other eligible addresses in different formats

**"Phantom won't import WIF key"**
- Ensure you're selecting "Bitcoin" as the blockchain in Phantom
- Verify the WIF format is correct (should start with K or L for bc1 addresses)
- Try creating a fresh Phantom wallet first

**"Portal doesn't recognize Phantom wallet"**
- Ensure Phantom is properly connected to the portal
- Try disconnecting and reconnecting
- Check that the imported address matches the eligible one

**"No address match found"**
- Script automatically tests multiple derivation scenarios
- Verify your seed phrase is exactly correct
- Try with empty passphrase if you're unsure
- Check if you're using a different account/index

**"Wallet creation failed"**
- Check seed phrase format (12 or 24 words, space-separated)
- Verify no extra spaces or special characters
- Ensure passphrase encoding is correct

## 📝 Important Notes

### Address Type Limitations
**ONLY SUPPORTED:**
- **Native SegWit (P2WPKH)**: `bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4`
- **Taproot**: `bc1p...` (if supported by your setup)

**NOT SUPPORTED:**
- **Legacy (P2PKH)**: `1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa`
- **SegWit (P2SH-P2WPKH)**: `3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy`

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
- Proper derivation paths for Native SegWit addresses

## ⚠️ Wallet Portal Limitations

The Midnight Portal only supports these browser wallets:
- **Phantom** (Bitcoin private key import supported)
- **OKX Wallet** (seed phrase only)
- **Leather** (seed phrase only)
- **Xverse Wallet** (seed phrase only)
- **Ledger Live** (hardware wallet only)

This is why desktop wallets like Electrum and Sparrow cannot be used, despite their superior private key import capabilities.

## ✅ Tested Configurations

This tool has been tested with:

### Address Types:
- ✅ **Native SegWit addresses** (bc1...) - P2WPKH
- ❌ **Legacy addresses** (1...) - NOT SUPPORTED
- ❌ **SegWit addresses** (3...) - NOT SUPPORTED

### Browser Wallets:
- ✅ **Phantom** - Native SegWit private key import

### Hardware:
- ✅ **Trezor Model T** with passphrase protection
- ✅ **Trezor One** with and without passphrase
- ✅ **12-word and 24-word seeds**

## 🆘 Alternative Solutions

### If Your Address Is Not bc1 Format:
1. **Contact Midnight Support** - they may have alternative claiming methods
2. **Check for other eligible addresses** - you might have bc1 addresses you haven't checked
3. **Wait for expanded wallet support** - portal may add more wallet options

### If Phantom Import Fails:
1. **Try creating a completely fresh Phantom wallet**
2. **Contact Phantom support** about private key import issues
3. **Reach out to Midnight community** for alternative approaches

## 💡 Support This Project

If this tool helped you successfully claim your Midnight tokens, consider supporting the project! 

*Donation addresses are available in the main README file.*

## 🆘 Support

- **Script Issues**: Create GitHub issue with error details
- **Midnight Claims**: Contact Midnight support team
- **Phantom Wallet Problems**: Consult Phantom documentation
- **General Bitcoin Questions**: Bitcoin community forums

## ⚖️ Disclaimer

- **This tool is provided as-is**
- **Authors not responsible for lost funds**
- **Always verify outputs independently**
- **Use only for legitimate token claims**
- **Delete all private keys after use**
- **This method exposes your seed phrase - use recommended security strategy**
- **Limited to Native SegWit addresses only**

---

**🎯 Successfully claim your Midnight tokens from Native SegWit Bitcoin addresses safely!**

*Remember: This only works with bc1 addresses. Contact Midnight support if your address starts with 1 or 3.*