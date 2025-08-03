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
    amount: float
    price: float
    market_cap: float
    timestamp: int
    
class PumpPortalMonitor:
    def __init__(self):
        self.websocket = None
        self.ws_app = None  # Add WebSocketApp instance
        self.monitoring = False
        self.new_token_callback = None
        self.trade_callback = None
        self.known_tokens = set()
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        self.sol_price_usd = 100.0  # Default fallback price
        self.last_sol_price_update = 0
        self.sol_price_cache_duration = 300  # 5 minutes
        
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
    
    def set_new_token_callback(self, callback: Callable[[TokenInfo], None]):
        """Set callback function for new token notifications"""
        self.new_token_callback = callback
    
    def set_trade_callback(self, callback: Callable[[TradeInfo], None]):
        """Set callback function for trade notifications"""
        self.trade_callback = callback
    
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
            subscription = {
                "method": "subscribeNewToken"
            }
            logger.info(f"📤 Sending subscription: {subscription}")
            await self.websocket.send(json.dumps(subscription))
            logger.info("🎯 Subscribed to new token events successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to new tokens: {e}")
            return False
    
    async def subscribe_token_trades(self, token_mints: list):
        """Subscribe to trades for specific tokens"""
        if not self.websocket or not token_mints:
            return False
            
        try:
            subscription = {
                "method": "subscribeTokenTrade",
                "keys": token_mints
            }
            await self.websocket.send(json.dumps(subscription))
            logger.info(f"📊 Subscribed to trades for {len(token_mints)} tokens")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to token trades: {e}")
            return False
    
    async def subscribe_account_trades(self, account_addresses: list):
        """Subscribe to trades by specific accounts (wallets)"""
        if not self.websocket or not account_addresses:
            return False
            
        try:
            subscription = {
                "method": "subscribeAccountTrade", 
                "keys": account_addresses
            }
            await self.websocket.send(json.dumps(subscription))
            logger.info(f"👤 Subscribed to trades for {len(account_addresses)} accounts")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to account trades: {e}")
            return False
    
    async def subscribe_all_trades(self):
        """Subscribe to all trading activity"""
        if not self.websocket:
            logger.warning("❌ Cannot subscribe - WebSocket not connected")
            return False
            
        try:
            # First subscribe to new tokens
            subscription = {
                "method": "subscribeNewToken"
            }
            logger.info(f"📤 Sending new token subscription: {subscription}")
            await self.websocket.send(json.dumps(subscription))
            logger.info("✅ New token subscription sent successfully")
            
            # Wait a moment before next subscription
            await asyncio.sleep(0.5)
            
            # Also subscribe to all trades to get real-time activity
            trade_subscription = {
                "method": "subscribeAccountTrade",
                "keys": ["all"]
            }
            logger.info(f"📤 Sending all trades subscription: {trade_subscription}")
            await self.websocket.send(json.dumps(trade_subscription))
            logger.info("✅ All trades subscription sent successfully")
            
            logger.info("🎯 All subscriptions sent - waiting for confirmations...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send subscriptions: {e}")
            logger.error(f"   Exception type: {type(e).__name__}")
            return False
    
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
        """Process trade data synchronously"""
        try:
            # Only process pool == 'pump'
            if data.get("pool") != "pump":
                logger.info(f"⏭️ SKIPPING - Not a pump pool (pool: {data.get('pool')})")
                return
            
            # Parse trade data
            trade_info = self.parse_trade_data(data)
            
            # Call trade callback
            if self.trade_callback:
                logger.info("📡 Calling trade callback...")
                if asyncio.iscoroutinefunction(self.trade_callback):
                    # For async callbacks, we need to schedule them in the event loop
                    try:
                        loop = asyncio.get_event_loop()
                        asyncio.run_coroutine_threadsafe(self.trade_callback(trade_info), loop)
                    except:
                        # If no loop available, call synchronously
                        asyncio.run(self.trade_callback(trade_info))
                else:
                    self.trade_callback(trade_info)
                logger.info("✅ Trade callback completed")
            else:
                logger.warning("⚠️ No trade callback set!")
                
        except Exception as e:
            logger.error(f"❌ Error processing trade: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
    
    def parse_trade_data(self, data: Dict[str, Any]) -> TradeInfo:
        """Parse trade data from WebSocket"""
        try:
            # Extract trade information from PumpPortal data
            mint = data.get("mint", "")
            trader = data.get("traderPublicKey", data.get("trader", ""))
            
            # Determine if this is a buy or sell
            tx_type = data.get("txType", "").lower()
            is_buy = tx_type in ["buy", "swap"]
            
            # Extract amount and price
            sol_amount = data.get("solAmount", 0.0)
            token_amount = data.get("tokenAmount", 0.0)
            
            # Calculate price (SOL per token)
            price = sol_amount / token_amount if token_amount > 0 else 0.0
            
            # Get market cap if available
            market_cap_sol = data.get("marketCapSol", 0.0)
            market_cap_usd = market_cap_sol * self.sol_price_usd
            
            # Get timestamp
            timestamp = data.get("timestamp", int(datetime.now().timestamp()))
            
            logger.info(f"📊 Trade parsed: {mint}")
            logger.info(f"   Trader: {trader}")
            logger.info(f"   Type: {'BUY' if is_buy else 'SELL'}")
            logger.info(f"   SOL Amount: {sol_amount}")
            logger.info(f"   Token Amount: {token_amount}")
            logger.info(f"   Price: {price:.12f} SOL")
            
            return TradeInfo(
                signature=data.get("signature", ""),
                mint=mint,
                trader=trader,
                is_buy=is_buy,
                amount=sol_amount,
                price=price,
                market_cap=market_cap_usd,
                timestamp=timestamp
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
                price=0.0,
                market_cap=0.0,
                timestamp=int(datetime.now().timestamp())
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
            
            # Log all data keys to see what we're getting
            logger.info(f"🔍 MESSAGE KEYS: {list(data.keys())}")
            
            # Check if this looks like token data (has the key fields we expect)
            required_fields = ['mint', 'symbol', 'name']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                logger.info(f"⏭️ SKIPPING - Missing fields: {missing_fields}")
                logger.info(f"📊 Available keys: {list(data.keys())}")
                return
            
            # Check for txType = 'create' to ensure it's a new token creation
            if data.get('txType') != 'create':
                logger.info(f"⏭️ SKIPPING - Not a token creation (txType: {data.get('txType')})")
                return
            
            # Check if we've already processed this token
            mint = data.get("mint", "")
            if mint in self.known_tokens:
                logger.info(f"⏭️ Already processed token: {mint}")
                return
            
            # Process as new token
            logger.info(f"🆕 PROCESSING NEW TOKEN: {data.get('symbol', 'Unknown')} ({data.get('name', 'Unknown')})")
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
                    # For async callbacks, we need to schedule them in the event loop
                    try:
                        loop = asyncio.get_event_loop()
                        asyncio.run_coroutine_threadsafe(self.new_token_callback(token_info), loop)
                    except:
                        # If no loop available, call synchronously
                        asyncio.run(self.new_token_callback(token_info))
                else:
                    self.new_token_callback(token_info)
                logger.info("✅ Token callback completed")
            else:
                logger.warning("⚠️ No new token callback set!")
                
        except Exception as e:
            logger.error(f"❌ Error processing token: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
    
    async def start_monitoring(self):
        """Start monitoring for new tokens and trades"""
        self.monitoring = True
        logger.info("🎯 Starting PumpPortal monitoring...")
        
        # Use synchronous WebSocket in a thread since async hangs
        def on_message(ws, message):
            try:
                logger.info(f"📥 RAW MESSAGE: {message}")
                data = json.loads(message)
                
                # Handle subscription confirmation
                if 'message' in data and 'subscribed' in data['message'].lower():
                    logger.info(f"✅ Subscription confirmed: {data['message']}")
                    return
                
                # Check for token data
                required_fields = ['mint', 'symbol', 'name']
                if not all(field in data for field in required_fields):
                    # This might be trade data, try to process it
                    if 'mint' in data and 'trader' in data:
                        self._process_trade_sync(data)
                    return
                
                # Check for token creation
                if data.get('txType') != 'create':
                    # This might be trade data, try to process it
                    if 'mint' in data and 'trader' in data:
                        self._process_trade_sync(data)
                    return
                
                # Check if already processed
                mint = data.get("mint", "")
                if mint in self.known_tokens:
                    return
                
                logger.info(f"🆕 PROCESSING NEW TOKEN: {data.get('symbol')} ({data.get('name')})")
                
                # Parse token data synchronously
                self._process_token_sync(data)
                
            except Exception as e:
                logger.error(f"❌ Error handling message: {e}")
        
        def on_error(ws, error):
            logger.error(f"❌ WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("🔌 WebSocket closed")
        
        def on_open(ws):
            logger.info("✅ WebSocket opened successfully!")
            # Send subscription
            subscription = {"method": "subscribeNewToken"}
            logger.info(f"📤 Sending subscription: {subscription}")
            ws.send(json.dumps(subscription))
            logger.info("✅ Subscription sent successfully")
        
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
    
    def _is_websocket_closed(self):
        """Check if websocket connection is closed"""
        if not self.websocket:
            return True
        
        try:
            # Try to check the connection state
            return self.websocket.closed if hasattr(self.websocket, 'closed') else False
        except Exception:
            # If we can't check the state, assume it's closed
            return True
    
    def stop_monitoring(self):
        """Stop monitoring"""
        logger.info("🛑 Stopping PumpPortal monitoring...")
        self.monitoring = False
        
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
        
        logger.info("✅ PumpPortal monitoring stopped")
    
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