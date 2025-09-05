#!/usr/bin/env python3
"""
Tests for security utilities
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import tkinter as tk
import tempfile
import os
from pathlib import Path

from Src.utils.security import (
    SecurityManager, 
    validate_seed_phrase_format, 
    validate_address_format
)

class TestSecurityManager(unittest.TestCase):
    """Tests for SecurityManager"""
    
    def setUp(self):
        self.security_manager = SecurityManager()
    
    def test_create_secure_workspace(self):
        """Test secure workspace creation"""
        workspace = self.security_manager.create_secure_workspace()
        
        self.assertIsInstance(workspace, Path)
        self.assertTrue(workspace.exists())
        self.assertTrue(workspace.is_dir())
        
        # Check permissions (owner only)
        stat = workspace.stat()
        permissions = oct(stat.st_mode)[-3:]
        self.assertEqual(permissions, '700')
        
        # Cleanup
        self.security_manager.secure_cleanup(show_confirmation=False)
    
    def test_register_temp_file(self):
        """Test temporary file registration"""
        temp_file = Path("/tmp/test_file.txt")
        self.security_manager.register_temp_file(temp_file)
        
        self.assertIn(temp_file, self.security_manager.temp_files)
    
    def test_secure_cleanup(self):
        """Test secure cleanup process"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"sensitive data")
        
        # Register for cleanup
        self.security_manager.register_temp_file(temp_path)
        
        # Perform cleanup
        result = self.security_manager.secure_cleanup(show_confirmation=False)
        
        self.assertTrue(result)
        self.assertFalse(temp_path.exists())
        self.assertEqual(len(self.security_manager.temp_files), 0)

class TestValidationFunctions(unittest.TestCase):
    """Tests for validation utility functions"""
    
    def test_validate_seed_phrase_format(self):
        """Test seed phrase format validation"""
        # Valid cases
        valid_12 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        is_valid, error = validate_seed_phrase_format(valid_12)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        
        valid_24 = " ".join(["abandon"] * 23 + ["about"])
        is_valid, error = validate_seed_phrase_format(valid_24)
        self.assertTrue(is_valid)
        
        # Invalid cases
        # Empty phrase
        is_valid, error = validate_seed_phrase_format("")
        self.assertFalse(is_valid)
        self.assertIn("empty", error.lower())
        
        # Wrong word count
        is_valid, error = validate_seed_phrase_format("abandon abandon abandon")
        self.assertFalse(is_valid)
        self.assertIn("must be", error)
        
        # Non-alphabetic characters
        is_valid, error = validate_seed_phrase_format("abandon abandon123 abandon abandon abandon abandon abandon abandon abandon abandon abandon about")
        self.assertFalse(is_valid)
        self.assertIn("non-alphabetic", error)
        
        # Too short words
        is_valid, error = validate_seed_phrase_format("ab cd ef gh hi jk lm no pq rs tu vw")
        self.assertFalse(is_valid)
        self.assertIn("too short", error)
    
    def test_validate_address_format(self):
        """Test address format validation"""
        # Valid Cardano addresses
        is_valid, error = validate_address_format("addr1qxk3cq8emwuusdlas04yn0qf3xndd6ts6ta7l3kh4vphuhss0y3k3y7r4ztz6xy0xjysj4j9ksysnlhnp0stqdwwyusq9g5th3", "cardano")
        self.assertTrue(is_valid)
        
        is_valid, error = validate_address_format("Ae2tdPwUPEZ5uzkzh1o2DHECiUi3iugvnnKHRisPgRRP3CTF4KCMvy54Xd3", "cardano")
        self.assertTrue(is_valid)
        
        # Valid Bitcoin addresses
        is_valid, error = validate_address_format("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "bitcoin")
        self.assertTrue(is_valid)
        
        is_valid, error = validate_address_format("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", "bitcoin")
        self.assertTrue(is_valid)
        
        is_valid, error = validate_address_format("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", "bitcoin")
        self.assertTrue(is_valid)
        
        # Invalid cases
        # Empty address
        is_valid, error = validate_address_format("", "bitcoin")
        self.assertFalse(is_valid)
        self.assertIn("empty", error.lower())
        
        # Wrong format for type
        is_valid, error = validate_address_format("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "cardano")
        self.assertFalse(is_valid)
        self.assertIn("must start with", error)
        
        is_valid, error = validate_address_format("addr1test", "bitcoin")
        self.assertFalse(is_valid)
        self.assertIn("must start with", error)
        
        # Too short
        is_valid, error = validate_address_format("addr1test", "cardano")
        self.assertFalse(is_valid)
        self.assertIn("too short", error)

# GUI component tests (require tkinter)
@patch('tkinter.messagebox.askyesno', return_value=True)
@patch('tkinter.messagebox.showinfo')
class TestSecureWidgets(unittest.TestCase):
    """Tests for secure GUI widgets"""
    
    def setUp(self):
        # Only run GUI tests if tkinter is available
        try:
            self.root = tk.Tk()
            self.root.withdraw()  # Hide the window
        except tk.TclError:
            self.skipTest("Tkinter not available")
    
    def tearDown(self):
        if hasattr(self, 'root'):
            self.root.destroy()
    
    def test_secure_entry_creation(self, mock_showinfo, mock_askyesno):
        """Test SecureEntry widget creation and basic functionality"""
        from Src.utils.security import SecureEntry
        
        entry = SecureEntry(self.root)
        self.assertIsInstance(entry, tk.Entry)
        
        # Test secure content tracking
        entry.insert(0, "test_password")
        self.assertEqual(entry.get(), "test_password")
        
        # Test secure clear
        entry.secure_clear()
        self.assertEqual(entry.get(), "")
    
    def test_secure_text_creation(self, mock_showinfo, mock_askyesno):
        """Test SecureText widget creation and basic functionality"""
        from Src.utils.security import SecureText
        
        text = SecureText(self.root)
        self.assertIsInstance(text, tk.Text)
        
        # Test secure content tracking
        text.insert("1.0", "test seed phrase")
        # Simulate key release event to update tracking
        text._on_key_release(None)
        self.assertEqual(text.get("1.0", tk.END).strip(), "test seed phrase")
        
        # Test secure clear
        text.secure_clear()
        self.assertEqual(text.get("1.0", tk.END).strip(), "")

class TestIntegrationSecurity(unittest.TestCase):
    """Integration tests for security features"""
    
    def test_complete_secure_workflow(self):
        """Test complete secure workflow from creation to cleanup"""
        security_manager = SecurityManager()
        
        # Create workspace
        workspace = security_manager.create_secure_workspace()
        self.assertTrue(workspace.exists())
        
        # Create some temporary files
        temp_file1 = workspace / "test1.txt"
        temp_file2 = workspace / "test2.txt"
        
        with open(temp_file1, 'w') as f:
            f.write("sensitive data 1")
        with open(temp_file2, 'w') as f:
            f.write("sensitive data 2")
        
        # Register files
        security_manager.register_temp_file(temp_file1)
        security_manager.register_temp_file(temp_file2)
        
        # Verify files exist
        self.assertTrue(temp_file1.exists())
        self.assertTrue(temp_file2.exists())
        
        # Perform cleanup
        result = security_manager.secure_cleanup(show_confirmation=False)
        
        # Verify cleanup success
        self.assertTrue(result)
        self.assertFalse(temp_file1.exists())
        self.assertFalse(temp_file2.exists())
        self.assertFalse(workspace.exists())

if __name__ == '__main__':
    # Skip GUI tests if running in headless environment
    if 'DISPLAY' not in os.environ and os.name != 'nt':
        TestSecureWidgets = None
    
    unittest.main()