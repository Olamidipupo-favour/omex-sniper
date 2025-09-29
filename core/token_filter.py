"""
Token Filter - Simplified token filtering service
"""

import logging
from typing import Dict, Any
from models.schemas import SniperConfig

logger = logging.getLogger(__name__)

class TokenFilterService:
    """Service for token filtering and configuration"""
    
    def __init__(self):
        self.config = SniperConfig(
            sol_per_snipe=0.01,
            max_positions=5,
            profit_target_percent=50.0,
            stop_loss_percent=20.0,
            min_market_cap=1000.0,
            max_market_cap=100000.0,
            min_liquidity=100.0,
            min_holders=10,
            auto_buy=False,
            auto_sell=True
        )
    
    def get_current_config(self) -> SniperConfig:
        """Get current configuration"""
        return self.config
    
    def update_config(self, config_data: Dict[str, Any]):
        """Update configuration"""
        try:
            for key, value in config_data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            logger.info("Token filter configuration updated")
            
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            raise
    
    def should_trade_token(self, token_data: Dict[str, Any]) -> bool:
        """Determine if a token should be traded based on filters"""
        try:
            # Apply market cap filter
            market_cap = token_data.get('market_cap', 0)
            if market_cap < self.config.min_market_cap or market_cap > self.config.max_market_cap:
                return False
            
            # Apply liquidity filter
            liquidity = token_data.get('liquidity', 0)
            if liquidity < self.config.min_liquidity:
                return False
            
            # Apply holders filter
            holders = token_data.get('holders', 0)
            if holders < self.config.min_holders:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking token filters: {e}")
            return False
