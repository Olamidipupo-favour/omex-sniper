import asyncio
import websockets
import websocket  # Add synchronous websocket
import json
import logging
import ssl
import aiohttp
import threading
import time
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
from config import PUMPPORTAL_WS_URL, PUMPPORTAL_API_URL
from queue import Queue
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# SSL context configuration for macOS compatibility
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

@dataclass
class TokenInfo:
    mint: str
    name: str
    symbol: str
    description: str
    image: str
    created_timestamp: int
    usd_market_cap: float
    market_cap: float
    price: float
    creator: str = ""
    twitter: str = ""
    telegram: str = ""
    website: str = ""
    nsfw: bool = False
    # Additional PumpPortal fields
    sol_in_pool: float = 0.0
    tokens_in_pool: float = 0.0
    initial_buy: float = 0.0
    sol_amount: float = 0.0
    new_token_balance: float = 0.0
    trader_public_key: str = ""
    tx_type: str = ""
    signature: str = ""
    pool: str = ""
    # New filtering fields
    liquidity: float = 0.0  # Liquidity in SOL
    holders: int = 0  # Number of holders
    
@dataclass
class TradeInfo:
    signature: str
    mint: str
    trader: str
    is_buy: bool
    amount: float  # SOL amount
    token_amount: float  # Token amount
    price: float
    market_cap: float
    timestamp: int
    token_symbol: str = ""  # Token symbol from trade data
    token_name: str = ""    # Token name from trade data
    
class PumpPortalMonitor:
    def __init__(self):
        """Initialize the monitor"""
        self.websocket = None
        self.ws_app = None
        self.monitoring = False
        self.new_token_callback = None
        self.trade_callback = None
        self.known_tokens = set()
        
        # Track subscriptions for proper unsubscription
        self.monitored_tokens = set()  # Track which tokens we're monitoring
        self.monitored_accounts = set()  # Track which accounts we're monitoring
        self.subscribed_to_new_tokens = False  # Track if we're subscribed to new tokens
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        self.sol_price_usd = 188.76  # Default fallback price (current SOL price)
        self.last_sol_price_update = 0
        self.sol_price_cache_duration = 300  # 5 minutes
        
        # Callback queue for handling async callbacks from WebSocket threads
        self.callback_queue = Queue()
        self.callback_processor_running = False
        
        # Price update callback
        self.price_update_callback = None
        
        # Buy count tracking per token
        self.buy_counts = {}  # {token_address: count}
    
    async def start_callback_processor(self):
        """Start the callback processor to handle async callbacks from WebSocket threads"""
        if self.callback_processor_running:
            logger.info("🔄 Callback processor already marked as running, checking if task is alive...")
            # Force restart if the task died
            self.callback_processor_running = False
        
        self.callback_processor_running = True
        logger.info("🔄 Starting callback processor...")
        
        async def process_callbacks():
            logger.info("🔄 Callback processor loop started - ACTIVE")
            callback_count = 0
            while self.callback_processor_running:
                try:
                    # Check for callbacks in the queue
                    if not self.callback_queue.empty():
                        callback_info = self.callback_queue.get_nowait()
                        callback_func, args = callback_info
                        callback_count += 1
                        
                        logger.info(f"📤 Processing callback #{callback_count}: {callback_func.__name__} with args: {args}")
                        
                        if asyncio.iscoroutinefunction(callback_func):
                            logger.info(f"🔄 Executing async callback: {callback_func.__name__}")
                            await callback_func(*args)
                            logger.info(f"✅ Async callback completed: {callback_func.__name__}")
                        else:
                            logger.info(f"🔄 Executing sync callback: {callback_func.__name__}")
                            callback_func(*args)
                            logger.info(f"✅ Sync callback completed: {callback_func.__name__}")
                    else:
                        # Log periodic heartbeat to confirm processor is alive
                        if callback_count > 0 and callback_count % 100 == 0:
                            logger.info(f"💓 Callback processor heartbeat - processed {callback_count} callbacks")
                        await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                except Exception as e:
                    logger.error(f"❌ Error processing callback: {e}")
                    import traceback
                    logger.error(f"❌ Callback error traceback: {traceback.format_exc()}")
                    await asyncio.sleep(0.1)
            
            logger.info("🛑 Callback processor loop ended")
        
        # Start the callback processor task and store reference
        self._callback_processor_task = asyncio.create_task(process_callbacks())
        logger.info("✅ Callback processor task created and started")
    
    def stop_callback_processor(self):
        """Stop the callback processor"""
        self.callback_processor_running = False
        logger.info("🛑 Callback processor stopped")
    
    async def get_sol_price(self) -> float:
        """Fetch real-time SOL price from Pump.Fun API"""
        current_time = datetime.now().timestamp()
        
        # Return cached price if it's still fresh
        if current_time - self.last_sol_price_update < self.sol_price_cache_duration:
            return self.sol_price_usd
        
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                async with session.get('https://frontend-api-v3.pump.fun/sol-price') as response:
                    if response.status == 200:
                        data = await response.json()
                        self.sol_price_usd = data.get('solPrice', 100.0)
                        self.last_sol_price_update = current_time
                        logger.info(f"📈 Updated SOL price: ${self.sol_price_usd:.2f}")
                        return self.sol_price_usd
                    else:
                        logger.warning(f"Failed to fetch SOL price: HTTP {response.status}")
                        return self.sol_price_usd
        except Exception as e:
            logger.warning(f"Error fetching SOL price: {e}")
            return self.sol_price_usd
    
    async def get_token_holders_count(self, mint: str) -> int:
        """Get the number of holders for a token using SolanaTracker API with Moralis fallback"""
        try:
            # Add 0.5 second delay between requests to prevent rate limiting
            await asyncio.sleep(0.5)
            
            # Primary: Try SolanaTracker API first
            logger.info(f"🔍 Fetching holders for {mint} from SolanaTracker API")
            
            url = f"https://data.solanatracker.io/tokens/{mint}/holders"
            headers = {
                "x-api-key": os.getenv('SOLANA_TRACKER_API')
            }
            
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    logger.info(f"📡 SolanaTracker response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"📋 SolanaTracker response for {mint}: {data}")
                        
                        # Extract holder count from SolanaTracker response
                        if 'total' in data:
                            holders_count = int(data['total'])
                            logger.info(f"📊 Token {mint}: Found {holders_count} holders (from SolanaTracker total)")
                            return holders_count
                        elif 'accounts' in data and isinstance(data['accounts'], list):
                            # If total not available, count the accounts array
                            holders_count = len(data['accounts'])
                            logger.info(f"📊 Token {mint}: Found {holders_count} holders (from SolanaTracker accounts array)")
                            return holders_count
                        else:
                            logger.warning(f"⚠️ No holder data found in SolanaTracker response for {mint}")
                            logger.debug(f"📋 Full response: {data}")
                            # Fall back to Moralis API
                            return await self._get_holders_from_moralis_fallback(mint)
                    else:
                        # Try to get error response body
                        try:
                            error_body = await response.text()
                            logger.error(f"❌ HTTP {response.status} error for {mint}: {error_body}")
                        except:
                            logger.error(f"❌ HTTP {response.status} error for {mint}: Could not read error body")
                        
                        logger.warning(f"⚠️ SolanaTracker failed for {mint}: HTTP {response.status}, trying Moralis fallback")
                        # Fall back to Moralis API
                        return await self._get_holders_from_moralis_fallback(mint)
                        
        except Exception as e:
            logger.error(f"❌ Exception getting holders from SolanaTracker for {mint}: {e}")
            logger.info(f"🔄 Trying Moralis fallback for {mint}")
            # Fall back to Moralis API
            return await self._get_holders_from_moralis_fallback(mint)
    
    async def _get_holders_from_moralis_fallback(self, mint: str) -> int:
        """Fallback method to get holder count from Moralis API"""
        try:
            # Add 0.5 second delay between requests to prevent rate limiting
            await asyncio.sleep(0.5)
            
            logger.info(f"🔄 Fetching holders for {mint} from Moralis API (fallback)")
            
            # Moralis API endpoint for holder data
            url = f"https://solana-gateway.moralis.io/token/mainnet/holders/{mint}"
            headers = {
                "Accept": "application/json",
                "X-API-Key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjkyZThkZmJhLTAyOGUtNGI5NC04ZjMzLWJkMTIwY2Y1MmM4MSIsIm9yZ0lkIjoiNDY3MjA2IiwidXNlcklkIjoiNDgwNjQ1IiwidHlwZUlkIjoiZmRlNTBkZmItNWIwNS00ZTIzLWIzODYtYjhiMzc5NTUwM2JlIiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3NTYxNDY2NjQsImV4cCI6NDkxMTkwNjY2NH0.iOqIBD7EERIIi38WSiqzcEfqwWxdAWjLDBL7tNZ-6MQ"
            }
            
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                async with session.get(url, headers=headers, timeout=15) as response:
                    logger.info(f"📡 Moralis fallback response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"📋 Moralis fallback response for {mint}: {data}")
                        
                        # Check if data is None or empty
                        if data is None:
                            logger.warning(f"⚠️ Moralis fallback returned None for {mint}, using default holder count")
                            return 0
                        
                        # Extract holder count from Moralis response
                        if 'totalHolders' in data:
                            holders_count = data['totalHolders']
                            logger.info(f"📊 Token {mint}: Found {holders_count} holders (from Moralis fallback totalHolders)")
                            return int(holders_count)
                        elif 'result' in data and isinstance(data['result'], list):
                            # Fallback for other response formats
                            holders_count = len(data['result'])
                            logger.info(f"📊 Token {mint}: Found {holders_count} holders (from Moralis fallback result array)")
                            return int(holders_count)
                        elif 'total' in data:
                            # Fallback for other response formats
                            holders_count = data['total']
                            logger.info(f"📊 Token {mint}: Found {holders_count} holders (from Moralis fallback total)")
                            return int(holders_count)
                        else:
                            logger.warning(f"⚠️ No holder data found in Moralis fallback response for {mint}")
                            logger.debug(f"📋 Full response: {data}")
                            return 0
                    else:
                        # Try to get error response body
                        try:
                            error_body = await response.text()
                            logger.error(f"❌ HTTP {response.status} error for {mint} from Moralis fallback: {error_body}")
                        except:
                            logger.error(f"❌ HTTP {response.status} error for {mint} from Moralis fallback: Could not read error body")
                        
                        logger.warning(f"⚠️ Moralis fallback failed for {mint}: HTTP {response.status}")
                        return 0
                        
        except Exception as e:
            logger.error(f"❌ Exception getting holders from Moralis fallback for {mint}: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            logger.info(f"🔄 Using default holder count (0) for {mint}")
            return 0
    
    async def update_token_holders_and_filter(self, token: TokenInfo, min_liquidity: float = 100.0, min_holders: int = 10) -> bool:
        """Update holders count for a token and check if it passes filtering criteria"""
        try:
            # Get current holders count from SolanaTracker API
            holders_count = await self.get_token_holders_count(token.mint)
            
            # Update the token with real holders count
            token.holders = holders_count
            
            # Get liquidity (should already be in SOL)
            liquidity = token.liquidity
            
            logger.info(f"📊 Token {token.symbol}: liquidity={liquidity:.2f} SOL, holders={holders_count}")
            
            # Check if token passes filtering criteria
            if liquidity >= min_liquidity and holders_count >= min_holders:
                logger.debug(f"✅ Token {token.symbol} passed filter: liquidity={liquidity:.2f} SOL, holders={holders_count}")
                return True
            else:
                logger.debug(f"❌ Token {token.symbol} failed filter: liquidity={liquidity:.2f} SOL, holders={holders_count}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating holders for {token.symbol}: {e}")
            logger.info(f"🔄 Using fallback holder count (0) for {token.symbol}")
            token.holders = 0
            return True  # Pass through if there's an error
    
    def set_new_token_callback(self, callback: Callable[[TokenInfo], None]):
        """Set callback function for new token notifications"""
        self.new_token_callback = callback
    
    def set_trade_callback(self, callback: Callable[[TradeInfo], None]):
        """Set callback function for trade notifications"""
        self.trade_callback = callback
    
    def set_price_update_callback(self, callback: Callable[[str, float, float], None]):
        """Set callback function for price update notifications"""
        self.price_update_callback = callback
    
    async def connect_websocket(self) -> bool:
        """Connect to PumpPortal WebSocket"""
        try:
            self.connection_attempts += 1
            logger.info(f"🔌 Connecting to PumpPortal WebSocket (attempt {self.connection_attempts})...")
            logger.info(f"📡 WebSocket URL: {PUMPPORTAL_WS_URL}")
            
            # Add step-by-step logging
            logger.info("🔧 Step 1: Creating SSL context...")
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            logger.info("✅ Step 1 complete")
            
            logger.info("🔧 Step 2: Attempting WebSocket connection...")
            # Add timeout to prevent hanging
            try:
                logger.info(f"🔧 Step 2: Attempting WebSocket connection to {PUMPPORTAL_WS_URL}...")
                self.websocket = await asyncio.wait_for(
                    websockets.connect(
                        PUMPPORTAL_WS_URL,
                        ssl=ssl_ctx,
                        ping_interval=20,
                        ping_timeout=10,
                        close_timeout=10
                    ),
                    timeout=15  # 15 second timeout
                )
                logger.info(f"🔧 Step 2: WebSocket connected to {PUMPPORTAL_WS_URL}")
                logger.info("✅ Step 2 complete - WebSocket connected!")
            except asyncio.TimeoutError:
                logger.error("❌ Step 2 TIMEOUT - WebSocket connection timed out after 15 seconds")
                raise
            
            logger.info("🔧 Step 3: Testing connection with ping...")
            await self.websocket.ping()
            logger.info("✅ Step 3 complete - Ping successful!")
            
            logger.info("✅ Connected to PumpPortal WebSocket successfully")
            self.connection_attempts = 0  # Reset on successful connection
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to WebSocket: {e}")
            logger.error(f"   Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            self.websocket = None
            return False
    
    async def subscribe_new_tokens(self):
        """Subscribe to new token creation events"""
        if not self.websocket:
            logger.warning("❌ Cannot subscribe - WebSocket not connected")
            return False
            
        try:
            payload = {"method": "subscribeNewToken"}
            await self.websocket.send(json.dumps(payload))
            self.subscribed_to_new_tokens = True
            logger.info("✅ Subscribed to new token creation")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to new tokens: {e}")
            return False

    async def subscribe_token_trades(self, token_mints: list):
        """Subscribe to trades for specific tokens"""
        if not self.websocket or not token_mints:
            return False
            
        try:
            payload = {"method": "subscribeTokenTrade", "keys": token_mints}
            await self.websocket.send(json.dumps(payload))
            
            # Track the tokens we're monitoring
            for mint in token_mints:
                self.monitored_tokens.add(mint)
            
            logger.info(f"✅ Subscribed to trades for {len(token_mints)} tokens")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to token trades: {e}")
            return False

    async def subscribe_account_trades(self, account_addresses: list):
        """Subscribe to trades by specific accounts (wallets)"""
        if not self.websocket or not account_addresses:
            return False
            
        try:
            payload = {"method": "subscribeAccountTrade", "keys": account_addresses}
            await self.websocket.send(json.dumps(payload))
            
            # Track the accounts we're monitoring
            for account in account_addresses:
                self.monitored_accounts.add(account)
            
            logger.info(f"✅ Subscribed to trades for {len(account_addresses)} accounts")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to account trades: {e}")
            return False
    
    async def unsubscribe_new_tokens(self):
        """Unsubscribe from new token creation events"""
        if not self.websocket:
            return False
            
        try:
            payload = {
                "method": "unsubscribeNewToken"
            }
            await self.websocket.send(json.dumps(payload))
            logger.info("📤 Unsubscribed from new token events")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to unsubscribe from new tokens: {e}")
            return False
    
    async def unsubscribe_token_trades(self, token_mints: list):
        """Unsubscribe from trades for specific tokens"""
        if not self.websocket or not token_mints:
            logger.warning(f"❌ Cannot unsubscribe - WebSocket not connected or no tokens provided")
            return False
            
        try:
            payload = {
                "method": "unsubscribeTokenTrade",
                "keys": token_mints
            }
            await self.websocket.send(json.dumps(payload))
            logger.info(f"📤 Unsubscribed from trades for {len(token_mints)} tokens")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to unsubscribe from token trades: {e}")
            return False
    
    async def unsubscribe_account_trades(self, account_addresses: list):
        """Unsubscribe from trades by specific accounts (wallets)"""
        if not self.websocket or not account_addresses:
            return False
            
        try:
            payload = {
                "method": "unsubscribeAccountTrade",
                "keys": account_addresses
            }
            await self.websocket.send(json.dumps(payload))
            logger.info(f"📤 Unsubscribed from trades for {len(account_addresses)} accounts")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to unsubscribe from account trades: {e}")
            return False
    
    def send_subscription_sync(self, subscription_data: dict):
        """Send subscription directly to WebSocket (synchronous, for use in WebSocket thread)"""
        try:
            if self.ws_app and self.ws_app.sock:
                logger.info(f"📤 Sending subscription via WebSocket: {subscription_data}")
                self.ws_app.send(json.dumps(subscription_data))
                logger.info("✅ Subscription sent successfully")
                return True
            else:
                logger.warning("❌ WebSocket not connected, cannot send subscription")
                return False
        except Exception as e:
            logger.error(f"❌ Error sending subscription: {e}")
            return False
    
    async def add_token_trades_subscription(self, token_mints: list):
        """Add token trades subscription after WebSocket is already running"""
        if not token_mints:
            return False
            
        try:
            subscription = {
                "method": "subscribeTokenTrade",
                "keys": token_mints
            }
            
            # Track the tokens we're monitoring
            for mint in token_mints:
                self.monitored_tokens.add(mint)
            
            # Send via the synchronous method since we're in the WebSocket thread
            success = self.send_subscription_sync(subscription)
            if success:
                logger.info(f"📊 Added token trades subscription for {len(token_mints)} tokens")
            return success
        except Exception as e:
            logger.error(f"❌ Error adding token trades subscription: {e}")
            return False
    
    async def add_account_trades_subscription(self, account_addresses: list):
        """Add account trades subscription after WebSocket is already running"""
        if not account_addresses:
            return False
            
        try:
            subscription = {
                "method": "subscribeAccountTrade",
                "keys": account_addresses
            }
            
            # Track the accounts we're monitoring
            for account in account_addresses:
                self.monitored_accounts.add(account)
            
            # Send via the synchronous method since we're in the WebSocket thread
            success = self.send_subscription_sync(subscription)
            if success:
                logger.info(f"👤 Added account trades subscription for {len(account_addresses)} addresses")
            return success
        except Exception as e:
            logger.error(f"❌ Error adding account trades subscription: {e}")
            return False
    
    # async def subscribe_all_trades(self, wallet_address: str = None):
    #     """Subscribe to all trading activity and optionally to a specific wallet"""
    #     if not self.websocket:
    #         logger.warning("❌ Cannot subscribe - WebSocket not connected")
    #         return False
    #         
    #     try:
    #         # First subscribe to new tokens
    #         subscription = {
    #             "method": "subscribeNewToken"
    #         }
    #         logger.info(f"📤 Sending new token subscription: {subscription}")
    #         await self.websocket.send(json.dumps(subscription))
    #         logger.info("✅ New token subscription sent successfully")
    #         
    #         # Wait a moment before next subscription
    #         await asyncio.sleep(0.5)
    #         
    #         # Subscribe to account trades if wallet address is provided
    #         if wallet_address:
    #             trade_subscription = {
    #                 "method": "subscribeAccountTrade",
    #                 "keys": [wallet_address]
    #             }
    #             logger.info(f"📤 Sending account trades subscription for {wallet_address}: {trade_subscription}")
    #             await self.websocket.send(json.dumps(trade_subscription))
    #             logger.info(f"✅ Account trades subscription sent successfully for {wallet_address}")
    #         else:
    #             logger.info("⚠️ No wallet address provided, skipping account trades subscription")
    #         
    #         logger.info("🎯 All subscriptions sent - waiting for confirmations...")
    #         return True
    #         
    #     except Exception as e:
    #         logger.error(f"❌ Failed to send subscriptions: {e}")
    #         logger.error(f"   Exception type: {type(e).__name__}")
    #         return False
    
    async def parse_token_data(self, data: Dict[str, Any]) -> TokenInfo:
        """Parse new token data from WebSocket"""
        # Extract the correct fields based on actual data structure
        sol_amount = data.get("solAmount", 0.0)  # This is the SOL in the initial transaction
        
        # Handle different field variations in the data
        if "vSolInBondingCurve" in data:
            # New format with bonding curve data
            v_sol_in_bonding_curve = data.get("vSolInBondingCurve", 0.0)
            v_tokens_in_bonding_curve = data.get("vTokensInBondingCurve", 0.0)
        else:
            # Old format with pool data
            v_sol_in_bonding_curve = data.get("solInPool", 0.0)
            v_tokens_in_bonding_curve = data.get("tokensInPool", 0.0)
            
        initial_buy_tokens = data.get("initialBuy", 0.0)  # Initial buy amount in tokens
        market_cap_sol = data.get("marketCapSol", 0.0)  # Market cap in SOL
        
        # Calculate price per token = SOL in bonding curve / tokens in bonding curve
        price_per_token = v_sol_in_bonding_curve / v_tokens_in_bonding_curve if v_tokens_in_bonding_curve > 0 else 0.0
        
        # Get real-time SOL price and convert market cap to USD
        sol_price_usd = await self.get_sol_price()
        market_cap_usd = market_cap_sol * sol_price_usd
        
        # Price per token in USD
        price_usd = price_per_token * sol_price_usd
        
        # Debug logging with corrected mappings
        logger.info(f"Token data parsed for {data.get('symbol', 'Unknown')}:")
        logger.info(f"  SOL amount (transaction): {sol_amount}")
        logger.info(f"  SOL in bonding curve: {v_sol_in_bonding_curve}")
        logger.info(f"  Tokens in bonding curve: {v_tokens_in_bonding_curve:,.0f}")
        logger.info(f"  Initial buy (tokens): {initial_buy_tokens:,.0f}")
        logger.info(f"  Market cap (SOL): {market_cap_sol:.4f}")
        logger.info(f"  SOL price (USD): ${sol_price_usd:.2f}")
        logger.info(f"  Market cap (USD): ${market_cap_usd:,.0f}")
        logger.info(f"  Price per token (SOL): {price_per_token:.12f}")
        logger.info(f"  Price per token (USD): ${price_usd:.12f}")
        
        # Extract liquidity and holders (if available in data)
        liquidity = data.get("liquidity", v_sol_in_bonding_curve)  # Use SOL in pool as liquidity if not specified
        holders = data.get("holders", data.get("holderCount", 0))  # Try different field names for holders
        
        logger.info(f"  Liquidity (SOL): {liquidity:.4f}")
        logger.info(f"  Holders: {holders}")
        
        token_info = TokenInfo(
            mint=data.get("mint", ""),
            name=data.get("name", ""),
            symbol=data.get("symbol", ""),
            description="",  # Not provided in this data structure
            image=data.get("uri", ""),  # URI field contains the image/metadata link
            created_timestamp=int(datetime.now().timestamp()),  # Current time since no timestamp in data
            usd_market_cap=market_cap_usd,
            market_cap=market_cap_usd,  # Use USD market cap for display
            price=price_usd,  # Price in USD
            creator=data.get("traderPublicKey", ""),  # The trader who created the token
            twitter="",
            telegram="",
            website="",
            nsfw=False,
            # Correctly mapped fields
            sol_in_pool=v_sol_in_bonding_curve,  # Total SOL in bonding curve
            tokens_in_pool=v_tokens_in_bonding_curve,  # Total tokens in bonding curve
            initial_buy=initial_buy_tokens,  # Initial buy in tokens
            sol_amount=sol_amount,  # SOL amount from transaction
            new_token_balance=0.0,  # Not available in this data
            trader_public_key=data.get("traderPublicKey", ""),
            tx_type=data.get("txType", ""),
            signature=data.get("signature", ""),
            pool=data.get("pool", ""),
            liquidity=liquidity,  # Liquidity in SOL
            holders=holders  # Number of holders
        )
        
        # Debug log the final TokenInfo object
        logger.info(f"Final TokenInfo object for {token_info.symbol}:")
        logger.info(f"  sol_in_pool: {token_info.sol_in_pool}")
        logger.info(f"  tokens_in_pool: {token_info.tokens_in_pool}")
        logger.info(f"  initial_buy: {token_info.initial_buy}")
        logger.info(f"  market_cap: ${token_info.market_cap:,.0f}")
        logger.info(f"  price: ${token_info.price:.8f}")
        
        return token_info
    
    def _process_trade_sync(self, data: Dict[str, Any]):
        """Process trade data synchronously with immediate price updates"""
        try:
            # Only process pool == 'pump'
            if data.get("pool") != "pump":
                logger.info(f"⏭️ SKIPPING - Not a pump pool (pool: {data.get('pool')})")
                return
            
            # IMMEDIATELY calculate price from websocket data before any other processing
            mint = data.get("mint", "")
            if mint:
                logger.info(f"🔍 Processing data: {data}")
                # Calculate price using bonding curve data (most accurate)
                v_sol_in_bonding_curve = data.get("vSolInBondingCurve", 0.0)
                v_tokens_in_bonding_curve = data.get("vTokensInBondingCurve", 0.0)
                
                # Calculate price immediately
                if v_sol_in_bonding_curve > 0 and v_tokens_in_bonding_curve > 0:
                    current_price_sol = v_sol_in_bonding_curve / v_tokens_in_bonding_curve
                    current_price_usd = current_price_sol * self.sol_price_usd
                    
                    logger.info(f"💰 IMMEDIATE PRICE CALCULATION for {mint}:")
                    logger.info(f"   vSolInBondingCurve: {v_sol_in_bonding_curve:.6f} SOL")
                    logger.info(f"   vTokensInBondingCurve: {v_tokens_in_bonding_curve:,.0f}")
                    logger.info(f"   Current Price: {current_price_sol:.12f} SOL (${current_price_usd:.8f})")
                    
                    # Emit price update to frontend immediately
                    self._emit_price_update(mint, current_price_sol, current_price_usd, v_sol_in_bonding_curve, v_tokens_in_bonding_curve)
                else:
                    logger.warning(f"⚠️ No bonding curve data available for price calculation: {mint}")
            
            # Parse trade data (now with price already calculated and frontend updated)
            trade_info = self.parse_trade_data(data)
            
            # Call trade callback
            if self.trade_callback:
                logger.info("📡 Calling trade callback...")
                logger.info(f"📊 Trade callback function: {self.trade_callback.__name__}")
                logger.info(f"📊 Trade callback is async: {asyncio.iscoroutinefunction(self.trade_callback)}")
                
                if asyncio.iscoroutinefunction(self.trade_callback):
                    # For async callbacks, add to queue for processing in main event loop
                    logger.info("📤 Adding async callback to queue...")
                    self.callback_queue.put((self.trade_callback, (trade_info,)))
                    logger.info(f"📤 Added async callback to queue. Queue size: {self.callback_queue.qsize()}")
                    
                    # ADDITIONAL: Try to immediately schedule the callback in the stored main event loop
                    try:
                        if hasattr(self, '_main_event_loop') and self._main_event_loop and not self._main_event_loop.is_closed():
                            logger.info("🔄 Scheduling async callback in stored main event loop...")
                            self._main_event_loop.call_soon_threadsafe(
                                lambda: asyncio.create_task(self.trade_callback(trade_info))
                            )
                            logger.info("✅ Async callback scheduled successfully in main loop")
                        else:
                            logger.warning("⚠️ No valid main event loop found, relying on queue processor")
                            logger.info(f"📊 Queue processor running: {self.callback_processor_running}")
                            logger.info(f"📊 Current queue size: {self.callback_queue.qsize()}")
                    except Exception as schedule_error:
                        logger.warning(f"⚠️ Could not schedule callback directly: {schedule_error}, relying on queue processor")
                        logger.info(f"📊 Queue processor running: {self.callback_processor_running}")
                        logger.info(f"📊 Current queue size: {self.callback_queue.qsize()}")
                    
                    # BACKUP: If queue processor is not running, execute async callback synchronously as last resort
                    if not self.callback_processor_running:
                        logger.warning("🚨 Queue processor not running! Executing async callback synchronously as BACKUP")
                        try:
                            # Create a new event loop just for this callback
                            import threading
                            
                            def run_async_callback():
                                try:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    loop.run_until_complete(self.trade_callback(trade_info))
                                    loop.close()
                                    logger.info("✅ Backup async callback completed successfully")
                                except Exception as e:
                                    logger.error(f"❌ Backup async callback failed: {e}")
                            
                            # Run in a separate thread to avoid blocking
                            backup_thread = threading.Thread(target=run_async_callback, daemon=True)
                            backup_thread.start()
                            logger.info("🔄 Started backup thread for async callback")
                            
                        except Exception as backup_error:
                            logger.error(f"❌ Backup mechanism failed: {backup_error}")
                            logger.warning("⚠️ Trade callback completely failed - this trade will be lost!")
                else:
                    # Synchronous callback - call directly
                    logger.info("🔄 Calling sync callback directly...")
                    self.trade_callback(trade_info)
                logger.info("✅ Trade callback queued/completed")
            else:
                logger.warning("⚠️ No trade callback set!")
                
        except Exception as e:
            logger.error(f"❌ Error processing trade: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
    
    def _emit_price_update(self, mint: str, price_sol: float, price_usd: float, v_sol: float, v_tokens: float):
        """Emit price update to frontend immediately"""
        try:
            # Import here to avoid circular imports
            from web_server import socketio
            
            price_update_data = {
                'mint': mint,
                'current_price_sol': price_sol,
                'current_price_usd': price_usd,
                'v_sol_in_bonding_curve': v_sol,
                'v_tokens_in_bonding_curve': v_tokens,
                'timestamp': int(time.time()),
                'source': 'websocket_trade'
            }
            
            logger.info(f"📡 Emitting price update to frontend: {mint} = {price_sol:.12f} SOL")
            socketio.emit('price_update', price_update_data)
            
            # Also call the price update callback if set
            if self.price_update_callback:
                try:
                    self.price_update_callback(mint, price_sol, price_usd)
                    logger.info(f"✅ Price update callback executed for {mint}")
                except Exception as callback_error:
                    logger.error(f"❌ Error in price update callback: {callback_error}")
            
        except Exception as e:
            logger.error(f"❌ Error emitting price update: {e}")
            # Fallback: try to use the UI callback if available
            if hasattr(self, 'ui_callback') and self.ui_callback:
                try:
                    # Emit SOL-first fields to match frontend expectations
                    self.ui_callback('price_update', {
                        'mint': mint,
                        'current_price': price_sol,            # keep legacy key but in SOL
                        'current_price_sol': price_sol,
                        'current_price_usd': price_usd
                    })
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback UI callback also failed: {fallback_error}")
    
    def parse_trade_data(self, data: Dict[str, Any]) -> TradeInfo:
        """Parse trade data from WebSocket"""
        try:
            # Extract trade information from PumpPortal data
            mint = data.get("mint", "")
            trader = data.get("traderPublicKey", data.get("trader", ""))
            
            # Determine if this is a buy or sell
            tx_type = data.get("txType", "").lower()
            is_buy = tx_type in ["buy", "swap"]
            
            # Track buy counts for tokens
            if is_buy and mint:
                if mint not in self.buy_counts:
                    self.buy_counts[mint] = 0
                self.buy_counts[mint] += 1
                logger.info(f"📈 BUY COUNT UPDATE: {{'token': '{mint}', 'count': {self.buy_counts[mint]}}}")
            
            # Extract amounts
            sol_amount = data.get("solAmount", 0.0)
            token_amount = data.get("tokenAmount", 0.0)
            
            # Price is already calculated and frontend updated in _process_trade_sync
            # Use the already calculated price from bonding curve data
            v_sol_in_bonding_curve = data.get("vSolInBondingCurve", 0.0)
            v_tokens_in_bonding_curve = data.get("vTokensInBondingCurve", 0.0)
            
            # Use bonding curve data for price calculation (most accurate)
            if v_sol_in_bonding_curve > 0 and v_tokens_in_bonding_curve > 0:
                price = v_sol_in_bonding_curve / v_tokens_in_bonding_curve
                logger.info(f"💰 Using bonding curve price: {price:.12f} SOL")
            else:
                # Fallback to transaction-based price
                price = sol_amount / token_amount if token_amount > 0 else 0.0
                logger.info(f"💰 Using transaction-based price: {price:.12f} SOL")
            
            # Get market cap if available
            market_cap_sol = data.get("marketCapSol", 0.0)
            market_cap_usd = market_cap_sol * self.sol_price_usd
            
            # Get timestamp
            timestamp = data.get("timestamp", int(datetime.now().timestamp()))
            
            # Extract token metadata from the trade data if available
            token_symbol = data.get("symbol", "Unknown")
            token_name = data.get("name", "Unknown")
            
            logger.info(f"📊 Trade parsed: {mint}")
            logger.info(f"   Trader: {trader}")
            logger.info(f"   Type: {'BUY' if is_buy else 'SELL'}")
            logger.info(f"   SOL Amount: {sol_amount}")
            logger.info(f"   Token Amount: {token_amount}")
            logger.info(f"   vSolInBondingCurve: {v_sol_in_bonding_curve}")
            logger.info(f"   vTokensInBondingCurve: {v_tokens_in_bonding_curve}")
            logger.info(f"   Calculated Price: {price:.12f} SOL")
            logger.info(f"   Token Symbol: {token_symbol}")
            logger.info(f"   Token Name: {token_name}")
            
            return TradeInfo(
                signature=data.get("signature", ""),
                mint=mint,
                trader=trader,
                is_buy=is_buy,
                amount=sol_amount,
                token_amount=token_amount,
                price=price,
                market_cap=market_cap_usd,
                timestamp=timestamp,
                token_symbol=token_symbol,  # Add token metadata
                token_name=token_name       # Add token metadata
            )
            
        except Exception as e:
            logger.error(f"❌ Error parsing trade data: {e}")
            # Return a basic trade info object
            return TradeInfo(
                signature=data.get("signature", ""),
                mint=data.get("mint", ""),
                trader=data.get("traderPublicKey", ""),
                is_buy=True,
                amount=0.0,
                token_amount=0.0,
                price=0.0,
                market_cap=0.0,
                timestamp=int(datetime.now().timestamp()),
                token_symbol="Unknown",
                token_name="Unknown"
            )
    
    async def handle_message(self, message: str):
        """Handle incoming WebSocket messages"""
        try:
            # LOG EVERY SINGLE MESSAGE RECEIVED
            logger.info(f"📥 RAW MESSAGE: {message}")
            
            data = json.loads(message)
            logger.info(f"📊 PARSED DATA: {data}")
            
            # Only process pool == 'pump'
            if data.get("pool") != "pump":
                logger.info(f"⏭️ SKIPPING - Not a pump pool (pool: {data.get('pool')})")
                return
            
            # Handle subscription confirmation messages
            if 'message' in data and 'subscribed' in data['message'].lower():
                logger.info(f"✅ Subscription confirmed: {data['message']}")
                return
            
            # Simple check: txType determines if it's a token or trade
            tx_type = data.get('txType', '')
            
            if tx_type == 'create':
                # This is a new token creation
                mint = data.get("mint", "")
                if mint in self.known_tokens:
                    logger.info(f"⏭️ Already processed token: {mint}")
                    return
                
                logger.info(f"🆕 PROCESSING NEW TOKEN: {data.get('symbol')} ({data.get('name')})")
                logger.info(f"📊 Mint: {mint}")
                
                try:
                    token = await self.parse_token_data(data)
                    self.known_tokens.add(token.mint)
                    
                    logger.info(f"🚀 NEW TOKEN PARSED: {token.symbol} ({token.name})")
                    logger.info(f"   Mint: {token.mint}")
                    logger.info(f"   Market Cap: ${token.market_cap:,.0f}")
                    logger.info(f"   Price: ${token.price:.8f}")
                    
                    if self.new_token_callback:
                        logger.info("📡 Calling new token callback...")
                        if asyncio.iscoroutinefunction(self.new_token_callback):
                            await self.new_token_callback(token)
                        else:
                            self.new_token_callback(token)
                        logger.info("✅ Token callback completed")
                    else:
                        logger.warning("⚠️ No new token callback set!")
                        
                except Exception as e:
                    logger.error(f"❌ Error parsing token data: {e}")
                    logger.error(f"   Data: {data}")
                    import traceback
                    logger.error(f"   Traceback: {traceback.format_exc()}")
                    
            elif tx_type in ['buy', 'sell']:
                # This is a trade
                logger.info(f"📊 PROCESSING TRADE: {tx_type} for {data.get('mint')}")
                self._process_trade_sync(data)
                
            else:
                logger.info(f"⏭️ Unknown txType: {tx_type}, skipping")
                        
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON DECODE ERROR: {e}")
            logger.error(f"   Raw message: {message[:200]}...")
        except Exception as e:
            logger.error(f"❌ GENERAL ERROR handling message: {e}")
            logger.error(f"   Message: {message[:200]}...")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
    
    def _process_token_sync(self, data: Dict[str, Any]):
        """Process token data synchronously"""
        try:
            # Only process pool == 'pump'
            if data.get("pool") != "pump":
                logger.info(f"⏭️ SKIPPING - Not a pump pool (pool: {data.get('pool')})")
                return
            # Extract fields like in parse_token_data but synchronously
            sol_amount = data.get("solAmount", 0.0)
            
            # Handle different field variations
            if "vSolInBondingCurve" in data:
                v_sol_in_bonding_curve = data.get("vSolInBondingCurve", 0.0)
                v_tokens_in_bonding_curve = data.get("vTokensInBondingCurve", 0.0)
            else:
                v_sol_in_bonding_curve = data.get("solInPool", 0.0)
                v_tokens_in_bonding_curve = data.get("tokensInPool", 0.0)
                
            initial_buy_tokens = data.get("initialBuy", 0.0)
            market_cap_sol = data.get("marketCapSol", 0.0)
            
            # Calculate price and market cap (use cached SOL price)
            price_per_token = v_sol_in_bonding_curve / v_tokens_in_bonding_curve if v_tokens_in_bonding_curve > 0 else 0.0
            market_cap_usd = market_cap_sol * self.sol_price_usd
            price_usd = price_per_token * self.sol_price_usd
            
            # Extract liquidity and holders (if available in data)
            liquidity = data.get("liquidity", v_sol_in_bonding_curve)  # Use SOL in pool as liquidity if not specified
            holders = data.get("holders", data.get("holderCount", 0))  # Try different field names for holders
            
            logger.info(f"  Liquidity (SOL): {liquidity:.4f}")
            logger.info(f"  Holders: {holders}")
            
            # Create TokenInfo object
            token_info = TokenInfo(
                mint=data.get("mint", ""),
                name=data.get("name", ""),
                symbol=data.get("symbol", ""),
                description="",
                image=data.get("uri", ""),
                created_timestamp=int(datetime.now().timestamp()),
                usd_market_cap=market_cap_usd,
                market_cap=market_cap_usd,
                price=price_usd,
                creator=data.get("traderPublicKey", ""),
                twitter="",
                telegram="",
                website="",
                nsfw=False,
                sol_in_pool=v_sol_in_bonding_curve,
                tokens_in_pool=v_tokens_in_bonding_curve,
                initial_buy=initial_buy_tokens,
                sol_amount=sol_amount,
                new_token_balance=0.0,
                trader_public_key=data.get("traderPublicKey", ""),
                tx_type=data.get("txType", ""),
                signature=data.get("signature", ""),
                pool=data.get("pool", ""),
                liquidity=liquidity,  # Liquidity in SOL
                holders=holders  # Number of holders
            )
            
            # Add to known tokens
            self.known_tokens.add(token_info.mint)
            
            logger.info(f"🚀 NEW TOKEN PARSED: {token_info.symbol} ({token_info.name})")
            logger.info(f"   Market Cap: ${token_info.market_cap:,.0f}")
            logger.info(f"   Price: ${token_info.price:.8f}")
            
            # Call callback
            if self.new_token_callback:
                logger.info("📡 Calling new token callback...")
                if asyncio.iscoroutinefunction(self.new_token_callback):
                    # For async callbacks, add to queue for processing in main event loop
                    self.callback_queue.put((self.new_token_callback, (token_info,)))
                    logger.info("📤 Added async token callback to queue")
                else:
                    # Synchronous callback - call directly
                    self.new_token_callback(token_info)
                logger.info("✅ Token callback queued/completed")
            else:
                logger.warning("⚠️ No new token callback set!")
                
        except Exception as e:
            logger.error(f"❌ Error processing token: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
    
    async def start_monitoring(self, initial_subscriptions: dict = None):
        """Start monitoring for new tokens and trades"""
        self.monitoring = True
        logger.info("🎯 Starting PumpPortal monitoring...")
        
        # Store the main event loop reference for cross-thread callback scheduling
        try:
            self._main_event_loop = asyncio.get_running_loop()
            logger.info(f"✅ Stored main event loop reference: {self._main_event_loop}")
        except Exception as e:
            logger.warning(f"⚠️ Could not store main event loop reference: {e}")
            self._main_event_loop = None
        
        # Start the callback processor
        await self.start_callback_processor()
        
        # Check if WebSocket is already connected
        if self.is_websocket_connected():
            logger.info("🔌 WebSocket already connected, just resubscribing...")
            
            # Store initial subscriptions to send
            self.initial_subscriptions = initial_subscriptions or {}
            
            # Send subscriptions directly to existing WebSocket
            if self.initial_subscriptions:
                logger.info(f"📤 Resubscribing with: {self.initial_subscriptions}")
                
                # Send new token subscription if requested
                if self.initial_subscriptions.get('subscribe_new_tokens', False):
                    subscription = {"method": "subscribeNewToken"}
                    logger.info(f"📤 Sending new token subscription: {subscription}")
                    self.ws_app.send(json.dumps(subscription))
                    logger.info("✅ New token subscription sent successfully")
                
                # Send account trades subscription if requested
                account_addresses = self.initial_subscriptions.get('account_addresses', [])
                if account_addresses:
                    account_subscription = {
                        "method": "subscribeAccountTrade",
                        "keys": account_addresses
                    }
                    logger.info(f"📤 Sending account trades subscription: {account_subscription}")
                    self.ws_app.send(json.dumps(account_subscription))
                    
                    # Track the accounts we're monitoring
                    for account in account_addresses:
                        self.monitored_accounts.add(account)
                    
                    logger.info(f"✅ Account trades subscription sent for {len(account_addresses)} addresses")
                
                # Send token trades subscription if requested
                token_mints = self.initial_subscriptions.get('token_mints', [])
                if token_mints:
                    token_subscription = {
                        "method": "subscribeTokenTrade",
                        "keys": token_mints
                    }
                    logger.info(f"📤 Sending token trades subscription: {token_subscription}")
                    self.ws_app.send(json.dumps(token_subscription))
                    
                    # Track the tokens we're monitoring
                    for mint in token_mints:
                        self.monitored_tokens.add(mint)
                    
                    logger.info(f"✅ Token trades subscription sent for {len(token_mints)} tokens")
            
            logger.info("✅ Resubscribed to all channels successfully")
            
            # Keep the async function alive
            while self.monitoring:
                await asyncio.sleep(1)
                
            logger.info("⏹ Stopped PumpPortal monitoring")
            return
        
        # If WebSocket is not connected, continue with original logic
        logger.info("🔌 WebSocket not connected, creating new connection...")
        
        # Store initial subscriptions to send when WebSocket opens
        self.initial_subscriptions = initial_subscriptions or {}
        
        # Use synchronous WebSocket in a thread since async hangs
        def on_message(ws, message):
            try:
                logger.info(f"📥 RAW MESSAGE: {message}")
                data = json.loads(message)
                
                # Handle subscription confirmation
                if 'message' in data and 'subscribed' in data['message'].lower():
                    logger.info(f"✅ Subscription confirmed: {data['message']}")
                    return
                
                # Simple check: txType determines if it's a token or trade
                tx_type = data.get('txType', '')
                
                if tx_type == 'create':
                    # This is a new token creation
                    mint = data.get("mint", "")
                    if mint in self.known_tokens:
                        return  # Already processed
                    
                    logger.info(f"🆕 PROCESSING NEW TOKEN: {data.get('symbol')} ({data.get('name')})")
                    self._process_token_sync(data)
                    
                elif tx_type in ['buy', 'sell']:
                    # This is a trade
                    logger.info(f"📊 PROCESSING TRADE: {tx_type} for {data.get('mint')}")
                    self._process_trade_sync(data)
                    
                else:
                    logger.info(f"⏭️ Unknown txType: {tx_type}, skipping")
                
            except Exception as e:
                logger.error(f"❌ Error handling message: {e}")
        
        def on_error(ws, error):
            logger.error(f"❌ WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("🔌 WebSocket closed")
        
        def on_open(ws):
            logger.info("✅ WebSocket opened successfully!")
            
            # Send initial subscriptions if provided
            if self.initial_subscriptions:
                logger.info(f"📤 Sending initial subscriptions: {self.initial_subscriptions}")
                
                # Send new token subscription if requested
                if self.initial_subscriptions.get('subscribe_new_tokens', False):
                    subscription = {"method": "subscribeNewToken"}
                    logger.info(f"📤 Sending new token subscription: {subscription}")
                    ws.send(json.dumps(subscription))
                    self.subscribed_to_new_tokens = True
                    logger.info("✅ New token subscription sent successfully")
                
                # Send account trades subscription if requested
                account_addresses = self.initial_subscriptions.get('account_addresses', [])
                if account_addresses:
                    account_subscription = {
                        "method": "subscribeAccountTrade",
                        "keys": account_addresses
                    }
                    logger.info(f"📤 Sending account trades subscription: {account_subscription}")
                    ws.send(json.dumps(account_subscription))
                    
                    # Track the accounts we're monitoring
                    for account in account_addresses:
                        self.monitored_accounts.add(account)
                    
                    logger.info(f"✅ Account trades subscription sent for {len(account_addresses)} addresses")
                
                # Send token trades subscription if requested
                token_mints = self.initial_subscriptions.get('token_mints', [])
                if token_mints:
                    token_subscription = {
                        "method": "subscribeTokenTrade",
                        "keys": token_mints
                    }
                    logger.info(f"📤 Sending token trades subscription: {token_subscription}")
                    ws.send(json.dumps(token_subscription))
                    
                    # Track the tokens we're monitoring
                    for mint in token_mints:
                        self.monitored_tokens.add(mint)
                    
                    logger.info(f"✅ Token trades subscription sent for {len(token_mints)} tokens")
            else:
                logger.info("⚠️ No initial subscriptions provided")
        
        # Create and run WebSocket in thread
        def run_websocket():
            logger.info("🚀 Starting synchronous WebSocket...")
            self.ws_app = websocket.WebSocketApp(
                PUMPPORTAL_WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            self.ws_app.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        
        # Start WebSocket in background thread
        ws_thread = threading.Thread(target=run_websocket)
        ws_thread.daemon = True
        ws_thread.start()
        
        logger.info("✅ Monitoring system started with synchronous WebSocket")
        
        # Keep the async function alive
        while self.monitoring:
            await asyncio.sleep(1)
            
        logger.info("⏹ Stopped PumpPortal monitoring")
    
    def unsubscribe_from_monitoring_sync(self):
        """Synchronously unsubscribe from monitoring (for use in stop_monitoring)"""
        try:
            logger.info("📤 Synchronously unsubscribing from monitoring...")
            
            if self.ws_app and self.ws_app.sock:
                # Unsubscribe from new token creation
                if self.subscribed_to_new_tokens:
                    try:
                        unsubscribe_new_tokens = {"method": "unsubscribeNewToken"}
                        self.ws_app.send(json.dumps(unsubscribe_new_tokens))
                        self.subscribed_to_new_tokens = False
                        logger.info("📤 Unsubscribed from new token creation")
                    except Exception as e:
                        logger.warning(f"⚠️ Error unsubscribing from new tokens: {e}")
                
                # Keep token and account trades subscriptions active (don't unsubscribe)
                if self.monitored_tokens:
                #     try:
                #         token_list = list(self.monitored_tokens)
                #         unsubscribe_token_trades = {
                #             "method": "unsubscribeTokenTrade", 
                #             "keys": token_list
                #         }
                #         self.ws_app.send(json.dumps(unsubscribe_token_trades))
                #         logger.info(f"📤 Unsubscribed from token trades: {token_list}")
                #         self.monitored_tokens.clear()
                #     except Exception as e:
                #         logger.warning(f"⚠️ Error unsubscribing from token trades: {e}")
                
                # # Keep account trades subscription active (don't unsubscribe)
                    logger.info(f"📡 Keeping token trades subscriptions active for: {list(self.monitored_tokens)}")
                if self.monitored_accounts:
                    logger.info(f"📡 Keeping account trades subscription active for: {list(self.monitored_accounts)}")
            
            logger.info("✅ Synchronous unsubscription completed")
            
        except Exception as e:
            logger.error(f"❌ Error in synchronous unsubscription: {e}")

    def remove_token_trade_subscription_sync(self, mint: str) -> bool:
        """Unsubscribe from a single token's trade stream synchronously."""
        try:
            if not mint:
                logger.warning(f"❌ Cannot unsubscribe - no mint provided")
                return False
            if self.ws_app and self.ws_app.sock:
                payload = {
                    "method": "unsubscribeTokenTrade",
                    "keys": [mint]
                }
                self.ws_app.send(json.dumps(payload))
                if mint in self.monitored_tokens:
                    self.monitored_tokens.discard(mint)
                logger.info(f"📤 Unsubscribed from token trades for {mint}")
                return True
            else:
                logger.warning("❌ WebSocket not connected, cannot unsubscribe token trade")
                return False
        except Exception as e:
            logger.error(f"❌ Error unsubscribing token {mint}: {e}")
            return False
    
    def stop_monitoring(self):
        """Stop monitoring but keep WebSocket connection alive"""
        logger.info("🛑 Stopping PumpPortal monitoring (keeping WebSocket alive)...")
        self.monitoring = False
        
        # Stop the callback processor
        self.stop_callback_processor()
        
        # Synchronously unsubscribe from monitoring
        self.unsubscribe_from_monitoring_sync()
        
        # Don't close the WebSocket connection - just stop the monitoring loop
        logger.info("✅ Monitoring stopped, WebSocket connection kept alive")
    
    def is_websocket_connected(self) -> bool:
        """Check if WebSocket is currently connected"""
        try:
            if self.ws_app and self.ws_app.sock:
                # Check if the socket is still open
                return self.ws_app.sock.connected
            return False
        except Exception:
            return False
    
    def close_websocket_connection(self):
        """Actually close the WebSocket connection (use this only when shutting down)"""
        logger.info("🔌 Closing WebSocket connection...")
        
        # Close the synchronous WebSocket connection
        if self.ws_app:
            try:
                logger.info("🔌 Closing WebSocket connection...")
                self.ws_app.close()
                logger.info("✅ WebSocket connection closed")
            except Exception as e:
                logger.warning(f"⚠️ Error closing WebSocket: {e}")
            finally:
                self.ws_app = None
        
        # Close websocket connection if it exists (for async version)
        if self.websocket:
            try:
                # Try to get the current event loop
                loop = asyncio.get_event_loop()
                if loop.is_running() and not loop.is_closed():
                    # If loop is running, schedule the close
                    asyncio.create_task(self.close_connection())
                else:
                    # If no loop is running or it's closed, just set websocket to None
                    logger.info("📡 Event loop closed, skipping graceful websocket close")
                    self.websocket = None
            except RuntimeError:
                # No event loop, just set to None
                logger.info("📡 No event loop available, skipping graceful websocket close")
                self.websocket = None
            except Exception as e:
                logger.warning(f"⚠️ Error during websocket cleanup: {e}")
                self.websocket = None
        
        logger.info("✅ WebSocket connection closed")
    
    async def close_connection(self):
        """Close WebSocket connection"""
        if self.websocket:
            try:
                # Close the websocket properly
                await self.websocket.close()
                logger.debug("WebSocket connection closed")
            except Exception as e:
                logger.debug(f"Error closing websocket: {e}")
            finally:
                self.websocket = None
    
    def is_token_suitable_for_sniping(self, token: TokenInfo, min_market_cap: float = 1000, max_market_cap: float = 100000) -> bool:
        """Check if token meets criteria for sniping"""
        criteria = [
            not token.nsfw,  # Not NSFW
            token.market_cap >= min_market_cap,  # Above minimum market cap
            token.market_cap <= max_market_cap,  # Below maximum market cap
            len(token.name) > 0,  # Has a name
            len(token.symbol) > 0,  # Has a symbol
            token.created_timestamp > 0,  # Valid creation time
            token.price > 0  # Has a price
        ]
        
        return all(criteria)

# For backwards compatibility
PumpFunMonitor = PumpPortalMonitor 