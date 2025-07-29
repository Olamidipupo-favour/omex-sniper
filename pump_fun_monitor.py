import asyncio
import websockets
import json
import logging
import ssl
import aiohttp
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
from config import Config

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
    
    async def connect_websocket(self):
        """Connect to PumpPortal WebSocket"""
        try:
            logger.info("🔌 Connecting to PumpPortal WebSocket...")
            self.websocket = await websockets.connect(
                Config.PUMPPORTAL_WS_URL,
                ssl=ssl_context,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            logger.info("✅ Connected to PumpPortal WebSocket")
            self.connection_attempts = 0
            return True
        except Exception as e:
            self.connection_attempts += 1
            logger.error(f"❌ WebSocket connection failed (attempt {self.connection_attempts}): {e}")
            return False
    
    async def subscribe_new_tokens(self):
        """Subscribe to new token creation events"""
        if not self.websocket:
            return False
            
        try:
            subscription = {
                "method": "subscribeNewToken"
            }
            await self.websocket.send(json.dumps(subscription))
            logger.info("🎯 Subscribed to new token events")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to new tokens: {e}")
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
    
    async def parse_token_data(self, data: Dict[str, Any]) -> TokenInfo:
        """Parse new token data from WebSocket"""
        # Extract the correct fields based on actual data structure
        sol_amount = data.get("solAmount", 0.0)  # This is the SOL in the initial transaction
        v_sol_in_bonding_curve = data.get("vSolInBondingCurve", 0.0)  # Total SOL in bonding curve
        v_tokens_in_bonding_curve = data.get("vTokensInBondingCurve", 0.0)  # Total tokens in bonding curve
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
            pool=data.get("pool", "")
        )
        
        # Debug log the final TokenInfo object
        logger.info(f"Final TokenInfo object for {token_info.symbol}:")
        logger.info(f"  sol_in_pool: {token_info.sol_in_pool}")
        logger.info(f"  tokens_in_pool: {token_info.tokens_in_pool}")
        logger.info(f"  initial_buy: {token_info.initial_buy}")
        logger.info(f"  market_cap: ${token_info.market_cap:,.0f}")
        logger.info(f"  price: ${token_info.price:.8f}")
        
        return token_info
    
    def parse_trade_data(self, data: Dict[str, Any]) -> TradeInfo:
        """Parse trade data from WebSocket"""
        return TradeInfo(
            signature=data.get("signature", ""),
            mint=data.get("mint", ""),
            trader=data.get("trader", ""),
            is_buy=data.get("is_buy", True),
            amount=data.get("amount", 0.0),
            price=data.get("price", 0.0),
            market_cap=data.get("market_cap", 0.0),
            timestamp=data.get("timestamp", int(datetime.now().timestamp()))
        )
    
    async def handle_message(self, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            
            # Debug: Log the raw data structure
            logger.info(f"Raw WebSocket data: {json.dumps(data, indent=2)}")
            
            # Only process tokens from "pump" pool
            pool = data.get("pool", "")
            if pool != "pump":
                logger.info(f"⏭️  Skipping token from '{pool}' pool (only processing 'pump' pool)")
                return
            
            # Check if this is a new token event
            if "mint" in data and data.get("mint") not in self.known_tokens:
                # This looks like a new token
                token = await self.parse_token_data(data)
                self.known_tokens.add(token.mint)
                
                logger.info(f"🚀 NEW TOKEN (pump pool): {token.symbol} ({token.name}) - {token.mint}")
                logger.info(f"   Market Cap: ${token.market_cap:,.0f} | Price: ${token.price:.8f}")
                
                if self.new_token_callback:
                    if asyncio.iscoroutinefunction(self.new_token_callback):
                        await self.new_token_callback(token)
                    else:
                        self.new_token_callback(token)
            
            # Check if this is a trade event
            elif "signature" in data and "trader" in data:
                trade = self.parse_trade_data(data)
                
                trade_type = "BUY" if trade.is_buy else "SELL"
                logger.info(f"💰 {trade_type}: {trade.amount:.4f} SOL on {trade.mint[:8]}...")
                
                if self.trade_callback:
                    if asyncio.iscoroutinefunction(self.trade_callback):
                        await self.trade_callback(trade)
                    else:
                        self.trade_callback(trade)
                        
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {message[:100]}...")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            logger.error(f"Message that caused error: {message[:200]}...")
    
    async def start_monitoring(self):
        """Start monitoring for new tokens and trades"""
        self.monitoring = True
        logger.info("🎯 Starting PumpPortal monitoring...")
        
        while self.monitoring:
            try:
                # Connect if not connected
                if not self.websocket or self._is_websocket_closed():
                    if not await self.connect_websocket():
                        if self.connection_attempts >= self.max_connection_attempts:
                            logger.error("❌ Max connection attempts reached. Stopping monitoring.")
                            break
                        await asyncio.sleep(5)
                        continue
                
                # Subscribe to new tokens
                if not await self.subscribe_new_tokens():
                    await asyncio.sleep(5)
                    continue
                
                # Listen for messages with proper cleanup
                try:
                    async for message in self.websocket:
                        if not self.monitoring:
                            break
                        await self.handle_message(message)
                except asyncio.CancelledError:
                    logger.info("Message listening cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in message loop: {e}")
                    await asyncio.sleep(2)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("⚠️ WebSocket connection closed. Reconnecting...")
                self.websocket = None
                await asyncio.sleep(2)
                
            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
        
        # Ensure proper cleanup
        await self.close_connection()
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
        self.monitoring = False
        
        # Close websocket connection synchronously if possible
        if self.websocket:
            try:
                # Try to get the current event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, schedule the close
                    asyncio.create_task(self.close_connection())
                else:
                    # If no loop is running, we can't close gracefully
                    # Just set websocket to None
                    self.websocket = None
            except RuntimeError:
                # No event loop, just set to None
                self.websocket = None
    
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