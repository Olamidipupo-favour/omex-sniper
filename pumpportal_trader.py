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
from solders.transaction import Transaction, VersionedTransaction
from solders.rpc.config import RpcSendTransactionConfig
from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts
from config import PUMPPORTAL_API_URL, HELIUS_RPC_URL, PUMPPORTAL_API_KEY

logger = logging.getLogger(__name__)

# SSL context configuration for macOS compatibility
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class PumpPortalTrader:
    """Handles trading operations via PumpPortal API"""
    
    def __init__(self, private_key: bytes = None, rpc_url: str = HELIUS_RPC_URL):
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
    
    async def build_transaction(self, action: str, mint: str, amount: float, slippage: float = 5.0, pool: str = "pump", priority_fee: float = 0.00001) -> Optional[Dict[str, Any]]:
        """Build transaction using PumpPortal API"""
        try:
            # Create a new session for this request to avoid event loop issues
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                if not self.keypair:
                    logger.error("❌ No wallet keypair available")
                    return None
                
                # Get wallet public key
                public_key = str(self.keypair.pubkey())
                
                # Debug logging
                logger.info(f"🔍 Building {action} transaction - amount: {amount}, type: {type(amount)}")
                logger.info(f"💰 Priority fee: {priority_fee} SOL")
                
                # Validate inputs
                if not mint or not public_key:
                    logger.error(f"❌ Invalid inputs - mint: {mint}, public_key: {public_key}")
                    return None
                
                if amount <= 0:
                    logger.error(f"❌ Invalid amount: {amount}")
                    return None
                
                # Prepare request data according to PumpPortal API docs
                logger.info(f"📊 Preparing {action} request for {mint}")
                if action == "buy":
                    # For buy, amount is SOL and denominatedInSol should be "true"
                    request_data = {
                        "publicKey": public_key,
                        "action": "buy",
                        "mint": mint,
                        "amount": float(amount),  # Convert SOL to lamports
                        "denominatedInSol": "true",
                        "slippage": int(slippage),
                        "priorityFee": float(priority_fee),  # Use provided priority fee
                        "pool": pool
                    }
                elif action == "sell":
                    # For sell, amount is token amount and denominatedInSol should be "false"
                    request_data = {
                        "publicKey": public_key,
                        "action": "sell",
                        "mint": mint,
                        "amount": float(amount),  # Token amount
                        "denominatedInSol": "false",
                        "slippage": int(slippage),
                        "priorityFee": float(priority_fee),  # Use provided priority fee
                        "pool": pool
                    }
                else:
                    logger.error(f"❌ Invalid action: {action}")
                    return None
                
                url = f"{PUMPPORTAL_API_URL}/trade-local"
                
                # Log the request details
                logger.info(f"📤 Building {action} transaction for {mint}")
                logger.info(f"🔗 URL: {url}")
                logger.info(f"📊 Request data: {request_data}")
                
                # Make the request
                async with session.post(url, json=request_data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    logger.info(f"📥 Response status: {response.status}")
                    logger.info(f"📥 Response headers: {dict(response.headers)}")
                    
                    if response.status == 200:
                        # Get response as bytes first
                        response_bytes = await response.read()
                        logger.info(f"📥 Response bytes length: {len(response_bytes)}")
                        logger.info(f"📥 First 100 bytes: {response_bytes[:100]}")
                        
                        # Try to decode as text first (for error messages)
                        try:
                            response_text = response_bytes.decode('utf-8')
                            logger.info(f"📥 Response as text: {response_text}")
                            
                            # Check if it's JSON (error message or metadata)
                            if response_text.strip().startswith('{'):
                                try:
                                    data = json.loads(response_text)
                                    logger.info(f"✅ JSON response received: {data}")
                                    return data
                                except json.JSONDecodeError:
                                    logger.info("📥 Not JSON, treating as raw transaction")
                            
                            # If it's not JSON, treat as base58 encoded transaction
                            logger.info(f"✅ Base58 transaction received")
                            return {"transaction": response_text}
                            
                        except UnicodeDecodeError:
                            # If it can't be decoded as UTF-8, it's raw binary transaction data
                            logger.info(f"✅ Raw binary transaction received (bytes: {len(response_bytes)})")
                            return {"transaction": response_bytes}
                    else:
                        # For error responses, try to get text
                        try:
                            response_text = await response.text()
                            logger.error(f"❌ API error {response.status}: {response_text}")
                        except:
                            response_bytes = await response.read()
                            logger.error(f"❌ API error {response.status}: Binary response (bytes: {len(response_bytes)})")
                        
                        logger.error(f"❌ Request data that failed: {request_data}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error building transaction: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return None
    
    async def lightning_transaction(self, action: str, mint: str, amount: float, slippage: float = 5.0, priority_fee: float = 0.00001,
                                  pool: str = "auto", skip_preflight: str = "true", jito_only: str = "false") -> Tuple[bool, Optional[str], float]:
        """Execute lightning transaction using PumpPortal API"""
        try:
            if not self.keypair:
                logger.error("❌ No wallet keypair available")
                return False, None, 0.0
            
            # Get wallet public key
            public_key = str(self.keypair.pubkey())
            
            # Prepare request data according to Lightning API docs
            print("Amount: ", amount)
            if action == "buy":
                # For buy, amount is SOL and denominatedInSol should be "true"
                request_data = {
                    "action": "buy",
                    "mint": mint,
                    "amount": float(amount),  # Convert SOL to lamports
                    "denominatedInSol": "true",
                    "slippage": int(slippage),
                    "priorityFee": float(priority_fee),  # Use provided priority fee
                    "pool": pool,
                    "skipPreflight": skip_preflight,
                    "jitoOnly": jito_only
                }
            elif action == "sell":
                # For sell, amount is token amount and denominatedInSol should be "false"
                request_data = {
                    "action": "sell",
                    "mint": mint,
                    "amount": float(amount),  # Token amount
                    "denominatedInSol": "false",
                    "slippage": int(slippage),
                    "priorityFee": float(priority_fee),  # Use provided priority fee
                    "pool": pool,
                    "skipPreflight": skip_preflight,
                    "jitoOnly": jito_only
                }
            else:
                raise ValueError(f"Invalid action: {action}")
            
            url = f"{PUMPPORTAL_API_URL}/trade?api-key={PUMPPORTAL_API_KEY}"
            
            # Log the request details
            logger.info(f"⚡ Lightning {action} transaction for {mint}")
            logger.info(f"🔗 URL: {url}")
            logger.info(f"📊 Request data: {request_data}")
            
            # Create a new session for this request to avoid event loop issues
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                async with session.post(url, data=request_data) as response:
                    logger.info(f"📥 Response status: {response.status}")
                    logger.info(f"📥 Response headers: {dict(response.headers)}")
                    
                    if response.status == 200:
                        response_text = await response.text()
                        logger.info(f"📥 Response text: {response_text}")
                        
                        try:
                            data = json.loads(response_text)
                            logger.info(f"✅ Lightning transaction response: {data}")
                            
                            # Check if transaction was successful
                            if "signature" in data:
                                logger.info(f"✅ Lightning transaction successful: {data}")
                                signature = data["signature"]
                                logger.info(f"✅ Lightning transaction successful: {signature}")
                                
                                # Extract token amount if available
                                token_amount = data.get("outputAmount", 0)
                                if action == "buy":
                                    logger.info(f"✅ Lightning buy successful - Tokens: {token_amount:,.0f}")
                                else:
                                    logger.info(f"✅ Lightning sell successful - SOL received: {token_amount/1e9:.4f}")
                                
                                return True, signature, token_amount
                            else:
                                logger.error(f"❌ Lightning transaction failed: {data}")
                                return False, None, 0.0
                                
                        except json.JSONDecodeError:
                            logger.error(f"❌ Invalid JSON response: {response_text}")
                            return False, None, 0.0
                    else:
                        # For error responses, try to get text
                        try:
                            response_text = await response.text()
                            logger.error(f"❌ Lightning API error {response.status}: {response_text}")
                        except:
                            logger.error(f"❌ Lightning API error {response.status}: Could not read response")
                        
                        logger.error(f"❌ Lightning request data that failed: {request_data}")
                        return False, None, 0.0
                        
        except Exception as e:
            logger.error(f"❌ Error in lightning transaction: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return False, None, 0.0
    
    async def sign_and_send_transaction(self, transaction_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Sign and send transaction"""
        try:
            if not self.keypair:
                raise ValueError("Wallet not set")
            
            logger.info(f"🔧 Transaction data received: {transaction_data}")
            
            # Handle different response formats
            if "transaction" in transaction_data:
                # Standard format with transaction field
                tx_data = transaction_data["transaction"]
            else:
                # Raw transaction data
                tx_data = transaction_data
            
            logger.info(f"📦 Transaction data type: {type(tx_data)}")
            logger.info(f"📦 Transaction data length: {len(str(tx_data))}")
            
            # Decode the transaction
            try:
                if isinstance(tx_data, str):
                    # If it's a string, try to decode as base58
                    tx_bytes = base58.b58decode(tx_data)
                elif isinstance(tx_data, bytes):
                    # If it's already bytes, use directly
                    tx_bytes = tx_data
                else:
                    logger.error(f"❌ Unexpected transaction data type: {type(tx_data)}")
                    return False, None
                
                logger.info(f"🔧 Decoded transaction bytes length: {len(tx_bytes)}")
                logger.info(f"🔧 First 50 bytes: {tx_bytes[:50]}")
                
                # Try to deserialize as VersionedTransaction first
                try:
                    tx = VersionedTransaction.from_bytes(tx_bytes)
                    logger.info("✅ Transaction deserialized as VersionedTransaction")
                except Exception as e:
                    logger.info(f"⚠️ Not a VersionedTransaction, trying regular Transaction: {e}")
                    # Fallback to regular Transaction
                    tx = Transaction.deserialize(tx_bytes)
                    logger.info("✅ Transaction deserialized as regular Transaction")
                
                # Sign transaction
                if hasattr(tx, 'sign'):
                    tx.sign(self.keypair)
                    logger.info("✅ Transaction signed")
                else:
                    # For VersionedTransaction, we need to create a new one with signatures
                    tx = VersionedTransaction(tx.message, [self.keypair])
                    logger.info("✅ VersionedTransaction created with signature")
                
                # Send transaction using a new client to avoid event loop issues
                logger.info("📤 Sending transaction...")
                async with AsyncClient(self.rpc_url) as client:
                    # Create proper options object
                    # opts = RpcSendTransactionConfig(
                    #     skip_preflight=True,
                    #     max_retries=3,
                    #     preflight_commitment="confirmed",
                    # )
                    latest=await client.get_latest_blockhash(commitment="confirmed")
                    opts = TxOpts(
                        skip_preflight=False,
                        max_retries=3,
                        preflight_commitment="confirmed",
                        skip_confirmation=False,
                        last_valid_block_height=latest.value.last_valid_block_height,
                    )
                    
                    signature = await client.send_transaction(
                        tx,
                        opts=opts
                    )

                    logger.info(f"✅ Transaction VALUE: {signature.value}")
                    
                    if signature.value:
                        logger.info(f"✅ Transaction sent: {signature.value}")
                        
                        # Wait for confirmation
                        confirmed = await self._wait_for_confirmation(signature.value, client)
                        #confirmed = True
                        if confirmed:
                            logger.info(f"✅ Transaction confirmed: {signature.value}")
                            return True, signature.value
                        else:
                            logger.error("❌ Transaction failed confirmation")
                            return False, signature.value
                    else:
                        logger.error("❌ Failed to send transaction")
                        return False, None
                        
            except Exception as e:
                logger.error(f"❌ Error processing transaction data: {e}")
                import traceback
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                return False, None
                
        except Exception as e:
            logger.error(f"❌ Error signing/sending transaction: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return False, None
    
    async def _wait_for_confirmation(self, signature: str, client: AsyncClient = None, timeout: int = 30) -> bool:
        """Wait for transaction confirmation"""
        try:
            start_time = time.time()
            
            # Use provided client or create a new one
            if client is None:
                client = self.async_rpc_client
            
            while time.time() - start_time < timeout:
                try:
                    result = await client.get_signature_statuses([signature], search_transaction_history=True)
                    if result.value and len(result.value) > 0 and None not in result.value:
                        logger.info(f"🙈 Transaction status check: {result}")
                        status = result.value[0]
                        if status and status.confirmation_status:
                            logger.info(f"Transaction status: {status}")
                            logger.info(f"Transaction confirmation status: {status.confirmation_status}")
                            
                            # Check if transaction is confirmed or finalized
                            # Convert enum to string for comparison
                            confirmation_str = str(status.confirmation_status).split('.')[-1].lower()
                            if confirmation_str in ["confirmed", "finalized"]:
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
    
    async def buy_token(self, mint_address: str, sol_amount: float, slippage: float = 5.0, transaction_type: str = "local", priority_fee: float = 0.00001) -> Tuple[bool, Optional[str], float]:
        """Buy tokens using SOL"""
        try:
            logger.info(f"Buying {sol_amount} SOL worth of {mint_address} using {transaction_type} transaction")
            logger.info(f"💰 Priority fee: {priority_fee} SOL")
            
            if transaction_type == "lightning":
                # Use lightning transaction
                success, signature, token_amount = await self.lightning_transaction("buy", mint_address, sol_amount, slippage, priority_fee=priority_fee)
                return success, signature, token_amount
            else:
                # Use local transaction (default)
                # Build transaction
                tx_data = await self.build_transaction("buy", mint_address, sol_amount, slippage, priority_fee=priority_fee)
                logger.info(f"🔍 Transaction data: {tx_data}")
                if not tx_data:
                    logger.error(f"❌ Failed to build transaction for {mint_address}")
                    return False, None, 0.0
                
                # Sign and send
                success, signature = await self.sign_and_send_transaction(tx_data)
                logger.info(f"sign and send transaction: {success} signature: {signature}")
                if success:
                    # Extract token amount from response or calculate estimate
                    token_amount = tx_data.get("outputAmount", 0)
                    logger.info(f"✅ Buy successful - Tokens: {token_amount:,.0f}")
                    return True, signature, token_amount
                else:
                    logger.error(f"❌ Failed to sign and send transaction for {mint_address}")
                    return False, signature, 0.0
                
        except Exception as e:
            logger.error(f"Error buying token: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return False, None, 0.0
    
    async def sell_token(self, mint_address: str, token_amount: float, slippage: float = 5.0, transaction_type: str = "local", priority_fee: float = 0.00001) -> Tuple[bool, Optional[str], float]:
        """Sell tokens for SOL"""
        try:
            logger.info(f"Selling {token_amount:,.0f} tokens of {mint_address} using {transaction_type} transaction")
            logger.info(f"💰 Priority fee: {priority_fee} SOL")
            
            if transaction_type == "lightning":
                # Use lightning transaction
                success, signature, sol_received = await self.lightning_transaction("sell", mint_address, token_amount, slippage, priority_fee=priority_fee)
                return success, signature, sol_received
            else:
                # Use local transaction (default)
                # Build transaction
                tx_data = await self.build_transaction("sell", mint_address, token_amount, slippage, priority_fee=priority_fee)
                if not tx_data:
                    logger.error(f"❌ Failed to build sell transaction for {mint_address}")
                    return False, None, 0.0
                
                # Sign and send
                success, signature = await self.sign_and_send_transaction(tx_data)
                
                if success:
                    # Extract SOL amount from response
                    sol_received = tx_data.get("outputAmount", 0) / 1e9  # Convert lamports to SOL
                    logger.info(f"✅ Sell successful - SOL received: {sol_received:.4f}")
                    return True, signature, sol_received
                else:
                    logger.error(f"❌ Failed to sign and send sell transaction for {mint_address}")
                    return False, signature, 0.0
                
        except Exception as e:
            logger.error(f"Error selling token: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
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