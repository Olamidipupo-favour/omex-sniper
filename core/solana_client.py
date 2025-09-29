"""
Solana Client - Simplified Solana blockchain interaction
"""

import logging
import base58
from typing import Optional
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from config import HELIUS_RPC_URL

logger = logging.getLogger(__name__)

class SolanaClient:
    """Simplified Solana client for wallet operations"""
    
    def __init__(self, rpc_url: str = HELIUS_RPC_URL):
        self.rpc_url = rpc_url
        self.rpc_client = Client(rpc_url)
        self.async_client = AsyncClient(rpc_url)
        self.keypair: Optional[Keypair] = None
        self.wallet_address: Optional[str] = None
    
    def set_wallet(self, private_key: str) -> bool:
        """Set wallet from private key"""
        try:
            # Parse private key
            if private_key.startswith('[') and private_key.endswith(']'):
                # JSON array format
                import json
                key_array = json.loads(private_key)
                private_key_bytes = bytes(key_array)
            else:
                # Base58 format
                private_key_bytes = base58.b58decode(private_key)
            
            # Create keypair
            self.keypair = Keypair.from_bytes(private_key_bytes)
            self.wallet_address = str(self.keypair.pubkey())
            
            logger.info(f"Wallet set: {self.wallet_address}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set wallet: {e}")
            return False
    
    def clear_wallet(self):
        """Clear wallet data"""
        self.keypair = None
        self.wallet_address = None
    
    def get_wallet_address(self) -> Optional[str]:
        """Get wallet address"""
        return self.wallet_address
    
    def get_sol_balance(self) -> float:
        """Get SOL balance"""
        try:
            if not self.keypair:
                return 0.0
            
            balance = self.rpc_client.get_balance(self.keypair.pubkey())
            return balance.value / 1e9  # Convert lamports to SOL
            
        except Exception as e:
            logger.error(f"Failed to get SOL balance: {e}")
            return 0.0
    
    def is_wallet_set(self) -> bool:
        """Check if wallet is set"""
        return self.keypair is not None
