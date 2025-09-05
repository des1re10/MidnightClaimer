#!/usr/bin/env python3
"""
Main GUI Window for MidnightClaimer
Provides a user-friendly wizard interface for claiming Midnight tokens
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
from pathlib import Path
from typing import Optional, Dict
import threading
import queue
from PIL import Image, ImageTk

from ..services.cardano_service import CardanoService
from ..services.bitcoin_service import BitcoinService
from ..utils.security import SecurityManager, SecureEntry, SecureText, validate_seed_phrase_format, validate_address_format

logger = logging.getLogger(__name__)

class MidnightClaimerGUI:
    """Main GUI application for MidnightClaimer"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MidnightClaimer - Secure Token Claiming Tool")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        
        # Services
        self.cardano_service = CardanoService()
        self.bitcoin_service = BitcoinService()
        self.security_manager = SecurityManager()
        
        # State
        self.current_step = 0
        self.claim_type = None
        self.derivation_result = None
        self.progress_queue = queue.Queue()
        
        # Style
        self.setup_styles()
        
        # Ensure cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Create main interface
        self.create_widgets()
        
        # Show welcome screen
        self.show_welcome()
    
    def setup_styles(self):
        """Setup custom styles for the application"""
        style = ttk.Style()
        
        # Configure custom styles
        style.configure("Title.TLabel", font=("Arial", 16, "bold"))
        style.configure("Subtitle.TLabel", font=("Arial", 12))
        style.configure("Warning.TLabel", font=("Arial", 10), foreground="red")
        style.configure("Success.TLabel", font=("Arial", 10), foreground="green")
        style.configure("Big.TButton", font=("Arial", 12), padding=10)
    
    def create_widgets(self):
        """Create the main widget structure"""
        # Main container
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        
        # Header frame
        self.header_frame = ttk.Frame(self.main_frame)
        self.header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        self.header_frame.columnconfigure(1, weight=1)
        
        # Progress bar
        self.progress_var = tk.StringVar(value="Step 1 of 5: Welcome")
        self.progress_label = ttk.Label(self.header_frame, textvariable=self.progress_var, style="Subtitle.TLabel")
        self.progress_label.grid(row=0, column=0, sticky=tk.W)
        
        # Content frame (will hold different screens)
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1)
        
        # Button frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        self.button_frame.columnconfigure(1, weight=1)
        
        self.back_button = ttk.Button(self.button_frame, text="< Back", command=self.go_back)
        self.back_button.grid(row=0, column=0, padx=(0, 10))
        
        self.next_button = ttk.Button(self.button_frame, text="Next >", command=self.go_next, style="Big.TButton")
        self.next_button.grid(row=0, column=2, padx=(10, 0))
        
        self.cancel_button = ttk.Button(self.button_frame, text="Cancel", command=self.on_closing)
        self.cancel_button.grid(row=0, column=3, padx=(10, 0))
    
    def clear_content_frame(self):
        """Clear all widgets from content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_welcome(self):
        """Show welcome screen with security warnings"""
        self.clear_content_frame()
        self.current_step = 0
        self.progress_var.set("Step 1 of 5: Welcome & Security Warning")
        
        # Create scrollable frame
        canvas = tk.Canvas(self.content_frame)
        scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Title
        title_label = ttk.Label(scrollable_frame, text="🌙 Welcome to MidnightClaimer", style="Title.TLabel")
        title_label.pack(pady=(0, 20))
        
        # Warning section
        warning_frame = ttk.LabelFrame(scrollable_frame, text="⚠️ CRITICAL SECURITY WARNING", padding="15")
        warning_frame.pack(fill=tk.X, pady=(0, 20))
        
        warnings = [
            "This tool requires exposing your hardware wallet seed phrase",
            "NEVER use this tool on your primary wallet with funds",
            "ALWAYS create a NEW wallet first and transfer funds there",
            "Only use your OLD eligible addresses for claiming authorization",
            "Delete all generated files immediately after claiming",
            "Use only on secure, isolated computers"
        ]
        
        for warning in warnings:
            warning_label = ttk.Label(warning_frame, text=f"• {warning}", style="Warning.TLabel", wraplength=700)
            warning_label.pack(anchor=tk.W, pady=2)
        
        # Security checklist
        checklist_frame = ttk.LabelFrame(scrollable_frame, text="✅ Security Checklist - Complete BEFORE Proceeding", padding="15")
        checklist_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.checklist_vars = []
        checklist_items = [
            "I have created a NEW wallet with fresh seed phrase",
            "I have transferred ALL funds from my old wallet to the new wallet",
            "I understand my OLD wallet seed will be compromised by this process",
            "I will ONLY use my OLD wallet to prove eligibility for claiming",
            "I will NEVER receive funds on my OLD wallet addresses after this",
            "I am using a secure, isolated computer for this process"
        ]
        
        for item in checklist_items:
            var = tk.BooleanVar()
            self.checklist_vars.append(var)
            checkbox = ttk.Checkbutton(checklist_frame, text=item, variable=var, command=self.update_next_button)
            checkbox.pack(anchor=tk.W, pady=2)
        
        # Info section
        info_frame = ttk.LabelFrame(scrollable_frame, text="ℹ️ What This Tool Does", padding="15")
        info_frame.pack(fill=tk.X)
        
        info_text = """This tool extracts private keys from your Trezor seed phrase to enable claiming Midnight (NIGHT) tokens through software wallets. This bypasses known hardware wallet integration issues with the official Midnight Portal.

The tool supports both Cardano and Bitcoin address claims and uses comprehensive derivation testing to find the correct keys automatically."""
        
        info_label = ttk.Label(info_frame, text=info_text, wraplength=700)
        info_label.pack()
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Update buttons
        self.back_button.configure(state="disabled")
        self.update_next_button()
    
    def show_claim_type_selection(self):
        """Show claim type selection screen"""
        self.clear_content_frame()
        self.current_step = 1
        self.progress_var.set("Step 2 of 5: Choose Claim Type")
        
        title_label = ttk.Label(self.content_frame, text="Choose Your Claim Type", style="Title.TLabel")
        title_label.pack(pady=(0, 30))
        
        subtitle_label = ttk.Label(self.content_frame, 
                                   text="Select the type of address your Midnight eligibility is tied to:",
                                   style="Subtitle.TLabel")
        subtitle_label.pack(pady=(0, 30))
        
        # Claim type selection
        self.claim_type_var = tk.StringVar()
        
        # Cardano option
        cardano_frame = ttk.LabelFrame(self.content_frame, text="🔗 Cardano Address Claims", padding="20")
        cardano_frame.pack(fill=tk.X, pady=(0, 15))
        
        cardano_radio = ttk.Radiobutton(cardano_frame, text="My eligibility is tied to a Cardano address (starts with 'addr1')",
                                        variable=self.claim_type_var, value="cardano", command=self.update_next_button)
        cardano_radio.pack(anchor=tk.W)
        
        cardano_info = ttk.Label(cardano_frame, 
                                text="• Requires synced Cardano node\n• Uses Eternl wallet for importing\n• Generates .skey files",
                                style="Subtitle.TLabel")
        cardano_info.pack(anchor=tk.W, pady=(5, 0))
        
        # Bitcoin option
        bitcoin_frame = ttk.LabelFrame(self.content_frame, text="₿ Bitcoin Address Claims", padding="20")
        bitcoin_frame.pack(fill=tk.X)
        
        bitcoin_radio = ttk.Radiobutton(bitcoin_frame, text="My eligibility is tied to a Bitcoin address (starts with '1', '3', or 'bc1')",
                                        variable=self.claim_type_var, value="bitcoin", command=self.update_next_button)
        bitcoin_radio.pack(anchor=tk.W)
        
        bitcoin_info = ttk.Label(bitcoin_frame, 
                                text="• No blockchain node required\n• Uses Electrum, Sparrow, or other software wallets\n• Generates WIF private keys",
                                style="Subtitle.TLabel")
        bitcoin_info.pack(anchor=tk.W, pady=(5, 0))
        
        # Update buttons
        self.back_button.configure(state="normal")
        self.update_next_button()
    
    def show_seed_entry(self):
        """Show seed phrase and address entry screen"""
        self.clear_content_frame()
        self.current_step = 2
        self.progress_var.set("Step 3 of 5: Enter Wallet Information")
        
        title_label = ttk.Label(self.content_frame, text="Enter Your Wallet Information", style="Title.TLabel")
        title_label.pack(pady=(0, 20))
        
        # Create main container with scrolling
        canvas = tk.Canvas(self.content_frame)
        scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Seed phrase section
        seed_frame = ttk.LabelFrame(scrollable_frame, text="🔑 Trezor Seed Phrase", padding="15")
        seed_frame.pack(fill=tk.X, pady=(0, 15))
        
        seed_label = ttk.Label(seed_frame, text="Enter your 12 or 24 word seed phrase:")
        seed_label.pack(anchor=tk.W)
        
        self.seed_entry = SecureText(seed_frame, height=3, width=70)
        self.seed_entry.pack(fill=tk.X, pady=(5, 0))
        self.seed_entry.bind('<KeyRelease>', self.validate_input)
        
        # Register secure widget for cleanup
        self.security_manager.register_secure_widget(self.seed_entry)
        
        # Passphrase section
        passphrase_frame = ttk.LabelFrame(scrollable_frame, text="🔒 Passphrase (Optional)", padding="15")
        passphrase_frame.pack(fill=tk.X, pady=(0, 15))
        
        passphrase_label = ttk.Label(passphrase_frame, text="Enter your passphrase (leave empty if none):")
        passphrase_label.pack(anchor=tk.W)
        
        self.passphrase_entry = SecureEntry(passphrase_frame, width=70)
        self.passphrase_entry.pack(fill=tk.X, pady=(5, 0))
        self.passphrase_entry.bind('<KeyRelease>', self.validate_input)
        
        # Register secure widget for cleanup
        self.security_manager.register_secure_widget(self.passphrase_entry)
        
        # Address section
        address_frame = ttk.LabelFrame(scrollable_frame, text=f"📍 Eligible {self.claim_type.title()} Address", padding="15")
        address_frame.pack(fill=tk.X, pady=(0, 15))
        
        address_label = ttk.Label(address_frame, text=f"Enter your eligible {self.claim_type} address from the Midnight Portal:")
        address_label.pack(anchor=tk.W)
        
        self.address_entry = tk.Entry(address_frame, width=70)
        self.address_entry.pack(fill=tk.X, pady=(5, 0))
        self.address_entry.bind('<KeyRelease>', self.validate_input)
        
        # Additional fields for Cardano
        if self.claim_type == "cardano":
            stake_frame = ttk.LabelFrame(scrollable_frame, text="🎯 Stake Key Checksum", padding="15")
            stake_frame.pack(fill=tk.X, pady=(0, 15))
            
            stake_label = ttk.Label(stake_frame, text="Enter your stake key checksum (64-character hex):")
            stake_label.pack(anchor=tk.W)
            
            self.stake_entry = tk.Entry(stake_frame, width=70)
            self.stake_entry.pack(fill=tk.X, pady=(5, 0))
            self.stake_entry.bind('<KeyRelease>', self.validate_input)
        
        # Validation status
        self.validation_frame = ttk.Frame(scrollable_frame)
        self.validation_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.validation_label = ttk.Label(self.validation_frame, text="", style="Warning.TLabel")
        self.validation_label.pack()
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Update buttons
        self.back_button.configure(state="normal")
        self.update_next_button()
    
    def show_derivation_progress(self):
        """Show derivation progress screen"""
        self.clear_content_frame()
        self.current_step = 3
        self.progress_var.set("Step 4 of 5: Finding Your Keys")
        
        title_label = ttk.Label(self.content_frame, text="Finding Your Private Keys", style="Title.TLabel")
        title_label.pack(pady=(0, 30))
        
        info_label = ttk.Label(self.content_frame, 
                              text="Testing multiple derivation scenarios to find the correct private keys...",
                              style="Subtitle.TLabel")
        info_label.pack(pady=(0, 30))
        
        # Progress bar
        self.derivation_progress = ttk.Progressbar(self.content_frame, mode='determinate', length=400)
        self.derivation_progress.pack(pady=(0, 20))
        
        # Status label
        self.status_label = ttk.Label(self.content_frame, text="Initializing...", style="Subtitle.TLabel")
        self.status_label.pack()
        
        # Log area
        log_frame = ttk.LabelFrame(self.content_frame, text="Progress Log", padding="10")
        log_frame.pack(fill="both", expand=True, pady=(20, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED)
        self.log_text.pack(fill="both", expand=True)
        
        # Disable navigation buttons during processing
        self.back_button.configure(state="disabled")
        self.next_button.configure(state="disabled")
        
        # Start derivation in background thread
        self.start_derivation()
    
    def show_results(self):
        """Show results screen"""
        self.clear_content_frame()
        self.current_step = 4
        self.progress_var.set("Step 5 of 5: Success!")
        
        if self.derivation_result:
            self.show_success_screen()
        else:
            self.show_failure_screen()
    
    def show_success_screen(self):
        """Show success screen with key extraction results"""
        title_label = ttk.Label(self.content_frame, text="🎉 Success! Keys Found!", style="Title.TLabel")
        title_label.pack(pady=(0, 20))
        
        # Success info
        success_frame = ttk.LabelFrame(self.content_frame, text="✅ Derivation Successful", padding="15")
        success_frame.pack(fill=tk.X, pady=(0, 20))
        
        if self.claim_type == "cardano":
            info_text = f"""Payment Path: {self.derivation_result['payment_path']}
Stake Path: {self.derivation_result.get('stake_path', 'N/A')}
Address Type: {self.derivation_result['address_type']}
Scenario: {self.derivation_result['scenario_name']}"""
        else:
            info_text = f"""Derivation Path: {self.derivation_result['derivation_result']['derivation_path']}
Address Type: {self.derivation_result['address_type']}
Account: {self.derivation_result['account']}
Index: {self.derivation_result['address_index']}
Scenario: {self.derivation_result['scenario_name']}"""
        
        info_label = ttk.Label(success_frame, text=info_text, style="Subtitle.TLabel")
        info_label.pack(anchor=tk.W)
        
        # Next steps
        steps_frame = ttk.LabelFrame(self.content_frame, text="📋 Next Steps", padding="15")
        steps_frame.pack(fill=tk.X, pady=(0, 20))
        
        steps_text = """1. Click 'Extract Keys' to generate your private key files
2. Follow the instructions in the generated instruction file
3. Import keys to your software wallet
4. Connect to Midnight Portal and execute claim
5. IMMEDIATELY delete all private key files after claiming
6. Transfer claimed tokens to your NEW secure wallet"""
        
        steps_label = ttk.Label(steps_frame, text=steps_text, style="Subtitle.TLabel")
        steps_label.pack(anchor=tk.W)
        
        # Extract button
        self.extract_button = ttk.Button(self.content_frame, text="Extract Keys", 
                                        command=self.extract_keys, style="Big.TButton")
        self.extract_button.pack(pady=20)
        
        # Update navigation
        self.back_button.configure(state="disabled")
        self.next_button.configure(text="Finish", state="normal")
    
    def show_failure_screen(self):
        """Show failure screen with troubleshooting information"""
        title_label = ttk.Label(self.content_frame, text="❌ No Matching Keys Found", style="Title.TLabel")
        title_label.pack(pady=(0, 20))
        
        # Error info
        error_frame = ttk.LabelFrame(self.content_frame, text="🔍 Analysis", padding="15")
        error_frame.pack(fill=tk.X, pady=(0, 20))
        
        error_text = """No derivation scenario matched your provided information. This typically indicates:

• Seed phrase doesn't match your Trezor wallet
• Address is from a different wallet entirely
• Passphrase encoding issues
• Non-standard derivation paths"""
        
        error_label = ttk.Label(error_frame, text=error_text, style="Warning.TLabel")
        error_label.pack(anchor=tk.W)
        
        # Troubleshooting steps
        steps_frame = ttk.LabelFrame(self.content_frame, text="🛠️ Troubleshooting Steps", padding="15")
        steps_frame.pack(fill=tk.X, pady=(0, 20))
        
        steps_text = """1. Double-check your seed phrase against your Trezor
2. Try with an empty passphrase (many users think they have one when they don't)
3. Verify the eligible address is correct from the Midnight Portal
4. Ensure the address is from the same wallet as your seed phrase
5. Consider using hardware wallet's native export functionality"""
        
        steps_label = ttk.Label(steps_frame, text=steps_text, style="Subtitle.TLabel")
        steps_label.pack(anchor=tk.W)
        
        # Update navigation
        self.back_button.configure(state="normal")
        self.next_button.configure(text="Start Over", state="normal")
    
    def start_derivation(self):
        """Start the derivation process in a background thread"""
        def derivation_worker():
            try:
                seed_phrase = self.seed_entry.get().strip()
                passphrase = self.passphrase_entry.get()
                address = self.address_entry.get().strip()
                
                if self.claim_type == "cardano":
                    stake_checksum = self.stake_entry.get().strip()
                    result = self.cardano_service.test_derivation_comprehensive(
                        seed_phrase, passphrase, address, stake_checksum, self.progress_callback
                    )
                else:
                    address_type = self.bitcoin_service.detect_address_type(address)
                    result = self.bitcoin_service.test_derivation_comprehensive(
                        seed_phrase, passphrase, address, address_type, self.progress_callback
                    )
                
                self.derivation_result = result
                self.progress_queue.put(("COMPLETE", result))
                
            except Exception as e:
                logger.error(f"Derivation error: {e}")
                self.progress_queue.put(("ERROR", str(e)))
        
        # Start worker thread
        worker_thread = threading.Thread(target=derivation_worker)
        worker_thread.daemon = True
        worker_thread.start()
        
        # Start progress monitoring
        self.monitor_progress()
    
    def progress_callback(self, message: str, percentage: int):
        """Callback for progress updates from derivation services"""
        self.progress_queue.put(("PROGRESS", (message, percentage)))
    
    def monitor_progress(self):
        """Monitor progress queue and update UI"""
        try:
            while True:
                msg_type, data = self.progress_queue.get_nowait()
                
                if msg_type == "PROGRESS":
                    message, percentage = data
                    self.derivation_progress['value'] = percentage
                    self.status_label.configure(text=message)
                    self.log_text.configure(state=tk.NORMAL)
                    self.log_text.insert(tk.END, f"{message}\n")
                    self.log_text.configure(state=tk.DISABLED)
                    self.log_text.see(tk.END)
                    
                elif msg_type == "COMPLETE":
                    self.derivation_progress['value'] = 100
                    if data:
                        self.status_label.configure(text="✅ Keys found successfully!", foreground="green")
                    else:
                        self.status_label.configure(text="❌ No matching keys found", foreground="red")
                    
                    # Enable next button after brief delay
                    self.root.after(2000, lambda: self.next_button.configure(state="normal"))
                    return
                    
                elif msg_type == "ERROR":
                    self.status_label.configure(text=f"❌ Error: {data}", foreground="red")
                    self.next_button.configure(state="normal")
                    return
                    
        except queue.Empty:
            pass
        
        # Continue monitoring
        self.root.after(100, self.monitor_progress)
    
    def extract_keys(self):
        """Extract private keys and create instruction files"""
        try:
            # Create secure workspace
            workspace = self.security_manager.create_secure_workspace()
            
            if self.claim_type == "cardano":
                key_info = self.cardano_service.extract_keys(self.derivation_result, workspace)
                instruction_file = self.cardano_service.create_instructions_file(key_info, workspace)
                
                # Register files for cleanup
                self.security_manager.register_temp_file(Path(key_info['payment_key_file']))
                if key_info['stake_key_file']:
                    self.security_manager.register_temp_file(Path(key_info['stake_key_file']))
                    
            else:
                key_info = self.bitcoin_service.extract_private_key(self.derivation_result, workspace)
                instruction_file = self.bitcoin_service.create_instructions_file(key_info, workspace)
                
                # Register files for cleanup
                self.security_manager.register_temp_file(Path(key_info['wif_file']))
            
            self.security_manager.register_temp_file(Path(instruction_file))
            
            # Show success message
            messagebox.showinfo("Keys Extracted Successfully", 
                              f"Your private keys have been saved to:\n{workspace}\n\n"
                              f"Please read the instruction file:\n{Path(instruction_file).name}\n\n"
                              f"IMPORTANT: Delete all files immediately after claiming!")
            
            # Update button
            self.extract_button.configure(text="Keys Extracted ✓", state="disabled")
            
        except Exception as e:
            logger.error(f"Key extraction failed: {e}")
            messagebox.showerror("Extraction Failed", f"Failed to extract keys: {e}")
    
    def validate_input(self, event=None):
        """Validate current input and update UI accordingly"""
        if self.current_step != 2:
            return
        
        seed_phrase = self.seed_entry.get().strip()
        address = self.address_entry.get().strip()
        
        # Validate seed phrase
        if seed_phrase:
            seed_valid, seed_error = validate_seed_phrase_format(seed_phrase)
            if not seed_valid:
                self.validation_label.configure(text=f"Seed phrase: {seed_error}", foreground="red")
                self.next_button.configure(state="disabled")
                return
            
            # Check cryptographic validity
            service = self.cardano_service if self.claim_type == "cardano" else self.bitcoin_service
            if not service.validate_seed_phrase(seed_phrase):
                self.validation_label.configure(text="Seed phrase: Invalid mnemonic checksum", foreground="red")
                self.next_button.configure(state="disabled")
                return
        
        # Validate address
        if address:
            addr_valid, addr_error = validate_address_format(address, self.claim_type)
            if not addr_valid:
                self.validation_label.configure(text=f"Address: {addr_error}", foreground="red")
                self.next_button.configure(state="disabled")
                return
        
        # Validate stake checksum for Cardano
        if self.claim_type == "cardano" and hasattr(self, 'stake_entry'):
            stake_checksum = self.stake_entry.get().strip()
            if stake_checksum and len(stake_checksum) != 64:
                self.validation_label.configure(text="Stake checksum must be exactly 64 characters", foreground="red")
                self.next_button.configure(state="disabled")
                return
        
        # All validations passed
        if seed_phrase and address:
            if self.claim_type == "cardano":
                if hasattr(self, 'stake_entry') and self.stake_entry.get().strip():
                    self.validation_label.configure(text="✓ All inputs valid", foreground="green")
                    self.next_button.configure(state="normal")
                else:
                    self.validation_label.configure(text="Stake checksum required for Cardano claims", foreground="red")
                    self.next_button.configure(state="disabled")
            else:
                self.validation_label.configure(text="✓ All inputs valid", foreground="green")
                self.next_button.configure(state="normal")
        else:
            self.validation_label.configure(text="Please fill in all required fields", foreground="orange")
            self.next_button.configure(state="disabled")
    
    def update_next_button(self, event=None):
        """Update next button state based on current screen requirements"""
        if self.current_step == 0:
            # Welcome screen - check all checkboxes
            all_checked = all(var.get() for var in self.checklist_vars)
            self.next_button.configure(state="normal" if all_checked else "disabled")
            
        elif self.current_step == 1:
            # Claim type selection
            has_selection = bool(self.claim_type_var.get())
            self.next_button.configure(state="normal" if has_selection else "disabled")
            
        elif self.current_step == 2:
            # Input validation handled by validate_input
            self.validate_input()
    
    def go_back(self):
        """Navigate to previous step"""
        if self.current_step > 0:
            self.current_step -= 1
            
            if self.current_step == 0:
                self.show_welcome()
            elif self.current_step == 1:
                self.show_claim_type_selection()
            elif self.current_step == 2:
                self.show_seed_entry()
    
    def go_next(self):
        """Navigate to next step"""
        if self.current_step == 0:
            self.show_claim_type_selection()
        elif self.current_step == 1:
            self.claim_type = self.claim_type_var.get()
            self.show_seed_entry()
        elif self.current_step == 2:
            self.show_derivation_progress()
        elif self.current_step == 3:
            self.show_results()
        elif self.current_step == 4:
            # Finish or start over
            if self.next_button.cget('text') == "Start Over":
                self.restart_application()
            else:
                self.finish_application()
    
    def restart_application(self):
        """Restart the application"""
        self.security_manager.secure_cleanup(show_confirmation=False)
        self.derivation_result = None
        self.claim_type = None
        self.show_welcome()
    
    def finish_application(self):
        """Finish the application"""
        if messagebox.askyesno("Secure Cleanup", 
                              "Application complete!\n\n"
                              "Would you like to securely clean up all temporary files now?\n"
                              "(Recommended immediately after importing to your wallet)"):
            if self.security_manager.secure_cleanup():
                messagebox.showinfo("Cleanup Complete", "All temporary files have been securely deleted.")
        
        self.root.quit()
    
    def on_closing(self):
        """Handle application close"""
        if messagebox.askyesno("Exit Application", 
                              "Are you sure you want to exit?\n\n"
                              "Any temporary files will be securely cleaned up."):
            self.security_manager.secure_cleanup(show_confirmation=False)
            self.root.destroy()
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

def main():
    """Main entry point for GUI application"""
    app = MidnightClaimerGUI()
    app.run()

if __name__ == "__main__":
    main()