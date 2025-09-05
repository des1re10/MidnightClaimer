# 🌙 Midnight Token Claim for Trezor Users

**Extract private keys from Trezor wallets to claim Midnight tokens via Eternl**

This tool helps Trezor users extract the correct private keys needed to claim Midnight (NIGHT) tokens. It works with **both passphrase-protected and standard Trezor wallets**.

## ⚠️ CRITICAL SECURITY WARNING

- **This method requires exposing your hardware wallet seed phrase and passphrase**
- **NEVER use this on your primary wallet with funds**
- **RECOMMENDED: Create a NEW Trezor wallet, transfer funds there first**
- **Use your OLD eligible address in this script for claiming**
- **Only use on a secure, isolated computer with synced Cardano node**
- **Delete all generated files immediately after claiming**
- **Never share your seed phrase or private keys**

## 🔒 Recommended Security Strategy

**CRITICAL: This method requires exposing your seed phrase, so follow this approach:**

### Before Starting:
1. **Create a NEW Trezor wallet** (generate new seed) 
2. **Transfer ALL funds** from your old wallet to the new wallet
3. **Keep your OLD wallet** for this claim process only
4. **Use your OLD eligible address** in the script (the one with Midnight claim rights)

### **🚨 CRITICAL: Where to Send Claimed Tokens**
- **NEVER use addresses from your OLD wallet for receiving claimed tokens**
- **ALWAYS use a fresh address from your NEW secure wallet**
- **The OLD wallet is compromised once you expose its seed phrase**
- **Any tokens sent to OLD wallet addresses are at risk**

### Why This Approach:
- ✅ Your funds are safe in the NEW wallet
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

Midnight token claims require importing private keys into Eternl wallet, but Trezor users can't easily extract these keys. This tool:

- ✅ Derives correct payment and staking keys from your Trezor seed
- ✅ Works with passphrase-protected wallets
- ✅ Tests multiple derivation scenarios automatically
- ✅ Generates Eternl-compatible `.skey` files
- ✅ Provides step-by-step claim instructions

## 📋 Requirements

### Software Requirements
- **Python 3.8+** with pip (including latest versions like Python 3.13.7)
- **Browser** with Eternl wallet extension
- **Cardano Node** (synced mainnet node - see setup instructions below)

### Hardware Requirements
- **Trezor hardware wallet** (Model T or One)
- **Your Trezor seed phrase** (12 or 24 words)
- **Passphrase** (if you use one, otherwise leave empty)

### Wallet Information Needed
- **Claim address** from Midnight Portal
- **Payment derivation path** (usually `m/1852'/1815'/0'/0/0`)
- **Stake key checksum** from your Cardano wallet

## 🚀 Quick Start

### 1. Download Files
Download these files to a secure folder:
- `midnight_claim.py` (main script)
- `cli_convert.py` (CLI format converter - REQUIRED for Eternl)
- `requirements.txt` (dependencies)
- `.env.example` (configuration template)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Environment
Copy the template and create your configuration:
```bash
cp .env.example .env
```

Then edit `.env` with your actual Trezor information (replace ALL placeholder values):
```env
# Replace with your actual seed phrase (12 or 24 words)
TREZOR_SEED_PHRASE=word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12

# Replace with your actual passphrase (or leave empty if none)
TREZOR_PASSPHRASE=YourActualPassphrase

# Replace with your claim address from Midnight Portal
CLAIM_ADDRESS=addr1qxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Standard Trezor derivation path
PAYMENT_PATH=m/1852'/1815'/0'/0/0

# Replace with your actual stake key checksum
STAKE_CHECKSUM=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

### 4. Run the Script
```bash
python midnight_claim.py
```

### 5. Convert Keys to CLI Format (REQUIRED)
The generated keys need to be converted to CLI format for Eternl compatibility:
```bash
python cli_convert.py
```

This creates the final `.skey` files that Eternl can import.

## 🔍 How to Get Required Information

### Getting Your Claim Address
1. Visit [Midnight Portal](https://midnight.network)
2. Connect your Trezor wallet
3. Navigate to token claim section
4. Copy the displayed claim address (starts with `addr1q`)

### Getting Your Stake Checksum
1. Open your Cardano wallet (Yoroi, Adalite, etc.)
2. Go to wallet settings or advanced view
3. Find "Stake Key" or "Reward Address"
4. Copy the stake key hash/checksum (64-character hex string)

### Getting Payment Path
- **Standard Trezor**: `m/1852'/1815'/0'/0/0`
- **Multi-account**: `m/1852'/1815'/1'/0/0` (account 1)
- **Custom**: Check your wallet's derivation settings

## 📊 Example Successful Output

When the script works correctly, you'll see output like this:

```
🎯 Midnight Claim - COMPREHENSIVE TEST
================================================================================
Testing multiple accounts, passphrase scenarios, and derivation methods
Saving all results to: /your/secure/folder/output
================================================================================

=== QUICK VERIFICATION ===
✅ Wallet creation successful
First address (current setup): addr1vexample123...
Target claim address:          addr1qexample456...

=== COMPREHENSIVE DERIVATION TEST ===
Target address: addr1qexample456789abcdef...
Expected stake checksum: 1234567890abcdef...

--- Testing current_passphrase ---
Account 0 payment-only: addr1vexample123...
Stake 0/0: 1234567890abcdef...
🔑 STAKE CHECKSUM MATCH! Scenario: current_passphrase
  Payment Account: 0, Stake Account: 0, Stake Index: 0
Complete address: addr1qexample456789abcdef...
🎯 PERFECT MATCH! Complete derivation found!

🎯 MATCH FOUND!
  Payment Path: m/1852'/1815'/0'/0/0
  Stake Path: m/1852'/1815'/0'/2/0
  Address Type: payment_stake

✅ Derivation successful!
Extracting private keys...

==========================================================================================
🎊 MIDNIGHT CLAIM KEYS SUCCESSFULLY GENERATED!
==========================================================================================

📁 KEYS SAVED TO: /your/secure/folder/output
🔑 Payment Key: midnight_payment_example_12345.skey
🔑 Stake Key: midnight_stake_example_12345.skey
📋 Instructions: MIDNIGHT_SUCCESS_example_12345.txt

✅ SUCCESS! Private keys extracted!
📂 Saved to: /your/secure/folder/output
📖 Read: MIDNIGHT_SUCCESS_example_12345.txt

🏆 CLAIM TEST SUCCESSFUL!
Your private keys are ready for Eternl import!
```

## 🌐 Eternl Import Process

### 1. Install Eternl Wallet
- Visit [eternl.io](https://eternl.io)
- Install browser extension
- Create account

### 2. Import CLI-Converted Keys to Eternl
**IMPORTANT: Only use the CLI-converted files from step 5 above**

1. Open Eternl → **"Add Wallet"**
2. Select **"Restore"** → **"Advanced"**
3. Choose **"Import from CLI signing key"**
4. **Upload Payment Key**: `midnight_payment_cli.skey` (CLI converted)
5. **Upload Staking Key**: `midnight_stake_cli.skey` (CLI converted)
6. **Skip DRep Key** (leave empty - not needed for claims)
7. **Name wallet**: "Midnight Claim"
8. **Create wallet**

### 3. Claim Your Tokens
1. Connect Eternl to Midnight Portal
2. Navigate to token claim section
3. Execute claim transaction
4. Confirm transaction in Eternl
5. Wait for confirmation

### 4. Secure Cleanup (CRITICAL!)
⚠️ **IMMEDIATELY after successful claiming:**
1. **Delete** all `.skey` files from your computer
2. **Delete** the Eternl wallet you created
3. **Transfer** claimed tokens to your NEW secure hardware wallet
4. **Delete** entire project folder
5. **Clear** browser cache/history
6. **Abandon** the OLD wallet completely

## 🛠️ Troubleshooting

### For Wallets WITHOUT Passphrase
If you don't use a passphrase on your Trezor:
```env
TREZOR_PASSPHRASE=
```
Leave it completely empty - the script will test this scenario automatically.

### Common Issues

**"No immediate match found"**
- ✅ Script will automatically test multiple scenarios
- ✅ Verify your seed phrase is exactly correct
- ✅ Try with empty passphrase if you're unsure

**"Wallet creation failed"**
- Check seed phrase format (12 or 24 words, space-separated)
- Verify no extra spaces or special characters
- Ensure passphrase encoding is correct

**"Eternl says 'Initialisiere acc#0'"**
- Make sure you used the CLI-converted keys (`*_cli.skey`)
- If still failing, try alternative wallets (Typhon, Nami)
- Contact Midnight support for alternative claim methods

**"Permission denied"**
- Run terminal/command prompt as administrator
- Ensure Python has write permissions to the folder

**"CLI conversion failed"**
- Make sure `midnight_claim.py` ran successfully first
- Check that the original `.skey` files exist
- Verify file permissions in the output directory

## 🔐 Security Best Practices

1. **Use offline computer** for key generation
2. **Create NEW wallet first** and transfer funds there
3. **Never share** seed phrases or private keys
4. **Delete all files** immediately after successful claim
5. **Use hardware wallet** for long-term storage
6. **Double-check** all addresses before sending transactions
7. **Abandon OLD wallet** after claiming is complete

## ⚠️ Important Notes

### Does This Work Without Passphrase?
**YES!** The script automatically tests both scenarios:
- With your provided passphrase
- With empty passphrase
- With various passphrase normalizations

### Seed Phrase Length Support
- **12-word seeds**: Fully supported
- **24-word seeds**: Fully supported
- Both are tested automatically

## 🔗 Cardano Node Setup (Required)

You need a **synced Cardano mainnet node** for address verification and network communication.

### Installation Options

#### Option 1: Daedalus Wallet (Easiest)
- Download from [daedaluswallet.io](https://daedaluswallet.io)
- Includes built-in Cardano node
- Automatically syncs mainnet
- No manual configuration needed

#### Option 2: Dedicated Cardano Node (Recommended for this script)

### Windows Setup

1. **Download Cardano Node:**
   - Visit: https://github.com/IntersectMBO/cardano-node/releases
   - Download latest Windows release
   - Extract to: `C:\Users\username\AppData\Roaming\Cardano`

2. **Download Configuration Files:**
   - Get `mainnet-topology.json` and `mainnet-config.yaml` from:
     https://github.com/input-output-hk/cardano-node/tree/master/configuration/cardano
   - Place them in your cardano-node folder

3. **Run Cardano Node:**
   ```cmd
   cardano-node.exe run ^
       --topology ./configuration/cardano/mainnet-topology.json ^
       --database-path ./state ^
       --port 3001 ^
       --config ./configuration/cardano/mainnet-config.yaml ^
       --socket-path \\.\pipe\cardano-node
   ```

4. **Set Environment Variable:**
   ```cmd
   set CARDANO_NODE_SOCKET_PATH=\\.\pipe\cardano-node
   ```

5. **Verify Setup:**
   ```cmd
   echo %CARDANO_NODE_SOCKET_PATH%
   cardano-cli query tip --mainnet
   ```

### Linux Setup

1. **Download and Extract:**
   ```bash
   wget https://github.com/IntersectMBO/cardano-node/releases/download/8.9.1/cardano-node-8.9.1-linux.tar.gz
   tar -zxvf cardano-node-8.9.1-linux.tar.gz
   ```

2. **Run Cardano Node:**
   ```bash
   chmod +x run_cardano_node.sh
   ./run_cardano_node.sh
   ```

3. **Set Environment Variable:**
   ```bash
   echo "export CARDANO_NODE_SOCKET_PATH=/home/username/Cardano/db/socket" >> ~/.bashrc
   source ~/.bashrc
   ```

4. **Verify Setup:**
   ```bash
   echo $CARDANO_NODE_SOCKET_PATH
   cardano-cli query tip --mainnet
   ```

### Successful Sync Verification

When properly synced, `cardano-cli query tip --mainnet` should return:
```json
{
    "block": 10241329,
    "epoch": 481,
    "era": "Babbage",
    "hash": "ac21826f9da1facad7634b1cf3d7d62d414238dc58fc871807136bb38dd63290",
    "slot": 122664226,
    "slotInEpoch": 235426,
    "slotsToEpochEnd": 196574,
    "syncProgress": "100.00"
}
```

**Important:** Wait for `"syncProgress": "100.00"` before running the claim script.

### Detailed Setup Tutorials
- **Windows:** https://docs.cardano.org/native-tokens/getting-started
- **Official Node Documentation:** https://developers.cardano.org/docs/get-started/running-cardano

## ✅ Tested Configuration

This tool has been successfully tested with the following setup:

### Hardware & Wallet:
- **OS**: Windows 11
- **Hardware Wallet**: Trezor Model T with passphrase protection
- **Cardano Node**: Fully synced mainnet node

### Software Environment:
- **Browser**: Brave Browser
- **Wallet Extension**: Eternl Wallet
- **Python**: 3.8+

### Test Results:
- ✅ **Seed phrase derivation**: Working correctly
- ✅ **Passphrase handling**: All scenarios tested successfully  
- ✅ **Key extraction**: Generated valid .skey files
- ✅ **Eternl import**: Keys imported without issues
- ✅ **Token claiming**: Successful Midnight token claim completed

*Your mileage may vary with different configurations, but this represents a confirmed working setup.*

## 💝 Support This Project

If this tool helped you successfully claim your Midnight tokens, consider sending a small tip to support development and maintenance:

### QR Codes for Easy Donations:

**ADA Address:** `addr1qxk3cq8emwuusdlas04yn0qf3xndd6ts6ta7l3kh4vphuhss0y3k3y7r4ztz6xy0xjysj4j9ksysnlhnp0stqdwwyusq9g5th3`

![ADA Donation QR Code](donation_qr_ada.png)

**BTC Address:** `bc1qkj9f592hlj3m26eukc54xruls6pdzqs70ly8a5`

![BTC Donation QR Code](donation_qr_btc.png)

*Tips help maintain this project and keep it updated for the community!*

## 🆘 Support

- **Script Issues**: Create GitHub issue with error details
- **Midnight Claims**: Contact Midnight support team
- **Eternl Problems**: Visit Eternl documentation
- **Cardano Questions**: Cardano community forums

## 📄 Disclaimer

- **This tool is provided as-is**
- **Authors not responsible for lost funds**
- **Always verify outputs independently**
- **Use only for legitimate token claims**
- **Delete all private keys after use**
- **This method exposes your seed phrase - use recommended security strategy**

---

**🌙 Successfully claim your Midnight tokens safely!**

*Remember: Security first - create new wallet, use old eligible address, delete everything after claiming!*