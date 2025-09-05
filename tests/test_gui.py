#!/usr/bin/env python3
"""
Tests for GUI components
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import tkinter as tk
import os
import sys

# Mock heavy dependencies for testing
mock_modules = {
    'pycardano': MagicMock(),
    'pycardano.HDWallet': MagicMock(),
    'pycardano.PaymentVerificationKey': MagicMock(),
    'pycardano.Address': MagicMock(),
    'pycardano.Network': MagicMock(),
    'pycardano.key': MagicMock(),
    'bitcoinlib': MagicMock(),
    'bitcoinlib.keys': MagicMock(),
    'bitcoinlib.wallets': MagicMock(),
    'mnemonic': MagicMock(),
    'PIL': MagicMock(),
    'PIL.Image': MagicMock(),
    'PIL.ImageTk': MagicMock(),
}

with patch.dict('sys.modules', mock_modules):
    from Src.gui.main_window import MidnightClaimerGUI

class TestMidnightClaimerGUI(unittest.TestCase):
    """Tests for main GUI application"""
    
    def setUp(self):
        # Only run GUI tests if tkinter is available
        try:
            # Mock the services to avoid dependency issues
            with patch('Src.gui.main_window.CardanoService'):
                with patch('Src.gui.main_window.BitcoinService'):
                    with patch('Src.gui.main_window.SecurityManager'):
                        self.app = MidnightClaimerGUI()
                        self.app.root.withdraw()  # Hide the window for testing
        except tk.TclError:
            self.skipTest("Tkinter not available")
    
    def tearDown(self):
        if hasattr(self, 'app'):
            self.app.root.destroy()
    
    def test_application_initialization(self):
        """Test application initializes correctly"""
        self.assertIsNotNone(self.app.root)
        self.assertEqual(self.app.current_step, 0)
        self.assertIsNone(self.app.claim_type)
        self.assertIsNone(self.app.derivation_result)
    
    def test_welcome_screen(self):
        """Test welcome screen display"""
        self.app.show_welcome()
        
        self.assertEqual(self.app.current_step, 0)
        self.assertEqual(self.app.progress_var.get(), "Step 1 of 5: Welcome & Security Warning")
        
        # Check that checklist variables are created
        self.assertTrue(hasattr(self.app, 'checklist_vars'))
        self.assertEqual(len(self.app.checklist_vars), 6)
    
    def test_claim_type_selection(self):
        """Test claim type selection screen"""
        self.app.show_claim_type_selection()
        
        self.assertEqual(self.app.current_step, 1)
        self.assertEqual(self.app.progress_var.get(), "Step 2 of 5: Choose Claim Type")
        
        # Check that claim type variable is created
        self.assertTrue(hasattr(self.app, 'claim_type_var'))
    
    def test_seed_entry_screen_cardano(self):
        """Test seed entry screen for Cardano"""
        self.app.claim_type = "cardano"
        self.app.show_seed_entry()
        
        self.assertEqual(self.app.current_step, 2)
        self.assertEqual(self.app.progress_var.get(), "Step 3 of 5: Enter Wallet Information")
        
        # Check that input widgets are created
        self.assertTrue(hasattr(self.app, 'seed_entry'))
        self.assertTrue(hasattr(self.app, 'passphrase_entry'))
        self.assertTrue(hasattr(self.app, 'address_entry'))
        self.assertTrue(hasattr(self.app, 'stake_entry'))  # Cardano specific
    
    def test_seed_entry_screen_bitcoin(self):
        """Test seed entry screen for Bitcoin"""
        self.app.claim_type = "bitcoin"
        self.app.show_seed_entry()
        
        self.assertEqual(self.app.current_step, 2)
        
        # Check that input widgets are created (no stake entry for Bitcoin)
        self.assertTrue(hasattr(self.app, 'seed_entry'))
        self.assertTrue(hasattr(self.app, 'passphrase_entry'))
        self.assertTrue(hasattr(self.app, 'address_entry'))
        self.assertFalse(hasattr(self.app, 'stake_entry'))
    
    def test_navigation_buttons(self):
        """Test navigation button states"""
        # Welcome screen - should have disabled back and next buttons initially
        self.app.show_welcome()
        self.assertEqual(self.app.back_button.cget('state'), 'disabled')
        self.assertEqual(self.app.next_button.cget('state'), 'disabled')
        
        # Simulate all checkboxes checked
        for var in self.app.checklist_vars:
            var.set(True)
        self.app.update_next_button()
        self.assertEqual(self.app.next_button.cget('state'), 'normal')
    
    def test_input_validation(self):
        """Test input validation functionality"""
        self.app.claim_type = "bitcoin"
        self.app.show_seed_entry()
        
        # Mock secure widgets
        self.app.seed_entry = Mock()
        self.app.passphrase_entry = Mock()
        self.app.address_entry = Mock()
        
        # Test empty inputs
        self.app.seed_entry.get.return_value = ""
        self.app.passphrase_entry.get.return_value = ""
        self.app.address_entry.get.return_value = ""
        
        self.app.validate_input()
        # Should be disabled when inputs are empty
        self.assertEqual(self.app.next_button.cget('state'), 'disabled')
        
        # Test valid inputs
        self.app.seed_entry.get.return_value = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        self.app.address_entry.get.return_value = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        
        with patch('Src.gui.main_window.validate_seed_phrase_format', return_value=(True, "")):
            with patch('Src.gui.main_window.validate_address_format', return_value=(True, "")):
                with patch.object(self.app.bitcoin_service, 'validate_seed_phrase', return_value=True):
                    self.app.validate_input()
                    self.assertEqual(self.app.next_button.cget('state'), 'normal')
    
    def test_progress_callback(self):
        """Test progress callback functionality"""
        self.app.progress_callback("Test message", 50)
        
        # Check that message was queued
        try:
            msg_type, data = self.app.progress_queue.get_nowait()
            self.assertEqual(msg_type, "PROGRESS")
            self.assertEqual(data, ("Test message", 50))
        except:
            self.fail("Progress message not queued properly")
    
    def test_security_manager_integration(self):
        """Test security manager integration"""
        # Test that security manager is properly initialized
        self.assertIsNotNone(self.app.security_manager)
        
        # Test widget registration would work
        mock_widget = Mock()
        mock_widget.secure_clear = Mock()
        
        self.app.security_manager.register_secure_widget(mock_widget)
        
        # Verify widget was registered
        self.assertIn(mock_widget, self.app.security_manager.secure_widgets)

class TestGUIUtilities(unittest.TestCase):
    """Tests for GUI utility functions"""
    
    def test_step_progression(self):
        """Test step progression logic"""
        try:
            with patch('Src.gui.main_window.CardanoService'):
                with patch('Src.gui.main_window.BitcoinService'):
                    with patch('Src.gui.main_window.SecurityManager'):
                        app = MidnightClaimerGUI()
                        app.root.withdraw()
                        
                        # Test forward progression
                        initial_step = app.current_step
                        app.go_next()
                        self.assertEqual(app.current_step, initial_step + 1)
                        
                        # Test backward progression
                        app.go_back()
                        self.assertEqual(app.current_step, initial_step)
                        
                        app.root.destroy()
        except tk.TclError:
            self.skipTest("Tkinter not available")

class TestErrorHandling(unittest.TestCase):
    """Tests for error handling in GUI"""
    
    def test_derivation_error_handling(self):
        """Test error handling during derivation"""
        try:
            with patch('Src.gui.main_window.CardanoService'):
                with patch('Src.gui.main_window.BitcoinService'):
                    with patch('Src.gui.main_window.SecurityManager'):
                        app = MidnightClaimerGUI()
                        app.root.withdraw()
                        
                        # Simulate derivation error
                        app.progress_queue.put(("ERROR", "Test error message"))
                        
                        # The error should be handled gracefully
                        # (This would be tested more thoroughly with actual GUI interaction)
                        
                        app.root.destroy()
        except tk.TclError:
            self.skipTest("Tkinter not available")

class TestMockIntegration(unittest.TestCase):
    """Tests for proper mocking of external dependencies"""
    
    def test_service_mocking(self):
        """Test that services are properly mocked"""
        try:
            with patch('Src.gui.main_window.CardanoService') as mock_cardano:
                with patch('Src.gui.main_window.BitcoinService') as mock_bitcoin:
                    with patch('Src.gui.main_window.SecurityManager') as mock_security:
                        app = MidnightClaimerGUI()
                        app.root.withdraw()
                        
                        # Verify services were instantiated
                        mock_cardano.assert_called_once()
                        mock_bitcoin.assert_called_once()
                        mock_security.assert_called_once()
                        
                        app.root.destroy()
        except tk.TclError:
            self.skipTest("Tkinter not available")

if __name__ == '__main__':
    # Skip GUI tests if running in headless environment
    if 'DISPLAY' not in os.environ and os.name != 'nt':
        print("Skipping GUI tests - no display available")
        sys.exit(0)
    
    # Run tests with minimal GUI interaction
    unittest.main(verbosity=2)