"""
Configuration Service - Manages bot configuration and wallet
"""

import logging
import os
from typing import Optional, Dict, Any
from models.schemas import SniperConfig
from core.solana_client import SolanaClient

logger = logging.getLogger(__name__)

class ConfigService:
    """Service for managing configuration and wallet connections"""
    
    def __init__(self):
        self.solana_client = SolanaClient()
        self.wallet_connected = False
        self.wallet_address = None
        self.sniper_config = self._load_default_config()
        
    def _load_default_config(self) -> SniperConfig:
        """Load default configuration"""
        return SniperConfig(
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
    
    def get_sniper_config(self) -> SniperConfig:
        """Get current sniper configuration"""
        return self.sniper_config
    
    def update_sniper_config(self, config_data: Dict[str, Any]) -> SniperConfig:
        """Update sniper configuration"""
        try:
            # Update configuration with provided data
            for key, value in config_data.items():
                if hasattr(self.sniper_config, key):
                    setattr(self.sniper_config, key, value)
            
            # Save configuration
            self._save_config()
            
            logger.info("Sniper configuration updated")
            return self.sniper_config
            
        except Exception as e:
            logger.error(f"Failed to update sniper configuration: {e}")
            raise
    
    def connect_wallet(self, private_key: str) -> bool:
        """Connect wallet with private key"""
        try:
            # Validate private key format
            if not private_key or len(private_key) < 32:
                logger.error("Invalid private key format")
                return False
            
            # Set wallet in Solana client
            success = self.solana_client.set_wallet(private_key)
            
            if success:
                self.wallet_connected = True
                self.wallet_address = self.solana_client.get_wallet_address()
                logger.info(f"Wallet connected: {self.wallet_address}")
                return True
            else:
                logger.error("Failed to connect wallet")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect wallet: {e}")
            return False
    
    def disconnect_wallet(self) -> bool:
        """Disconnect wallet"""
        try:
            self.wallet_connected = False
            self.wallet_address = None
            self.solana_client.clear_wallet()
            logger.info("Wallet disconnected")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disconnect wallet: {e}")
            return False
    
    def is_wallet_connected(self) -> bool:
        """Check if wallet is connected"""
        return self.wallet_connected
    
    def get_wallet_address(self) -> Optional[str]:
        """Get connected wallet address"""
        return self.wallet_address
    
    def get_wallet_balance(self) -> float:
        """Get wallet SOL balance"""
        try:
            if not self.wallet_connected:
                return 0.0
            
            balance = self.solana_client.get_sol_balance()
            return balance
            
        except Exception as e:
            logger.error(f"Failed to get wallet balance: {e}")
            return 0.0
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            # In a real implementation, you would save to a config file or database
            # For now, we'll just log the configuration
            logger.info(f"Configuration saved: {self.sniper_config}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    def get_environment_config(self) -> Dict[str, Any]:
        """Get configuration from environment variables"""
        return {
            'helius_api_key': os.getenv('HELIUS_API_KEY', ''),
            'pumpportal_api_key': os.getenv('PUMPPORTAL_API_KEY', ''),
            'rpc_url': os.getenv('RPC_URL', 'https://api.mainnet-beta.solana.com'),
            'debug': os.getenv('DEBUG', 'False').lower() == 'true',
            'port': int(os.getenv('PORT', 8000))
        }
