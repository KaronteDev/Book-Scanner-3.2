#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for scanner module
"""
import tkinter as tk
from gui.scanner_module import ScannerWindow

def test_scanner():
    """Launch scanner in standalone mode"""
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    # Open scanner window
    scanner = ScannerWindow(root)
    
    root.mainloop()

if __name__ == "__main__":
    test_scanner()
