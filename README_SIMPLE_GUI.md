# Simple Step-by-Step GUI for MidnightClaimer

A minimal, intuitive slider-based GUI that guides you through the Midnight token claiming process without adding complexity to your existing tested scripts.

## ✨ Features

- **Step-by-step guidance** with visual progress slider
- **Minimal attack surface** - directly calls your existing tested scripts
- **No additional dependencies** - uses only built-in tkinter
- **Security-focused workflow** - enforces security checklist
- **Cross-platform** - works on Windows, macOS, and Linux

## 🚀 Quick Start

### Windows
Double-click `run_simple_gui.bat` or run:
```cmd
python simple_gui.py
```

### macOS/Linux
Run the shell script:
```bash
./run_simple_gui.sh
```

Or directly:
```bash
python3 simple_gui.py
```

## 📋 Step-by-Step Process

### Step 1: Welcome
- Introduction to the claiming process
- Security overview

### Step 2: Security Checklist
- Enforced security requirements
- Must check all items to proceed
- Ensures proper wallet separation

### Step 3: Choose Claim Type
- **Cardano**: For `addr1` addresses
- **Bitcoin**: For `1`, `3`, or `bc1` addresses
- Automatically selects the right script

### Step 4: Environment Setup
- **Option A**: Open folder and manually create `.env`
- **Option B**: Use built-in helper to create `.env` file
- Validates `.env` file exists before proceeding

### Step 5: Script Execution
- Runs your existing tested claim scripts
- **Cardano**: `cardano-claim/midnight_claim_cardano.py`
- **Bitcoin**: `bitcoin-claim/midnight_claim_bitcoin.py`
- Real-time output display
- No modifications to your scripts

### Step 6: Results & Next Steps
- Links to generated files
- Clear instructions for wallet import
- Security reminders for cleanup

## 🔒 Security Benefits

- **No code changes** to your tested scripts
- **Minimal GUI code** - just navigation and file operations
- **No network access** - purely local interface
- **No sensitive data storage** - everything handled by your scripts
- **Clear security workflow** - enforces best practices

## 📁 File Structure

```
MidnightClaimer/
├── simple_gui.py              # Main GUI application
├── run_simple_gui.bat         # Windows launcher
├── run_simple_gui.sh          # macOS/Linux launcher
├── README_SIMPLE_GUI.md       # This file
├── cardano-claim/
│   ├── midnight_claim_cardano.py    # Your existing Cardano script
│   └── .env.example_cardano         # Template
└── bitcoin-claim/
    ├── midnight_claim_bitcoin.py     # Your existing Bitcoin script
    └── .env.example_bitcoin          # Template
```

## 🎯 Design Philosophy

This GUI was designed with these principles:

1. **Reuse, don't replace** - Your scripts work fine, so we just guide users through them
2. **Minimal complexity** - Simple tkinter GUI with no external dependencies
3. **Security first** - Enforced security checks and clear warnings
4. **User-friendly** - Step-by-step process anyone can follow
5. **Cross-platform** - Works everywhere Python works

## 🔧 Requirements

- **Python 3.8+** (with tkinter support)
- **Your existing claim scripts** in their respective folders
- **Windows/macOS/Linux** with GUI support

### Installing tkinter (if needed):

**Ubuntu/Debian:**
```bash
sudo apt-get install python3-tk
```

**CentOS/RHEL:**
```bash
sudo yum install tkinter
```

**macOS:**
```bash
brew install python-tk
```

## 🤝 Usage Tips

1. **Always start fresh** - Don't skip the security checklist
2. **Use the helper** - The built-in .env creator is easier than manual editing
3. **Watch the output** - The script execution screen shows real-time progress
4. **Follow the steps** - The final screen has important cleanup instructions
5. **Open the folder** - Use the folder buttons to easily access files

## 🛠️ Troubleshooting

### GUI won't start
- Ensure Python 3.8+ is installed
- Ensure tkinter is available (`python -c "import tkinter"`)
- Run from the MidnightClaimer root directory

### Scripts not found
- Ensure you're running from the correct directory
- Check that `cardano-claim/` and `bitcoin-claim/` folders exist
- Verify your scripts are in the right locations

### .env creation fails
- Check folder permissions
- Ensure the target folder exists
- Try manual creation if helper fails

## 🔍 Behind the Scenes

The GUI simply:
- Guides you through the process step-by-step
- Helps you create the `.env` file your scripts need
- Runs your existing scripts with `subprocess`
- Shows you the output and results

It doesn't modify your scripts or add any attack surface - it's just a friendly interface for the tools you've already tested and trust.

## 💡 Why This Approach?

You mentioned wanting to "reuse our existing scripts and not need to add any additional code to increase the surface attack vector" - that's exactly what this does:

- **Zero changes** to your working scripts
- **Minimal new code** - just UI navigation
- **No crypto operations** in the GUI - your scripts handle everything
- **No network code** - purely local file operations
- **Simple dependencies** - just built-in tkinter

The result is a user-friendly interface that makes your existing tools accessible to anyone, while maintaining the security and reliability you've already achieved.