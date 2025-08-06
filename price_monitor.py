#!/usr/bin/env python3
"""
Real-time Price Monitor using WebSocket for token price updates
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, Set, Callable, Optional
from datetime import datetime
from config import HELIUS_API_KEY

logger = logging.getLogger(__name__)

class PriceMonitor:
    """WebSocket-based price monitor for real-time token price updates"""
    
    def __init__(self, api_key: str = HELIUS_API_KEY):
        self.api_key = api_key
        self.ws_url = f"wss://ws.helius.xyz/?api-key={api_key}"
        self.websocket = None
        self.is_connected = False
        self.subscribed_accounts: Set[str] = set()
        self.price_callbacks: Dict[str, Callable] = {}
        self.monitoring_task = None
        
    async def connect(self):
        """Connect to Helius WebSocket"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            self.is_connected = True
            logger.info("✅ Connected to Helius WebSocket")
            
            # Start monitoring task
            self.monitoring_task = asyncio.create_task(self._monitor_messages())
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to WebSocket: {e}")
            self.is_connected = False
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        try:
            if self.websocket:
                await self.websocket.close()
            if self.monitoring_task:
                self.monitoring_task.cancel()
            self.is_connected = False
            logger.info("✅ Disconnected from Helius WebSocket")
        except Exception as e:
            logger.error(f"❌ Error disconnecting: {e}")
    
    async def subscribe_to_token(self, mint_address: str, callback: Callable):
        """Subscribe to token price updates"""
        try:
            if not self.is_connected:
                await self.connect()
            
            # Subscribe to account changes
            subscribe_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "accountSubscribe",
                "params": [
                    mint_address,
                    {
                        "encoding": "jsonParsed",
                        "commitment": "confirmed"
                    }
                ]
            }
            
            await self.websocket.send(json.dumps(subscribe_message))
            self.subscribed_accounts.add(mint_address)
            self.price_callbacks[mint_address] = callback
            
            logger.info(f"✅ Subscribed to token price updates: {mint_address}")
            
        except Exception as e:
            logger.error(f"❌ Error subscribing to token {mint_address}: {e}")
    
    async def unsubscribe_from_token(self, mint_address: str):
        """Unsubscribe from token price updates"""
        try:
            if mint_address in self.subscribed_accounts:
                # Unsubscribe message
                unsubscribe_message = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "accountUnsubscribe",
                    "params": [mint_address]
                }
                
                await self.websocket.send(json.dumps(unsubscribe_message))
                self.subscribed_accounts.discard(mint_address)
                
                if mint_address in self.price_callbacks:
                    del self.price_callbacks[mint_address]
                
                logger.info(f"✅ Unsubscribed from token: {mint_address}")
                
        except Exception as e:
            logger.error(f"❌ Error unsubscribing from token {mint_address}: {e}")
    
    async def _monitor_messages(self):
        """Monitor incoming WebSocket messages"""
        try:
            while self.is_connected and self.websocket:
                try:
                    message = await self.websocket.recv()
                    await self._process_message(message)
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("⚠️ WebSocket connection closed, attempting to reconnect...")
                    await self._reconnect()
                except Exception as e:
                    logger.error(f"❌ Error processing WebSocket message: {e}")
                    
        except asyncio.CancelledError:
            logger.info("🛑 Price monitoring task cancelled")
        except Exception as e:
            logger.error(f"❌ Error in price monitoring task: {e}")
    
    async def _process_message(self, message: str):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            # Handle subscription confirmation
            if 'result' in data and isinstance(data['result'], int):
                logger.debug(f"📡 Subscription confirmed: {data['result']}")
                return
            
            # Handle account updates
            if 'params' in data and 'result' in data['params']:
                result = data['params']['result']
                
                if 'value' in result:
                    account_data = result['value']
                    account_address = result.get('account', '')
                    
                    # Check if this is a token account we're monitoring
                    if account_address in self.subscribed_accounts:
                        await self._handle_token_update(account_address, account_data)
                        
        except json.JSONDecodeError:
            logger.warning("⚠️ Invalid JSON message received")
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
    
    async def _handle_token_update(self, account_address: str, account_data: Dict):
        """Handle token account update"""
        try:
            # Extract token balance and price info
            if 'data' in account_data and 'parsed' in account_data['data']:
                parsed_data = account_data['data']['parsed']
                
                if 'info' in parsed_data:
                    info = parsed_data['info']
                    token_amount = float(info.get('tokenAmount', {}).get('uiAmount', 0))
                    
                    # Get current price from callback
                    if account_address in self.price_callbacks:
                        callback = self.price_callbacks[account_address]
                        await callback(account_address, token_amount)
                        
                        logger.debug(f"📊 Token update - {account_address}: {token_amount}")
                        
        except Exception as e:
            logger.error(f"❌ Error handling token update: {e}")
    
    async def _reconnect(self):
        """Reconnect to WebSocket"""
        try:
            await self.disconnect()
            await asyncio.sleep(5)  # Wait before reconnecting
            await self.connect()
            
            # Resubscribe to all accounts
            for mint_address in list(self.subscribed_accounts):
                if mint_address in self.price_callbacks:
                    await self.subscribe_to_token(mint_address, self.price_callbacks[mint_address])
                    
        except Exception as e:
            logger.error(f"❌ Error reconnecting: {e}")
    
    async def get_current_price(self, mint_address: str) -> Optional[float]:
        """Get current token price (fallback to REST API)"""
        try:
            # This is a fallback method - in real implementation, you'd use Helius API
            # For now, return None to indicate price not available
            return None
        except Exception as e:
            logger.error(f"❌ Error getting current price: {e}")
            return None 