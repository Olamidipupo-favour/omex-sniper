import asyncio
import websockets
import json
import logging
import ssl
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
    
    def parse_token_data(self, data: Dict[str, Any]) -> TokenInfo:
        """Parse new token data from WebSocket"""
        # Try all possible field names for market cap and price
        print(f"data: {data}")
        exit()
        market_cap = (
            data.get("market_cap") or
            data.get("usd_market_cap") or
            data.get("marketCap") or
            0.0
        )
        price = (
            data.get("price") or
            data.get("current_price") or
            data.get("price_usd") or
            0.0
        )
        return TokenInfo(
            mint=data.get("mint", ""),
            name=data.get("name", ""),
            symbol=data.get("symbol", ""),
            description=data.get("description", ""),
            image=data.get("image", ""),
            created_timestamp=data.get("timestamp", int(datetime.now().timestamp())),
            usd_market_cap=data.get("usd_market_cap", 0.0),
            market_cap=market_cap,
            price=price,
            creator=data.get("creator", ""),
            twitter=data.get("twitter", ""),
            telegram=data.get("telegram", ""),
            website=data.get("website", ""),
            nsfw=data.get("nsfw", False)
        )
    
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
            
            # Check if this is a new token event
            if "mint" in data and data.get("mint") not in self.known_tokens:
                # This looks like a new token
                token = self.parse_token_data(data)
                self.known_tokens.add(token.mint)
                logger.info(f"🚀 NEW TOKEN: {token}")
                
                logger.info(f"🚀 NEW TOKEN: {token.symbol} ({token.name}) - {token.mint}")
                logger.info(f"   Market Cap: ${token.market_cap:,.0f} | Price: {token.price}")
                
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
    
    async def start_monitoring(self):
        """Start monitoring for new tokens and trades"""
        self.monitoring = True
        logger.info("🎯 Starting PumpPortal monitoring...")
        
        while self.monitoring:
            try:
                # Connect if not connected
                if not self.websocket or self.websocket.closed:
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
                
                # Listen for messages
                async for message in self.websocket:
                    if not self.monitoring:
                        break
                    await self.handle_message(message)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("⚠️ WebSocket connection closed. Reconnecting...")
                self.websocket = None
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
        
        logger.info("⏹ Stopped PumpPortal monitoring")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        if self.websocket:
            asyncio.create_task(self.close_connection())
    
    async def close_connection(self):
        """Close WebSocket connection"""
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
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