#!/usr/bin/env python3
"""
Security utilities for MidnightClaimer GUI
Enhanced version with better integration and validation
"""

import os
import logging
from pathlib import Path
from typing import List, Optional
import tkinter as tk
from tkinter import messagebox
import secrets
import tempfile
import shutil
import re
import hashlib

logger = logging.getLogger(__name__)

class SecureEntry(tk.Entry):
    """A secure text entry widget that can be securely cleared"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, show="*", **kwargs)
        self._secure_content = ""
        self._original_get = super().get
        self._original_insert = super().insert
        self._original_delete = super().delete
    
    def get(self):
        """Override get to return secure content"""
        return self._secure_content
    
    def insert(self, index, string):
        """Override insert to track secure content"""
        super().insert(index, string)
        # Update secure content tracking
        current = self._original_get()
        self._secure_content = current
    
    def delete(self, first, last=None):
        """Override delete to update secure content"""
        super().delete(first, last)
        current = self._original_get()
        self._secure_content = current
    
    def secure_clear(self):
        """
        Securely clear the entry widget
        Note: Python's garbage collector limitations mean sensitive strings 
        may persist in memory despite overwriting attempts
        """
        try:
            # Overwrite memory with random data
            if self._secure_content:
                random_data = ''.join(secrets.choice('0123456789abcdef') 
                                     for _ in range(len(self._secure_content)))
                self.delete(0, tk.END)
                self.insert(0, random_data)
                self.delete(0, tk.END)
            
            # Clear tracking variable
            self._secure_content = ""
            logger.debug("SecureEntry cleared")
            
        except Exception as e:
            logger.warning(f"SecureEntry clear failed: {e}")

class SecureText(tk.Text):
    """A secure text widget for seed phrases that can be securely cleared"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._secure_content = ""
        self.bind('<KeyRelease>', self._on_key_release)
        self.bind('<Button-1>', self._on_click)
        self.bind('<Control-v>', self._on_paste)
    
    def _on_key_release(self, event):
        """Update secure content tracking"""
        self._secure_content = super().get("1.0", tk.END).strip()
    
    def _on_click(self, event):
        """Update secure content on click"""
        self.after_idle(self._update_content)
    
    def _on_paste(self, event):
        """Update secure content on paste"""
        self.after_idle(self._update_content)
    
    def _update_content(self):
        """Update secure content"""
        self._secure_content = super().get("1.0", tk.END).strip()
    
    def get(self, start, end=None):
        """Override get to return secure content when requested"""
        if start == "1.0" and (end is None or end == tk.END):
            return self._secure_content
        return super().get(start, end)
    
    def secure_clear(self):
        """
        Securely clear the text widget
        Note: Python's garbage collector limitations mean sensitive strings 
        may persist in memory despite overwriting attempts
        """
        try:
            # Overwrite memory with random data
            if self._secure_content:
                # Generate random seed phrase of same length
                words = self._secure_content.split()
                random_words = [secrets.token_hex(4) for _ in words]
                random_phrase = ' '.join(random_words)
                
                self.delete("1.0", tk.END)
                self.insert("1.0", random_phrase)
                self.delete("1.0", tk.END)
            
            # Clear tracking variable
            self._secure_content = ""
            logger.debug("SecureText cleared")
            
        except Exception as e:
            logger.warning(f"SecureText clear failed: {e}")

class SecurityManager:
    """Enhanced security manager for the application"""
    
    def __init__(self):
        self.temp_files: List[Path] = []
        self.secure_widgets: List[tk.Widget] = []
        self.workspace_dir: Optional[Path] = None
        self._cleanup_performed = False
    
    def create_secure_workspace(self) -> Path:
        """Create a secure temporary workspace directory"""
        try:
            # Create temp directory with secure permissions
            # Use the same base path as the services for consistency
            base_workspace = Path(r"D:\workspace\VisualStudio\Midnight Claim")
            
            # Create unique subdirectory with timestamp and random component
            import time
            timestamp = int(time.time())
            random_suffix = secrets.token_hex(4)
            workspace_name = f"gui_session_{timestamp}_{random_suffix}"
            
            workspace = base_workspace / workspace_name
            workspace.mkdir(parents=True, exist_ok=True)
            
            # Set restrictive permissions (owner only)
            if os.name == 'nt':  # Windows
                # Windows doesn't support chmod the same way, use alternative approach
                import stat
                os.chmod(workspace, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
            else:  # Unix-like systems
                os.chmod(workspace, 0o700)
            
            self.workspace_dir = workspace
            logger.info(f"Created secure workspace: {workspace}")
            return workspace
            
        except Exception as e:
            logger.error(f"Failed to create secure workspace: {e}")
            raise
    
    def register_temp_file(self, file_path: Path):
        """Register a temporary file for cleanup"""
        if file_path not in self.temp_files:
            self.temp_files.append(file_path)
            logger.debug(f"Registered temp file: {file_path.name}")
    
    def register_secure_widget(self, widget: tk.Widget):
        """Register a secure widget for cleanup"""
        if widget not in self.secure_widgets:
            self.secure_widgets.append(widget)
            logger.debug(f"Registered secure widget: {type(widget).__name__}")
    
    def show_memory_warning(self) -> bool:
        """Show warning about Python memory management limitations"""
        warning_message = (
            "IMPORTANT SECURITY NOTICE\n\n"
            "Python's memory management has limitations:\n\n"
            "• Sensitive strings may persist in memory despite clearing attempts\n"
            "• Garbage collection timing is unpredictable\n"
            "• Memory pages may be swapped to disk\n\n"
            "SECURITY RECOMMENDATIONS:\n"
            "• Use this tool on an isolated, air-gapped computer\n"
            "• Restart the computer after claiming tokens\n"
            "• Consider using a live USB operating system\n"
            "• Never use this on a shared or public computer\n"
            "• Close all unnecessary applications before proceeding\n\n"
            "The tool implements multiple security layers:\n"
            "• Secure workspace with restricted permissions\n"
            "• Multi-pass file deletion\n"
            "• Memory overwrite attempts\n"
            "• Automatic cleanup on exit\n\n"
            "Do you understand and accept these limitations?"
        )
        
        return messagebox.askyesno("Memory Security Warning", warning_message)
    
    def get_cleanup_summary(self) -> str:
        """Get summary of items to be cleaned up"""
        summary_items = []
        
        if self.temp_files:
            summary_items.append(f"{len(self.temp_files)} temporary files")
        
        if self.workspace_dir and self.workspace_dir.exists():
            # Count files in workspace
            try:
                workspace_files = list(self.workspace_dir.rglob('*'))
                file_count = len([f for f in workspace_files if f.is_file()])
                if file_count > 0:
                    summary_items.append(f"workspace directory with {file_count} files")
                else:
                    summary_items.append("empty workspace directory")
            except:
                summary_items.append("workspace directory")
        
        if self.secure_widgets:
            summary_items.append(f"{len(self.secure_widgets)} secure input fields")
        
        return summary_items
    
    def secure_cleanup(self, show_confirmation: bool = True) -> bool:
        """
        Securely clean up all temporary files and sensitive data
        
        Args:
            show_confirmation: Whether to show confirmation dialog
            
        Returns:
            True if cleanup was successful
        """
        if self._cleanup_performed:
            logger.info("Cleanup already performed, skipping")
            return True
        
        try:
            cleanup_items = self.get_cleanup_summary()
            
            if not cleanup_items:
                logger.info("No items to clean up")
                self._cleanup_performed = True
                return True
            
            # Show confirmation if requested
            if show_confirmation:
                message = (f"About to securely delete:\n\n" +
                          "\n".join(f"• {item}" for item in cleanup_items) +
                          f"\n\nThis action cannot be undone. Continue?")
                
                if not messagebox.askyesno("Secure Cleanup", message):
                    return False
            
            cleanup_success = True
            
            # Clean secure widgets
            for widget in self.secure_widgets:
                try:
                    if hasattr(widget, 'secure_clear'):
                        widget.secure_clear()
                        logger.debug(f"Cleared secure widget: {type(widget).__name__}")
                except Exception as e:
                    logger.warning(f"Failed to clear secure widget: {e}")
                    cleanup_success = False
            
            # Securely delete temporary files
            deleted_files = 0
            for file_path in self.temp_files:
                try:
                    if file_path.exists():
                        self._secure_delete_file(file_path)
                        deleted_files += 1
                        logger.debug(f"Deleted temp file: {file_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")
                    cleanup_success = False
            
            # Remove workspace directory
            if self.workspace_dir and self.workspace_dir.exists():
                try:
                    # First, secure delete all files in workspace
                    for file_path in self.workspace_dir.rglob('*'):
                        if file_path.is_file():
                            try:
                                self._secure_delete_file(file_path)
                            except Exception as e:
                                logger.warning(f"Failed to secure delete {file_path}: {e}")
                    
                    # Then remove directory structure
                    shutil.rmtree(self.workspace_dir, ignore_errors=True)
                    logger.info(f"Deleted workspace directory: {self.workspace_dir}")
                except Exception as e:
                    logger.warning(f"Failed to delete workspace: {e}")
                    cleanup_success = False
            
            # Clear tracking lists
            self.temp_files.clear()
            self.secure_widgets.clear()
            self.workspace_dir = None
            self._cleanup_performed = True
            
            logger.info(f"Secure cleanup completed: {deleted_files} files deleted")
            
            if show_confirmation:
                if cleanup_success:
                    messagebox.showinfo("Cleanup Complete", 
                                       f"Successfully cleaned up {deleted_files} files and sensitive data.\n\n"
                                       f"SECURITY REMINDER:\nRestart your computer to clear any remaining traces from memory.")
                else:
                    messagebox.showwarning("Cleanup Partial", 
                                         f"Cleanup completed with some warnings. Check the log file for details.\n\n"
                                         f"SECURITY REMINDER:\nRestart your computer to clear any remaining traces from memory.")
            
            return cleanup_success
            
        except Exception as e:
            logger.error(f"Secure cleanup failed: {e}")
            if show_confirmation:
                messagebox.showerror("Cleanup Failed", 
                                   f"Failed to complete secure cleanup: {e}\n\n"
                                   f"Please manually delete files and restart your computer.")
            return False
    
    def _secure_delete_file(self, file_path: Path):
        """Securely delete a file by overwriting it multiple times"""
        try:
            if not file_path.exists():
                return
            
            # Get file size
            file_size = file_path.stat().st_size
            
            if file_size == 0:
                # Empty file, just delete
                os.remove(file_path)
                return
            
            # Overwrite file multiple times with different patterns
            with open(file_path, 'r+b') as f:
                # Pass 1: All zeros
                f.seek(0)
                f.write(b'\x00' * file_size)
                f.flush()
                os.fsync(f.fileno())
                
                # Pass 2: All ones
                f.seek(0)
                f.write(b'\xFF' * file_size)
                f.flush()
                os.fsync(f.fileno())
                
                # Pass 3: Random data
                f.seek(0)
                f.write(secrets.token_bytes(file_size))
                f.flush()
                os.fsync(f.fileno())
            
            # Finally delete the file
            os.remove(file_path)
            logger.debug(f"Securely deleted: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to securely delete {file_path}: {e}")
            # Try normal deletion as fallback
            try:
                os.remove(file_path)
                logger.debug(f"Fallback deleted: {file_path}")
            except:
                logger.error(f"Complete deletion failure: {file_path}")
                raise

def validate_seed_phrase_format(seed_phrase: str) -> tuple[bool, str]:
    """
    Validate seed phrase format without checking cryptographic validity
    
    Returns:
        (is_valid, error_message)
    """
    if not seed_phrase or not seed_phrase.strip():
        return False, "Seed phrase cannot be empty"
    
    words = seed_phrase.strip().split()
    
    if len(words) not in [12, 15, 18, 21, 24]:
        return False, f"Seed phrase must be 12, 15, 18, 21, or 24 words (found {len(words)})"
    
    # Check for obvious issues
    for i, word in enumerate(words, 1):
        if not word.isalpha():
            return False, f"Word {i} contains non-alphabetic characters: '{word}'"
        if len(word) < 3:
            return False, f"Word {i} is too short: '{word}'"
        if len(word) > 8:
            return False, f"Word {i} is too long: '{word}'"
    
    return True, ""

def validate_address_format(address: str, address_type: str) -> tuple[bool, str]:
    """
    Validate address format based on type
    
    Returns:
        (is_valid, error_message)
    """
    if not address or not address.strip():
        return False, "Address cannot be empty"
    
    address = address.strip()
    
    if address_type == "cardano":
        if not (address.startswith('addr1') or address.startswith('Ae2') or address.startswith('Ddz')):
            return False, "Cardano address must start with 'addr1', 'Ae2', or 'Ddz'"
        if len(address) < 50:
            return False, "Cardano address appears too short"
        if len(address) > 120:
            return False, "Cardano address appears too long"
    
    elif address_type == "bitcoin":
        if not (address.startswith('1') or address.startswith('3') or address.startswith('bc1')):
            return False, "Bitcoin address must start with '1', '3', or 'bc1'"
        if len(address) < 25:
            return False, "Bitcoin address appears too short"
        if len(address) > 65:
            return False, "Bitcoin address appears too long"
    
    return True, ""

def validate_stake_checksum(checksum: str) -> tuple[bool, str]:
    """
    Validate Cardano stake key checksum format
    
    Returns:
        (is_valid, error_message)
    """
    if not checksum or not checksum.strip():
        return False, "Stake checksum cannot be empty"
    
    checksum = checksum.strip()
    
    if len(checksum) != 64:
        return False, f"Stake checksum must be exactly 64 characters (found {len(checksum)})"
    
    if not re.match(r'^[0-9a-fA-F]{64}$', checksum):
        return False, "Stake checksum must contain only hexadecimal characters (0-9, a-f, A-F)"
    
    return True, ""

def validate_bitcoin_wif(wif_key: str) -> tuple[bool, str]:
    """
    Validate Bitcoin WIF private key format
    
    Returns:
        (is_valid, error_message)
    """
    if not wif_key or not wif_key.strip():
        return False, "WIF key cannot be empty"
    
    wif_key = wif_key.strip()
    
    # WIF keys should start with specific characters
    if not (wif_key.startswith('5') or wif_key.startswith('K') or wif_key.startswith('L')):
        return False, "WIF key must start with '5', 'K', or 'L'"
    
    # Basic length check
    if len(wif_key) < 51 or len(wif_key) > 52:
        return False, "WIF key has invalid length"
    
    # Additional validation with base58 if available
    try:
        import base58
        base58.b58decode_check(wif_key)
        return True, ""
    except ImportError:
        # base58 not available, basic validation only
        return True, ""
    except Exception:
        return False, "WIF key has invalid encoding"