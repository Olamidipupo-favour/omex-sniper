#!/usr/bin/env python3
"""
PumpPortal Trader - Handles buying/selling tokens via PumpPortal's trade-local API
Integrates with Helius RPC for fast transaction processing
"""

import asyncio
import aiohttp
import json
import logging
import time
import base58
import ssl
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from config import Config

logger = logging.getLogger(__name__)

# SSL context configuration for macOS compatibility
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class PumpPortalTrader:
    """Handles trading operations via PumpPortal API"""
    
    def __init__(self, private_key: bytes = None, rpc_url: str = Config.HELIUS_RPC_URL):
        self.private_key = private_key
        self.rpc_url = rpc_url
        self.rpc_client = Client(rpc_url)
        self.async_rpc_client = AsyncClient(rpc_url)
        self.session: Optional[aiohttp.ClientSession] = None
        self.keypair: Optional[Keypair] = None
        
        if private_key:
            self.set_wallet(private_key)
    
    def set_wallet(self, private_key: bytes):
        """Set wallet keypair from private key"""
        try:
            self.private_key = private_key
            self.keypair = Keypair.from_bytes(private_key)
            logger.info(f"Wallet set: {str(self.keypair.pubkey())}")
        except Exception as e:
            logger.error(f"Error setting wallet: {e}")
            raise
    
    async def start_session(self):
        """Start HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context))
    
    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def get_wallet_balance(self) -> float:
        """Get wallet SOL balance"""
        try:
            if not self.keypair:
                return 0.0
            
            balance = self.rpc_client.get_balance(self.keypair.pubkey())
            return balance.value / 1e9  # Convert lamports to SOL
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0.0
    
    async def build_transaction(self, action: str, mint: str, amount: float, slippage: float = 5.0, pool: str = "pump") -> Optional[Dict[str, Any]]:
        """Build transaction using PumpPortal API"""
        try:
            await self.start_session()
            
            if action == "buy":
                # Convert SOL to lamports
                lamports = int(amount * 1e9)
                url = f"{Config.PUMP_FUN_API_URL}/trade-local"
                
                params = {
                    "action": "buy",
                    "mint": mint,
                    "sol": lamports,
                    "slippage": int(slippage * 100),  # Convert to basis points
                    "pool": pool
                }
            elif action == "sell":
                # amount is token amount for sell
                url = f"{Config.PUMP_FUN_API_URL}/trade-local"
                
                params = {
                    "action": "sell",
                    "mint": mint,
                    "amount": int(amount),
                    "slippage": int(slippage * 100),
                    "pool": pool
                }
            else:
                raise ValueError(f"Invalid action: {action}")
            
            if Config.PUMPPORTAL_API_KEY:
                headers = {"Authorization": f"Bearer {Config.PUMPPORTAL_API_KEY}"}
            else:
                headers = {}
            
            logger.info(f"Building {action} transaction for {mint}")
            
            async with self.session.post(url, json=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"API error {response.status}: {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error building transaction: {e}")
            return None
    
    async def sign_and_send_transaction(self, transaction_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Sign and send transaction"""
        try:
            if not self.keypair:
                raise ValueError("Wallet not set")
            
            # Extract transaction from response
            if "transaction" not in transaction_data:
                logger.error("No transaction in response")
                return False, None
            
            # Decode the transaction
            tx_bytes = base58.b58decode(transaction_data["transaction"])
            tx = Transaction.deserialize(tx_bytes)
            
            # Sign transaction
            tx.sign(self.keypair)
            
            # Send transaction
            signature = await self.async_rpc_client.send_transaction(
                tx,
                opts={"skip_preflight": True, "max_retries": 3}
            )
            
            if signature.value:
                logger.info(f"Transaction sent: {signature.value}")
                
                # Wait for confirmation
                confirmed = await self._wait_for_confirmation(signature.value)
                if confirmed:
                    return True, signature.value
                else:
                    logger.error("Transaction failed confirmation")
                    return False, signature.value
            else:
                logger.error("Failed to send transaction")
                return False, None
                
        except Exception as e:
            logger.error(f"Error signing/sending transaction: {e}")
            return False, None
    
    async def _wait_for_confirmation(self, signature: str, timeout: int = 30) -> bool:
        """Wait for transaction confirmation"""
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    result = await self.async_rpc_client.get_signature_statuses([signature])
                    if result.value and len(result.value) > 0:
                        status = result.value[0]
                        if status and status.confirmation_status:
                            if status.confirmation_status in ["confirmed", "finalized"]:
                                logger.info(f"Transaction confirmed: {signature}")
                                return True
                            elif status.err:
                                logger.error(f"Transaction failed: {status.err}")
                                return False
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.debug(f"Error checking confirmation: {e}")
                    await asyncio.sleep(1)
            
            logger.warning(f"Transaction confirmation timeout: {signature}")
            return False
            
        except Exception as e:
            logger.error(f"Error waiting for confirmation: {e}")
            return False
    
    async def buy_token(self, mint_address: str, sol_amount: float, slippage: float = 5.0) -> Tuple[bool, Optional[str], float]:
        """Buy tokens using SOL"""
        try:
            logger.info(f"Buying {sol_amount} SOL worth of {mint_address}")
            
            # Build transaction
            tx_data = await self.build_transaction("buy", mint_address, sol_amount, slippage)
            if not tx_data:
                return False, None, 0.0
            
            # Sign and send
            success, signature = await self.sign_and_send_transaction(tx_data)
            
            if success:
                # Extract token amount from response or calculate estimate
                token_amount = tx_data.get("outputAmount", 0)
                logger.info(f"✅ Buy successful - Tokens: {token_amount:,.0f}")
                return True, signature, token_amount
            else:
                return False, signature, 0.0
                
        except Exception as e:
            logger.error(f"Error buying token: {e}")
            return False, None, 0.0
    
    async def sell_token(self, mint_address: str, token_amount: float, slippage: float = 5.0) -> Tuple[bool, Optional[str], float]:
        """Sell tokens for SOL"""
        try:
            logger.info(f"Selling {token_amount:,.0f} tokens of {mint_address}")
            
            # Build transaction
            tx_data = await self.build_transaction("sell", mint_address, token_amount, slippage)
            if not tx_data:
                return False, None, 0.0
            
            # Sign and send
            success, signature = await self.sign_and_send_transaction(tx_data)
            
            if success:
                # Extract SOL amount from response
                sol_received = tx_data.get("outputAmount", 0) / 1e9  # Convert lamports to SOL
                logger.info(f"✅ Sell successful - SOL received: {sol_received:.4f}")
                return True, signature, sol_received
            else:
                return False, signature, 0.0
                
        except Exception as e:
            logger.error(f"Error selling token: {e}")
            return False, None, 0.0
    
    def get_token_accounts(self, owner: str) -> List[Dict[str, Any]]:
        """Get token accounts for wallet"""
        try:
            response = self.rpc_client.get_token_accounts_by_owner(
                Pubkey.from_string(owner),
                {"programId": Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")}
            )
            return response.value if response.value else []
        except Exception as e:
            logger.error(f"Error getting token accounts: {e}")
            return []
    
    def get_transaction_url(self, signature: str) -> str:
        """Get Solscan URL for transaction"""
        return f"https://solscan.io/tx/{signature}"
    
    def get_token_url(self, mint: str) -> str:
        """Get Solscan URL for token"""
        return f"https://solscan.io/token/{mint}"
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_session() 