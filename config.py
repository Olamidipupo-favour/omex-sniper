import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Helius RPC Configuration
    HELIUS_API_KEY = os.getenv('HELIUS_API_KEY', 'your-helius-api-key-here')
    HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
    HELIUS_WS_URL = f"wss://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
    
    # PumpPortal API Configuration
    PUMP_FUN_API_URL = "https://pumpportal.fun/api"  # Updated to correct API endpoint
    PUMPPORTAL_WS_URL = "wss://pumpportal.fun/api/data"  # WebSocket for real-time data
    PUMPPORTAL_API_KEY = os.getenv('PUMPPORTAL_API_KEY', '')  # Optional API key
    
    # Bot Settings (defaults)
    DEFAULT_SOL_AMOUNT = 0.01  # SOL to spend per snipe
    DEFAULT_MAX_TOKENS = 5     # Max concurrent positions
    DEFAULT_PROFIT_PERCENT = 50.0  # Take profit at 50%
    DEFAULT_STOP_LOSS_PERCENT = 20.0  # Stop loss at -20%
    DEFAULT_SLIPPAGE = 5.0     # 5% slippage tolerance
    
    # Transaction Settings
    PRIORITY_FEE = 0.00005  # SOL priority fee (recommended by PumpPortal)
    MAX_RETRIES = 3
    CONFIRMATION_COMMITMENT = "confirmed"
    DEFAULT_POOL = "pump"  # pump, raydium, or auto
    
    # GUI Settings
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    UPDATE_INTERVAL = 1000  # milliseconds 