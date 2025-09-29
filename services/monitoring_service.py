"""
Monitoring Service - Handles token monitoring and detection
"""

import asyncio
import logging
from typing import Dict, List, Optional
from models.schemas import TokenInfo
from core.pump_monitor import PumpPortalMonitor
from core.token_filter import TokenFilterService

logger = logging.getLogger(__name__)

class MonitoringService:
    """Service for monitoring new tokens and market data"""
    
    def __init__(self):
        self.monitor = PumpPortalMonitor()
        self.filter_service = TokenFilterService()
        self.is_monitoring = False
        self.monitored_tokens = []
        self.callbacks = []
        
    def is_monitoring_active(self) -> bool:
        """Check if monitoring is currently active"""
        return self.is_monitoring
    
    def get_monitored_tokens(self) -> List[TokenInfo]:
        """Get list of currently monitored tokens"""
        return self.monitored_tokens
    
    def start_monitoring(self) -> bool:
        """Start token monitoring"""
        try:
            if self.is_monitoring:
                logger.warning("Monitoring is already active")
                return False
            
            # Set up callbacks
            self.monitor.set_new_token_callback(self._on_new_token)
            self.monitor.set_trade_callback(self._on_trade)
            
            # Start monitoring in background
            asyncio.create_task(self._monitoring_loop())
            
            self.is_monitoring = True
            logger.info("Token monitoring started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """Stop token monitoring"""
        try:
            if not self.is_monitoring:
                logger.warning("Monitoring is not active")
                return False
            
            self.monitor.stop_monitoring()
            self.is_monitoring = False
            logger.info("Token monitoring stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}")
            return False
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        try:
            await self.monitor.start_monitoring()
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}")
            self.is_monitoring = False
    
    def _on_new_token(self, token: TokenInfo):
        """Handle new token detection"""
        try:
            logger.info(f"New token detected: {token.symbol} ({token.name})")
            
            # Add to monitored tokens
            self.monitored_tokens.append(token)
            
            # Apply filters
            if self._should_trade_token(token):
                logger.info(f"Token {token.symbol} passed filters, triggering trade")
                # Trigger trade callback
                for callback in self.callbacks:
                    try:
                        callback('new_token', token)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
            
        except Exception as e:
            logger.error(f"Error handling new token: {e}")
    
    def _on_trade(self, trade_data):
        """Handle trade updates"""
        try:
            logger.debug(f"Trade update: {trade_data}")
            
            # Update token prices and positions
            for callback in self.callbacks:
                try:
                    callback('trade_update', trade_data)
                except Exception as e:
                    logger.error(f"Trade callback error: {e}")
            
        except Exception as e:
            logger.error(f"Error handling trade: {e}")
    
    def _should_trade_token(self, token: TokenInfo) -> bool:
        """Determine if a token should be traded based on filters"""
        try:
            # Get current configuration
            config = self.filter_service.get_current_config()
            
            # Apply market cap filter
            if token.market_cap < config.min_market_cap or token.market_cap > config.max_market_cap:
                return False
            
            # Apply liquidity filter
            if token.liquidity < config.min_liquidity:
                return False
            
            # Apply holders filter
            if token.holders < config.min_holders:
                return False
            
            # Check if auto buy is enabled
            if not config.auto_buy:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking token filters: {e}")
            return False
    
    def add_callback(self, callback):
        """Add a callback for monitoring events"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback):
        """Remove a callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
