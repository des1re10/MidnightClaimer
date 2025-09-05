# 🌙 MidnightClaimer GUI - User-Friendly Token Claiming

**A graphical interface for claiming Midnight (NIGHT) tokens from Trezor wallets**

This GUI version makes the MidnightClaimer accessible to non-technical users while maintaining the same security model and comprehensive derivation testing as the CLI tools.

## ✨ Features

### 🎯 User-Friendly Interface
- **Step-by-step wizard** guides you through the entire process
- **Built-in validation** for seed phrases and addresses
- **Real-time progress updates** during key derivation
- **Clear security warnings** and safety checklists
- **Automatic cleanup** of sensitive files

### 🔒 Security Features
- **Secure memory handling** for sensitive data
- **Automatic file encryption** and secure deletion
- **Temporary workspace** with restricted permissions
- **Memory overwrites** to prevent data recovery
- **Guided cleanup process** after claiming

### 🚀 Technical Capabilities
- **Comprehensive derivation testing** (multiple accounts, passphrases, normalizations)
- **Support for both Cardano and Bitcoin** address claims
- **Auto-detection** of address types
- **Multiple passphrase scenarios** tested automatically
- **Detailed error diagnosis** and troubleshooting

## 📋 Requirements

### System Requirements
- **Python 3.8+** with tkinter support
- **4GB RAM minimum** (for derivation testing)
- **Secure computer** (preferably offline during key generation)

### Dependencies
Install the required packages:

```bash
pip install -r requirements_gui.txt
```

### Required Dependencies:
- `pycardano>=0.11.0` - Cardano cryptographic operations
- `bitcoinlib>=0.12.0` - Bitcoin key derivation
- `mnemonic>=0.20` - BIP39 mnemonic validation
- `Pillow>=10.0.0` - GUI image support

## 🚀 Quick Start

### 1. Launch the GUI

```bash
python run_gui.py
```

### 2. Follow the Wizard

The GUI will guide you through these steps:

1. **Security Warning** - Review warnings and complete safety checklist
2. **Choose Claim Type** - Select Cardano or Bitcoin based on your eligibility
3. **Enter Information** - Provide seed phrase, passphrase, and eligible address
4. **Key Derivation** - Watch as the tool finds your private keys
5. **Success** - Extract keys and follow instructions for wallet import

## 🎮 GUI Walkthrough

### Step 1: Welcome & Security Warning
- **Review all security warnings carefully**
- **Complete the safety checklist** (all items required)
- **Ensure you have a NEW wallet** with funds transferred

### Step 2: Choose Your Claim Type

**🔗 Cardano Address Claims**
- For addresses starting with `addr1`, `Ae2`, or `Ddz`
- Requires stake key checksum from your wallet
- Generates `.skey` files for Eternl import

**₿ Bitcoin Address Claims**
- For addresses starting with `1`, `3`, or `bc1`
- Auto-detects address type (Legacy, SegWit, Native SegWit)
- Generates WIF private keys for software wallet import

### Step 3: Enter Wallet Information

**Required Information:**
- **Trezor seed phrase** (12 or 24 words)
- **Passphrase** (leave empty if none)
- **Eligible address** from Midnight Portal
- **Stake checksum** (Cardano only - 64 hex characters)

**Built-in Validation:**
- ✅ Real-time mnemonic validation
- ✅ Address format checking
- ✅ Checksum verification
- ✅ Input completeness verification

### Step 4: Finding Your Keys

The GUI will test multiple scenarios automatically:
- **6 passphrase variations** (empty, trimmed, normalized, etc.)
- **Multiple accounts** (0-4 for payment, 0-2 for stake)
- **Address indices** (0-19 per account)
- **All combinations** tested systematically

**Progress Indicators:**
- Real-time progress bar
- Status messages
- Detailed activity log
- Success/failure notifications

### Step 5: Success & Key Extraction

**If Keys Found:**
- View derivation details
- Extract private key files
- Receive wallet import instructions
- Guided secure cleanup

**If No Match Found:**
- Detailed troubleshooting analysis
- Common issue explanations
- Step-by-step resolution guide
- Option to start over

## 🛠️ Advanced Features

### Security Manager
- **Secure workspace creation** with restricted permissions
- **Memory overwrite** for sensitive data
- **Multi-pass file deletion** (DoD 5220.22-M standard)
- **Widget cleanup** for GUI input fields
- **Automatic cleanup** on application exit

### Error Handling
- **Comprehensive error catching** with user-friendly messages
- **Detailed diagnostic reports** saved for troubleshooting
- **Graceful fallback** for all failure scenarios
- **Clear next steps** for resolution

### Progress Monitoring
- **Thread-safe progress updates** from background processes
- **Real-time status messages** with context
- **Detailed activity logging** for transparency
- **User cancellation support** at any stage

## 🔧 Troubleshooting

### Common Issues

**"Missing Dependencies" Error:**
```bash
pip install pycardano bitcoinlib mnemonic Pillow
```

**"No Display Available" (Linux):**
```bash
export DISPLAY=:0
python run_gui.py
```

**GUI Doesn't Start:**
- Ensure tkinter is installed: `python -m tkinter`
- Check Python version: `python --version` (needs 3.8+)
- Verify all dependencies: `pip list`

### No Keys Found

If the derivation process finds no matching keys:

1. **Verify seed phrase** - Compare with your Trezor wallet
2. **Try empty passphrase** - Many users think they have one when they don't
3. **Check address source** - Ensure it's from the correct wallet
4. **Verify eligibility** - Confirm address is actually eligible

### Application Won't Close

If the application becomes unresponsive:
- **Force quit** the GUI window
- **Check for temp files** in your system temp directory
- **Manual cleanup**: Look for `midnight_claim_*` files

## 🧪 Testing

Run the test suite to verify functionality:

```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/test_gui.py          # GUI tests
python -m pytest tests/test_services.py     # Service tests
python -m pytest tests/test_security.py     # Security tests

# Run with coverage
python -m pytest tests/ --cov=Src --cov-report=html
```

## 🔒 Security Considerations

### Before Using
- ✅ **Create NEW wallet** and transfer funds there
- ✅ **Use isolated computer** (preferably offline)
- ✅ **Verify no malware** on system
- ✅ **Close unnecessary applications**

### During Use
- ✅ **Don't screenshot** or record screen
- ✅ **Don't copy-paste** to unsecured locations
- ✅ **Monitor system resources** for anomalies
- ✅ **Complete process** without interruption

### After Use
- ✅ **Secure cleanup** immediately
- ✅ **Clear browser cache** if used
- ✅ **Restart computer** for complete cleanup
- ✅ **Transfer tokens** to NEW secure wallet

## 📞 Support

### Technical Issues
- **Script problems**: Create GitHub issue with error details
- **GUI crashes**: Include log file from project directory
- **Performance issues**: Monitor system resources during use

### Claiming Process
- **Portal issues**: Contact Midnight support team
- **Wallet problems**: Consult specific wallet documentation
- **Eligibility questions**: Check Midnight Portal help

## 🆚 GUI vs CLI Comparison

| Feature | GUI | CLI |
|---------|-----|-----|
| **Ease of Use** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Security** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Progress Visibility** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Error Handling** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Automation** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Customization** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**Choose GUI for:**
- First-time users
- Non-technical users
- Visual progress feedback
- Guided security process

**Choose CLI for:**
- Advanced users
- Batch processing
- Automation needs
- Minimal resource usage

## 📄 License

This GUI application is part of the MidnightClaimer project and follows the same license terms as the main project.

---

**Remember: Security first - create new wallet, use old address for claiming, delete everything after claiming!**