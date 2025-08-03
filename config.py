import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Solana and API Configuration
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}" if HELIUS_API_KEY else "https://api.mainnet-beta.solana.com"

# PumpPortal Configuration  
PUMPPORTAL_API_URL = "https://pumpportal.fun/api"
PUMPPORTAL_WS_URL = "wss://pumpportal.fun/api/data"
PUMPPORTAL_API_KEY = os.getenv("PUMPPORTAL_API_KEY", "")

# Alternative WebSocket URLs to try
ALT_WS_URLS = [
    "wss://pumpportal.fun/api/data",
    "wss://frontend-api-v3.pump.fun/socket",
    "wss://client-api-2-74b1891ee9f9.pump.fun/socket.io/?EIO=4&transport=websocket"
]

# Transaction Configuration
PRIORITY_FEE = 0.0001  # SOL
DEFAULT_SLIPPAGE = 1.0  # 1%
DEFAULT_POOL = "pump"

@dataclass
class BotSettings:
    """Bot trading settings"""
    sol_per_snipe: float = 0.01
    max_positions: int = 5
    profit_target_percent: float = 50.0
    stop_loss_percent: float = 20.0
    min_market_cap: float = 1000.0
    max_market_cap: float = 100000.0
    min_liquidity: float = 100.0  # Minimum liquidity in SOL
    min_holders: int = 10  # Minimum number of holders
    auto_buy: bool = False
    auto_sell: bool = True

@dataclass
class BotState:
    """Current bot state"""
    is_running: bool = False
    wallet_connected: bool = False
    wallet_address: str = ""
    sol_balance: float = 0.0
    total_pnl: float = 0.0
    active_positions: int = 0

@dataclass
class AppConfig:
    """Complete application configuration"""
    private_key: str = ""
    bot_settings: BotSettings = None
    bot_state: BotState = None
    
    def __post_init__(self):
        if self.bot_settings is None:
            self.bot_settings = BotSettings()
        if self.bot_state is None:
            self.bot_state = BotState()

class ConfigManager:
    """Manages application configuration with file persistence"""
    
    def __init__(self, config_file: str = "bot_config.json"):
        self.config_file = Path(config_file)
        self.config = AppConfig()
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                # Load bot settings
                if 'bot_settings' in data:
                    self.config.bot_settings = BotSettings(**data['bot_settings'])
                
                # Load bot state  
                if 'bot_state' in data:
                    self.config.bot_state = BotState(**data['bot_state'])
                
                # Load private key (if exists)
                self.config.private_key = data.get('private_key', '')
                
                logger.info("✅ Configuration loaded successfully")
            else:
                logger.info("📁 No config file found, using defaults")
                self.save_config()  # Create default config file
            
            # Check for private key in environment variables if not in config
            if not self.config.private_key.strip():
                env_private_key = os.getenv('private_key', '').strip()
                if env_private_key:
                    logger.info("🔑 Found private key in environment variables")
                    self.config.private_key = env_private_key
                    self.save_config()  # Save it to config file
                
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            logger.info("🔄 Using default configuration")
    
    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            # Prepare data for saving
            config_data = {
                'private_key': self.config.private_key,
                'bot_settings': asdict(self.config.bot_settings),
                'bot_state': asdict(self.config.bot_state)
            }
            
            # Write to file with proper formatting
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info("💾 Configuration saved successfully")
            
        except Exception as e:
            logger.error(f"❌ Error saving config: {e}")
    
    def update_bot_settings(self, **kwargs) -> None:
        """Update bot settings"""
        for key, value in kwargs.items():
            if hasattr(self.config.bot_settings, key):
                setattr(self.config.bot_settings, key, value)
        self.save_config()
    
    def update_bot_state(self, **kwargs) -> None:
        """Update bot state"""
        for key, value in kwargs.items():
            if hasattr(self.config.bot_state, key):
                setattr(self.config.bot_state, key, value)
        self.save_config()
    
    def set_private_key(self, private_key: str) -> None:
        """Set private key"""
        self.config.private_key = private_key
        self.save_config()
    
    def get_private_key(self) -> str:
        """Get private key"""
        return self.config.private_key
    
    def has_private_key(self) -> bool:
        """Check if private key is configured"""
        return bool(self.config.private_key.strip())
    
    def clear_private_key(self) -> None:
        """Clear private key"""
        self.config.private_key = ""
        self.config.bot_state.wallet_connected = False
        self.config.bot_state.wallet_address = ""
        self.config.bot_state.sol_balance = 0.0
        self.save_config()

# Global config manager instance
config_manager = ConfigManager()

# Legacy exports for backward compatibility
Config = type('Config', (), {
    'HELIUS_RPC_URL': HELIUS_RPC_URL,
    'HELIUS_API_KEY': HELIUS_API_KEY,
    'PUMPPORTAL_API_URL': PUMPPORTAL_API_URL,
    'PUMPPORTAL_WS_URL': PUMPPORTAL_WS_URL,
    'PUMPPORTAL_API_KEY': PUMPPORTAL_API_KEY,
    'PRIORITY_FEE': PRIORITY_FEE,
    'DEFAULT_SLIPPAGE': DEFAULT_SLIPPAGE,
    'DEFAULT_POOL': DEFAULT_POOL,
}) 