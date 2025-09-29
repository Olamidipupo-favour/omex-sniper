"""
Pump Trader - Refactored from pumpportal_trader.py
"""

import asyncio
import logging
from typing import Tuple, Optional
from pumpportal_trader import PumpPortalTrader as OriginalTrader

logger = logging.getLogger(__name__)

class PumpPortalTrader:
    """Simplified wrapper around the original trader"""
    
    def __init__(self, private_key: bytes = None, rpc_url: str = None):
        self.trader = OriginalTrader(private_key, rpc_url)
    
    def set_wallet(self, private_key: bytes):
        """Set wallet keypair"""
        self.trader.set_wallet(private_key)
    
    async def buy_token(self, mint_address: str, sol_amount: float, 
                       slippage: float = 5.0, transaction_type: str = "local", 
                       priority_fee: float = 0.0001) -> Tuple[bool, Optional[str], float]:
        """Buy tokens"""
        try:
            return await self.trader.buy_token(
                mint_address, sol_amount, slippage, transaction_type, priority_fee
            )
        except Exception as e:
            logger.error(f"Buy token failed: {e}")
            return False, None, 0.0
    
    async def sell_token(self, mint_address: str, token_amount: float, 
                        slippage: float = 5.0, transaction_type: str = "local", 
                        priority_fee: float = 0.0001) -> Tuple[bool, Optional[str], float]:
        """Sell tokens"""
        try:
            return await self.trader.sell_token(
                mint_address, token_amount, slippage, transaction_type, priority_fee
            )
        except Exception as e:
            logger.error(f"Sell token failed: {e}")
            return False, None, 0.0
    
    def get_wallet_balance(self) -> float:
        """Get wallet balance"""
        return self.trader.get_wallet_balance()
