import asyncio
import json
import websockets
from typing import Optional, Dict, Any, List
from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.transaction import Transaction
from solana.rpc.commitment import Confirmed
from config import Config
import logging

logger = logging.getLogger(__name__)

class HeliusClient:
    def __init__(self):
        self.rpc_client = Client(Config.HELIUS_RPC_URL)
        self.async_client = AsyncClient(Config.HELIUS_RPC_URL)
        self.ws_url = Config.HELIUS_WS_URL
        self.websocket = None
        self.is_connected = False
        
    async def connect_websocket(self):
        """Connect to Helius WebSocket for real-time updates"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            self.is_connected = True
            logger.info("Connected to Helius WebSocket")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False
    
    async def subscribe_to_logs(self, program_id: str):
        """Subscribe to program logs for monitoring new tokens"""
        if not self.websocket:
            await self.connect_websocket()
            
        subscription = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {
                    "mentions": [program_id]
                },
                {
                    "commitment": "confirmed"
                }
            ]
        }
        
        await self.websocket.send(json.dumps(subscription))
        logger.info(f"Subscribed to logs for program: {program_id}")
    
    async def listen_for_new_tokens(self, callback):
        """Listen for new token creation events"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                if 'params' in data and 'result' in data['params']:
                    await callback(data['params']['result'])
        except Exception as e:
            logger.error(f"Error listening for tokens: {e}")
            self.is_connected = False
    
    def get_token_account_balance(self, token_account: str) -> float:
        """Get token account balance"""
        try:
            response = self.rpc_client.get_token_account_balance(PublicKey(token_account))
            if response['result']['value']:
                return float(response['result']['value']['uiAmount'])
            return 0.0
        except Exception as e:
            logger.error(f"Error getting token balance: {e}")
            return 0.0
    
    def get_sol_balance(self, wallet_address: str) -> float:
        """Get SOL balance in SOL (not lamports)"""
        try:
            response = self.rpc_client.get_balance(PublicKey(wallet_address))
            return response['result']['value'] / 1_000_000_000  # Convert lamports to SOL
        except Exception as e:
            logger.error(f"Error getting SOL balance: {e}")
            return 0.0
    
    async def send_transaction_with_priority(self, transaction: Transaction, keypair: Keypair) -> Optional[str]:
        """Send transaction with priority fee for faster execution"""
        try:
            # Add priority fee instruction
            from solana.system_program import TransferParams, transfer
            from solana.rpc.types import TxOpts
            
            # Send transaction with confirmed commitment
            opts = TxOpts(
                skip_confirmation=False,
                skip_preflight=False,
                preflight_commitment=Confirmed,
                max_retries=Config.MAX_RETRIES
            )
            
            response = await self.async_client.send_transaction(
                transaction, 
                keypair, 
                opts=opts
            )
            
            if response['result']:
                logger.info(f"Transaction sent: {response['result']}")
                return response['result']
            else:
                logger.error(f"Transaction failed: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending transaction: {e}")
            return None
    
    async def close(self):
        """Close connections"""
        if self.websocket:
            await self.websocket.close()
        await self.async_client.close()
        self.is_connected = False 