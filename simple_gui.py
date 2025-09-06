#!/usr/bin/env python3
"""
Simple Step-by-Step Slider GUI for MidnightClaimer
Minimal attack surface - directly calls existing tested scripts
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import subprocess
import sys
import os
from pathlib import Path
import threading
import queue

class SimpleClaimerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MidnightClaimer - Simple Step-by-Step Guide")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # State
        self.current_step = 0
        self.total_steps = 6
        self.claim_type = None
        
        # Create GUI
        self.setup_gui()
        
        # Show first step
        self.show_step()
    
    def setup_gui(self):
        """Setup the main GUI layout"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Progress section
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        progress_frame.columnconfigure(1, weight=1)
        
        # Step counter
        self.step_label = ttk.Label(progress_frame, text="Step 1 of 6", font=("Arial", 12, "bold"))
        self.step_label.grid(row=0, column=0, sticky=tk.W)
        
        # Progress slider
        self.progress_slider = ttk.Scale(
            progress_frame, 
            from_=0, 
            to=self.total_steps-1, 
            orient=tk.HORIZONTAL,
            state='disabled',
            length=300
        )
        self.progress_slider.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(20, 20))
        
        # Progress percentage
        self.progress_percent = ttk.Label(progress_frame, text="0%", font=("Arial", 10))
        self.progress_percent.grid(row=0, column=2, sticky=tk.E)
        
        # Content area
        self.content_frame = ttk.Frame(main_frame)
        self.content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1)
        
        # Navigation buttons
        nav_frame = ttk.Frame(main_frame)
        nav_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        nav_frame.columnconfigure(1, weight=1)
        
        self.prev_button = ttk.Button(nav_frame, text="← Previous", command=self.prev_step)
        self.prev_button.grid(row=0, column=0)
        
        self.next_button = ttk.Button(nav_frame, text="Next →", command=self.next_step)
        self.next_button.grid(row=0, column=2)
        
        self.quit_button = ttk.Button(nav_frame, text="Quit", command=self.quit_app)
        self.quit_button.grid(row=0, column=3, padx=(10, 0))
        
    def clear_content(self):
        """Clear the content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def update_progress(self):
        """Update progress indicators"""
        self.step_label.config(text=f"Step {self.current_step + 1} of {self.total_steps}")
        self.progress_slider.set(self.current_step)
        percentage = int((self.current_step / (self.total_steps - 1)) * 100)
        self.progress_percent.config(text=f"{percentage}%")
        
        # Update button states
        self.prev_button.config(state="normal" if self.current_step > 0 else "disabled")
        self.next_button.config(state="normal" if self.current_step < self.total_steps - 1 else "disabled")
    
    def show_step(self):
        """Show the current step content"""
        self.clear_content()
        self.update_progress()
        
        if self.current_step == 0:
            self.show_welcome()
        elif self.current_step == 1:
            self.show_security_check()
        elif self.current_step == 2:
            self.show_claim_type()
        elif self.current_step == 3:
            self.show_env_setup()
        elif self.current_step == 4:
            self.show_script_execution()
        elif self.current_step == 5:
            self.show_completion()
    
    def show_welcome(self):
        """Step 1: Welcome screen"""
        title = ttk.Label(self.content_frame, text="🌙 Welcome to MidnightClaimer", 
                         font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, pady=(0, 20))
        
        info_text = """This simple tool helps you claim Midnight tokens by:
        
1. Guiding you through security setup
2. Helping you choose Cardano or Bitcoin claiming
3. Setting up your environment file
4. Running the tested claim scripts
5. Showing you the results

⚠️ SECURITY WARNING: This process will expose your seed phrase.
Only use OLD wallets that you've already moved funds away from."""
        
        info = ttk.Label(self.content_frame, text=info_text, font=("Arial", 11), justify=tk.LEFT)
        info.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Project location info
        project_path = Path(__file__).parent.absolute()
        path_info = ttk.Label(self.content_frame, 
                             text=f"Project Location: {project_path}", 
                             font=("Arial", 9), foreground="gray")
        path_info.grid(row=2, column=0, sticky=tk.W)
    
    def show_security_check(self):
        """Step 2: Security checklist"""
        title = ttk.Label(self.content_frame, text="🔒 Security Checklist", 
                         font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, pady=(0, 20))
        
        # Checklist frame
        checklist_frame = ttk.LabelFrame(self.content_frame, text="Required Before Proceeding", padding="15")
        checklist_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.checklist_vars = []
        checklist_items = [
            "✓ I have created a NEW wallet with fresh seed phrase",
            "✓ I have transferred ALL funds to the NEW wallet",
            "✓ My OLD wallet (for claiming) has NO remaining funds",
            "✓ I understand my OLD seed phrase will be exposed",
            "✓ I will NEVER receive funds on OLD wallet addresses again",
            "✓ I am using a secure, isolated computer"
        ]
        
        for item in checklist_items:
            var = tk.BooleanVar()
            self.checklist_vars.append(var)
            check = ttk.Checkbutton(checklist_frame, text=item, variable=var)
            check.grid(sticky=tk.W, pady=2)
        
        # Warning
        warning = ttk.Label(self.content_frame, 
                           text="⚠️ You cannot proceed until all items are checked",
                           font=("Arial", 10), foreground="red")
        warning.grid(row=2, column=0)
        
        # Override next button behavior for this step
        self.next_button.config(command=self.check_security_and_proceed)
    
    def check_security_and_proceed(self):
        """Check security checklist before proceeding"""
        if all(var.get() for var in self.checklist_vars):
            self.next_button.config(command=self.next_step)  # Restore normal behavior
            self.next_step()
        else:
            messagebox.showwarning("Security Check", 
                                 "Please check all security requirements before proceeding.")
    
    def show_claim_type(self):
        """Step 3: Choose claim type"""
        title = ttk.Label(self.content_frame, text="🎯 Choose Your Claim Type", 
                         font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, pady=(0, 20))
        
        info = ttk.Label(self.content_frame, 
                        text="Select based on your eligible address from the Midnight Portal:",
                        font=("Arial", 11))
        info.grid(row=1, column=0, pady=(0, 20))
        
        # Claim type selection
        self.claim_var = tk.StringVar(value="")
        
        # Cardano option
        cardano_frame = ttk.LabelFrame(self.content_frame, text="Cardano Claims", padding="15")
        cardano_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        cardano_radio = ttk.Radiobutton(cardano_frame, 
                                       text="My eligible address starts with 'addr1' (Cardano)",
                                       variable=self.claim_var, value="cardano")
        cardano_radio.grid(row=0, column=0, sticky=tk.W)
        
        cardano_info = ttk.Label(cardano_frame, 
                                text="• Uses cardano-claim/midnight_claim_cardano.py\n• Requires Cardano node sync",
                                font=("Arial", 9), foreground="gray")
        cardano_info.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Bitcoin option
        bitcoin_frame = ttk.LabelFrame(self.content_frame, text="Bitcoin Claims", padding="15")
        bitcoin_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        bitcoin_radio = ttk.Radiobutton(bitcoin_frame, 
                                       text="My eligible address starts with '1', '3', or 'bc1' (Bitcoin)",
                                       variable=self.claim_var, value="bitcoin")
        bitcoin_radio.grid(row=0, column=0, sticky=tk.W)
        
        bitcoin_info = ttk.Label(bitcoin_frame, 
                                text="• Uses bitcoin-claim/midnight_claim_bitcoin.py\n• No blockchain sync required",
                                font=("Arial", 9), foreground="gray")
        bitcoin_info.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Override next button behavior
        self.next_button.config(command=self.check_claim_type_and_proceed)
    
    def check_claim_type_and_proceed(self):
        """Check claim type selection before proceeding"""
        if self.claim_var.get():
            self.claim_type = self.claim_var.get()
            self.next_button.config(command=self.next_step)  # Restore normal behavior
            self.next_step()
        else:
            messagebox.showwarning("Selection Required", 
                                 "Please select your claim type before proceeding.")
    
    def show_env_setup(self):
        """Step 4: Environment file setup"""
        title = ttk.Label(self.content_frame, text="⚙️ Setup Environment File", 
                         font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, pady=(0, 20))
        
        # Instructions
        claim_folder = f"{self.claim_type}-claim"
        env_file = f".env.example_{self.claim_type}"
        
        instructions = f"""We need to create your .env file with your wallet information.
        
1. Open the {claim_folder} folder
2. Copy {env_file} to .env
3. Edit .env with your information:
   • Your Trezor seed phrase
   • Your passphrase (if any)  
   • Your eligible address
   {'   • Your stake checksum (for Cardano)' if self.claim_type == 'cardano' else ''}

Below you can either open the folder or let this tool help you create the .env file."""
        
        info = ttk.Label(self.content_frame, text=instructions, font=("Arial", 11), justify=tk.LEFT)
        info.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Buttons frame
        button_frame = ttk.Frame(self.content_frame)
        button_frame.grid(row=2, column=0, pady=(0, 20))
        
        # Open folder button
        open_btn = ttk.Button(button_frame, text=f"📁 Open {claim_folder} folder", 
                             command=self.open_claim_folder)
        open_btn.grid(row=0, column=0, padx=(0, 10))
        
        # Helper button
        helper_btn = ttk.Button(button_frame, text="✏️ Create .env file helper", 
                               command=self.show_env_helper)
        helper_btn.grid(row=0, column=1)
        
        # Status
        self.env_status = ttk.Label(self.content_frame, text="", font=("Arial", 10))
        self.env_status.grid(row=3, column=0)
        
        # Check button
        check_btn = ttk.Button(self.content_frame, text="🔍 Check if .env file exists", 
                              command=self.check_env_file)
        check_btn.grid(row=4, column=0, pady=(10, 0))
    
    def open_claim_folder(self):
        """Open the claim folder"""
        try:
            folder_path = Path(__file__).parent / f"{self.claim_type}-claim"
            if folder_path.exists():
                if sys.platform == "win32":
                    os.startfile(folder_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(folder_path)])
                else:
                    subprocess.run(["xdg-open", str(folder_path)])
            else:
                messagebox.showerror("Folder Not Found", f"The {self.claim_type}-claim folder was not found!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")
    
    def show_env_helper(self):
        """Show environment file creation helper"""
        helper_window = tk.Toplevel(self.root)
        helper_window.title("Environment File Helper")
        helper_window.geometry("600x500")
        helper_window.grab_set()
        
        # Title
        title = ttk.Label(helper_window, text=f"Create .env file for {self.claim_type.title()} claiming", 
                         font=("Arial", 14, "bold"))
        title.pack(pady=(10, 20))
        
        # Form frame
        form_frame = ttk.Frame(helper_window, padding="20")
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Seed phrase
        ttk.Label(form_frame, text="Trezor Seed Phrase:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        seed_entry = tk.Text(form_frame, height=3, width=60)
        seed_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Passphrase
        ttk.Label(form_frame, text="Passphrase (leave empty if none):").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        passphrase_entry = ttk.Entry(form_frame, width=60, show="*")
        passphrase_entry.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Address
        ttk.Label(form_frame, text=f"Eligible {self.claim_type.title()} Address:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        address_entry = ttk.Entry(form_frame, width=60)
        address_entry.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Cardano-specific
        stake_entry = None
        if self.claim_type == "cardano":
            ttk.Label(form_frame, text="Stake Key Checksum:").grid(row=6, column=0, sticky=tk.W, pady=(0, 5))
            stake_entry = ttk.Entry(form_frame, width=60)
            stake_entry.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Buttons
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=8, column=0, columnspan=2, pady=(20, 0))
        
        def save_env():
            try:
                # Get values
                seed = seed_entry.get("1.0", tk.END).strip()
                passphrase = passphrase_entry.get()
                address = address_entry.get()
                
                if not seed or not address:
                    messagebox.showerror("Missing Information", "Seed phrase and address are required!")
                    return
                
                # Create .env content
                env_content = f"TREZOR_SEED_PHRASE={seed}\nTREZOR_PASSPHRASE={passphrase}\n"
                
                if self.claim_type == "cardano":
                    stake = stake_entry.get() if stake_entry else ""
                    env_content += f"CLAIM_ADDRESS={address}\nSTAKE_CHECKSUM={stake}\n"
                else:
                    env_content += f"BITCOIN_CLAIM_ADDRESS={address}\n"
                
                # Write file
                env_path = Path(__file__).parent / f"{self.claim_type}-claim" / ".env"
                with open(env_path, 'w') as f:
                    f.write(env_content)
                
                messagebox.showinfo("Success", f".env file created successfully!\n\nLocation: {env_path}")
                helper_window.destroy()
                self.check_env_file()  # Update status
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create .env file: {e}")
        
        ttk.Button(button_frame, text="Save .env File", command=save_env).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=helper_window.destroy).pack(side=tk.LEFT)
    
    def check_env_file(self):
        """Check if .env file exists and is valid"""
        env_path = Path(__file__).parent / f"{self.claim_type}-claim" / ".env"
        
        if env_path.exists():
            self.env_status.config(text="✅ .env file found!", foreground="green")
            self.next_button.config(state="normal")
        else:
            self.env_status.config(text="❌ .env file not found. Please create it first.", foreground="red")
            self.next_button.config(state="disabled")
    
    def show_script_execution(self):
        """Step 5: Run the claim script"""
        title = ttk.Label(self.content_frame, text="🚀 Run Claim Script", 
                         font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, pady=(0, 20))
        
        info = ttk.Label(self.content_frame, 
                        text=f"Ready to run the {self.claim_type} claim script. This will find your private keys.",
                        font=("Arial", 11))
        info.grid(row=1, column=0, pady=(0, 20))
        
        # Script info
        script_name = f"midnight_claim_{self.claim_type}.py"
        script_path = Path(__file__).parent / f"{self.claim_type}-claim" / script_name
        
        script_info = ttk.Label(self.content_frame, 
                               text=f"Script: {script_name}\nLocation: {script_path}",
                               font=("Arial", 9), foreground="gray")
        script_info.grid(row=2, column=0, pady=(0, 20))
        
        # Run button
        self.run_button = ttk.Button(self.content_frame, text=f"▶️ Run {script_name}", 
                                    command=self.run_claim_script, 
                                    style="Accent.TButton")
        self.run_button.grid(row=3, column=0, pady=(0, 20))
        
        # Output area
        output_frame = ttk.LabelFrame(self.content_frame, text="Script Output", padding="10")
        output_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=15, state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # Status
        self.script_status = ttk.Label(self.content_frame, text="", font=("Arial", 10))
        self.script_status.grid(row=5, column=0)
        
        # Configure grid weights
        self.content_frame.rowconfigure(4, weight=1)
    
    def run_claim_script(self):
        """Run the claim script in a separate thread"""
        self.run_button.config(state="disabled", text="⏳ Running...")
        self.script_status.config(text="Running script...", foreground="blue")
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        def run_script():
            try:
                script_path = Path(__file__).parent / f"{self.claim_type}-claim" / f"midnight_claim_{self.claim_type}.py"
                
                # Run the script
                process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    cwd=script_path.parent,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Read output line by line
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    
                    # Update UI in main thread
                    self.root.after(0, lambda l=line: self.append_output(l))
                
                # Wait for completion
                return_code = process.wait()
                
                # Update UI with final status
                if return_code == 0:
                    self.root.after(0, lambda: self.script_completed(True))
                else:
                    self.root.after(0, lambda: self.script_completed(False))
                    
            except Exception as e:
                self.root.after(0, lambda: self.script_error(str(e)))
        
        # Start in background thread
        thread = threading.Thread(target=run_script)
        thread.daemon = True
        thread.start()
    
    def append_output(self, text):
        """Append text to output area"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)
    
    def script_completed(self, success):
        """Handle script completion"""
        if success:
            self.script_status.config(text="✅ Script completed successfully!", foreground="green")
            self.next_button.config(state="normal")
        else:
            self.script_status.config(text="❌ Script completed with errors", foreground="red")
            
        self.run_button.config(state="normal", text=f"▶️ Run midnight_claim_{self.claim_type}.py")
    
    def script_error(self, error):
        """Handle script error"""
        self.script_status.config(text=f"❌ Error: {error}", foreground="red")
        self.append_output(f"\n\nError: {error}\n")
        self.run_button.config(state="normal", text=f"▶️ Run midnight_claim_{self.claim_type}.py")
    
    def show_completion(self):
        """Step 6: Completion and next steps"""
        title = ttk.Label(self.content_frame, text="🎉 Claiming Process Complete!", 
                         font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, pady=(0, 20))
        
        # Results folder
        results_folder = Path(__file__).parent / f"{self.claim_type}-claim"
        
        info_text = f"""Your claim script has finished running!
        
Check the {self.claim_type}-claim folder for:
• Private key files (.skey for Cardano, .wif for Bitcoin)
• Success/instruction files
• Diagnostic files (if there were issues)

NEXT STEPS:
1. Open the {self.claim_type}-claim folder
2. Look for SUCCESS files with instructions
3. Import the private keys to your software wallet
4. Execute your claim on the Midnight Portal
5. IMMEDIATELY delete all private key files
6. Transfer claimed tokens to your NEW secure wallet
7. Restart your computer to clear memory"""
        
        info = ttk.Label(self.content_frame, text=info_text, font=("Arial", 11), justify=tk.LEFT)
        info.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Open folder button
        open_btn = ttk.Button(self.content_frame, text=f"📁 Open {self.claim_type}-claim folder", 
                             command=self.open_claim_folder)
        open_btn.grid(row=2, column=0, pady=(0, 20))
        
        # Security reminder
        security_frame = ttk.LabelFrame(self.content_frame, text="🔒 CRITICAL SECURITY REMINDER", padding="15")
        security_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        security_text = """⚠️ Your OLD wallet seed phrase has been exposed during this process!

NEVER use your OLD wallet addresses to receive funds again!
DELETE all generated private key files immediately after claiming!
RESTART your computer after claiming to clear memory!
ONLY send claimed tokens to your NEW secure wallet!"""
        
        security_label = ttk.Label(security_frame, text=security_text, 
                                  font=("Arial", 10, "bold"), foreground="red", justify=tk.LEFT)
        security_label.pack(anchor=tk.W)
        
        # Update buttons
        self.next_button.config(text="🔄 Start Over", command=self.restart_process)
    
    def restart_process(self):
        """Restart the process from the beginning"""
        self.current_step = 0
        self.claim_type = None
        self.next_button.config(text="Next →", command=self.next_step)
        self.show_step()
    
    def prev_step(self):
        """Go to previous step"""
        if self.current_step > 0:
            self.current_step -= 1
            # Reset button behaviors
            self.next_button.config(command=self.next_step, state="normal", text="Next →")
            self.show_step()
    
    def next_step(self):
        """Go to next step"""
        if self.current_step < self.total_steps - 1:
            self.current_step += 1
            self.show_step()
    
    def quit_app(self):
        """Quit the application"""
        if messagebox.askyesno("Quit", "Are you sure you want to quit?"):
            self.root.destroy()
    
    def run(self):
        """Start the GUI"""
        self.root.mainloop()

def main():
    """Main entry point"""
    print("🌙 MidnightClaimer - Simple Step-by-Step GUI")
    print("=" * 50)
    
    # Ensure we're running from the script's directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    print(f"📁 Working directory: {script_dir}")
    
    # Check if we're in the right directory
    if not Path("cardano-claim").exists() or not Path("bitcoin-claim").exists():
        print("❌ Error: This GUI must be run from the MidnightClaimer root directory")
        print("Please navigate to the directory containing 'cardano-claim' and 'bitcoin-claim' folders")
        print(f"Current directory: {Path.cwd()}")
        messagebox.showerror("Directory Error", 
                           "This GUI must be run from the MidnightClaimer root directory.\n\n"
                           f"Current: {Path.cwd()}\n"
                           "Expected: Directory containing 'cardano-claim' and 'bitcoin-claim' folders")
        return
    
    print("✅ Required folders found")
    print("✅ Starting simple GUI...")
    
    try:
        app = SimpleClaimerGUI()
        app.run()
    except Exception as e:
        print(f"❌ Error starting GUI: {e}")
        messagebox.showerror("GUI Error", f"Failed to start GUI: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()