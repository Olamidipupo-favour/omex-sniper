"""
Pump Monitor - Refactored from pump_fun_monitor.py
"""

import asyncio
import logging
from typing import Callable, Optional, Dict, Any
from models.schemas import TokenInfo
from pump_fun_monitor import PumpPortalMonitor as OriginalMonitor

logger = logging.getLogger(__name__)

class PumpPortalMonitor:
    """Simplified wrapper around the original monitor"""
    
    def __init__(self):
        self.monitor = OriginalMonitor()
        self.is_monitoring = False
        self.new_token_callback: Optional[Callable] = None
        self.trade_callback: Optional[Callable] = None
    
    def set_new_token_callback(self, callback: Callable[[TokenInfo], None]):
        """Set callback for new token events"""
        self.new_token_callback = callback
        self.monitor.set_new_token_callback(self._on_new_token)
    
    def set_trade_callback(self, callback: Callable):
        """Set callback for trade events"""
        self.trade_callback = callback
        self.monitor.set_trade_callback(self._on_trade)
    
    def _on_new_token(self, token_data):
        """Handle new token from original monitor"""
        try:
            # Convert to our TokenInfo format
            token = TokenInfo(
                mint=token_data.mint,
                symbol=token_data.symbol,
                name=token_data.name,
                price=token_data.price,
                market_cap=token_data.market_cap,
                liquidity=token_data.liquidity,
                holders=token_data.holders,
                created_timestamp=token_data.created_timestamp,
                is_on_pump=token_data.is_on_pump if hasattr(token_data, 'is_on_pump') else False,
                source='pumpportal'
            )
            
            if self.new_token_callback:
                self.new_token_callback(token)
                
        except Exception as e:
            logger.error(f"Error handling new token: {e}")
    
    def _on_trade(self, trade_data):
        """Handle trade from original monitor"""
        try:
            if self.trade_callback:
                self.trade_callback(trade_data)
                
        except Exception as e:
            logger.error(f"Error handling trade: {e}")
    
    async def start_monitoring(self):
        """Start monitoring"""
        try:
            self.is_monitoring = True
            await self.monitor.start_monitoring()
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self.is_monitoring = False
    
    def stop_monitoring(self):
        """Stop monitoring"""
        try:
            self.is_monitoring = False
            self.monitor.stop_monitoring()
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}")
    
    def is_monitoring_active(self) -> bool:
        """Check if monitoring is active"""
        return self.is_monitoring
