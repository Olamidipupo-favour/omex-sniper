#!/usr/bin/env python3
"""
Pump.Fun Sniper Bot - Main Entry Point
Helius RPC Powered Solana Token Sniper

Author: Built for personal use
Description: Auto-detects and snipes new tokens on Pump.Fun with configurable
            buy/sell logic, profit targets, and stop losses.
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from gui import main
    main() 