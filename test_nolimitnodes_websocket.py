#!/usr/bin/env python3
"""
Test Script for NoLimitNodes WebSocket Integration
Tests real-time price updates for Pump.fun tokens
"""

import asyncio
import websockets
import json
import logging
import time
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NoLimitNodesWebSocketTest:
    """Test class for NoLimitNodes WebSocket integration"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.websocket_url = f"wss://api.nolimitnodes.com/solana_mainnet?api_key={api_key}"
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.reference_id = "test-ref-123"
        
        # Test token mint addresses (known Pump.fun tokens)
        self.test_tokens = [
            "So11111111111111111111111111111111111111112",  # WSOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
        ]
    
    async def connect(self):
        """Connect to NoLimitNodes WebSocket"""
        try:
            logger.info(f"🔌 Connecting to NoLimitNodes WebSocket...")
            logger.info(f"📍 URL: {self.websocket_url}")
            
            self.websocket = await websockets.connect(
                self.websocket_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.is_connected = True
            logger.info("✅ Successfully connected to NoLimitNodes WebSocket")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            self.is_connected = False
            raise
    
    async def subscribe_to_all_tokens(self):
        """Subscribe to all token price updates"""
        if not self.is_connected or not self.websocket:
            logger.error("❌ Not connected to WebSocket")
            return False
        
        try:
            subscribe_message = {
                "method": "pumpFunTradeSubscribe",
                "params": {
                    "coinAddress": "all",
                    "referenceId": self.reference_id
                }
            }
            
            logger.info(f"📡 Subscribing to all tokens...")
            logger.info(f"📋 Subscribe message: {json.dumps(subscribe_message, indent=2)}")
            
            await self.websocket.send(json.dumps(subscribe_message))
            logger.info("✅ Subscription message sent")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to all tokens: {e}")
            return False
    
    async def subscribe_to_specific_token(self, token_address: str):
        """Subscribe to a specific token's price updates"""
        if not self.is_connected or not self.websocket:
            logger.error("❌ Not connected to WebSocket")
            return False
        
        try:
            subscribe_message = {
                "method": "pumpFunTradeSubscribe",
                "params": {
                    "coinAddress": token_address,
                    "referenceId": f"{self.reference_id}-{token_address[:8]}"
                }
            }
            
            logger.info(f"📡 Subscribing to specific token: {token_address}")
            logger.info(f"📋 Subscribe message: {json.dumps(subscribe_message, indent=2)}")
            
            await self.websocket.send(json.dumps(subscribe_message))
            logger.info(f"✅ Subscription message sent for {token_address}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to token {token_address}: {e}")
            return False
    
    async def listen_for_messages(self, duration_seconds: int = 60):
        """Listen for incoming messages for a specified duration"""
        if not self.is_connected or not self.websocket:
            logger.error("❌ Not connected to WebSocket")
            return
        
        logger.info(f"👂 Listening for messages for {duration_seconds} seconds...")
        start_time = time.time()
        message_count = 0
        
        try:
            while time.time() - start_time < duration_seconds:
                try:
                    # Set a timeout for receiving messages
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=5.0  # 5 second timeout
                    )
                    
                    message_count += 1
                    logger.info(f"📨 Message #{message_count} received:")
                    
                    try:
                        # Try to parse as JSON
                        data = json.loads(message)
                        logger.info(f"📋 Parsed JSON: {json.dumps(data, indent=2)}")
                        
                        # Check if it's a trade update
                        if "method" in data and "pumpFunTrade" in data["method"]:
                            logger.info("🎯 Trade update received!")
                            await self._process_trade_update(data)
                        elif "method" in data and "pumpFunTradeSubscribe" in data["method"]:
                            logger.info("✅ Subscription confirmation received!")
                        else:
                            logger.info("ℹ️ Other message type received")
                            
                    except json.JSONDecodeError:
                        logger.info(f"📋 Raw message (not JSON): {message}")
                    
                except asyncio.TimeoutError:
                    # No message received within timeout - this is normal
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("⚠️ WebSocket connection closed")
                    break
                except Exception as e:
                    logger.error(f"❌ Error receiving message: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"❌ Error in message listening loop: {e}")
        
        logger.info(f"👂 Finished listening. Received {message_count} messages.")
    
    async def _process_trade_update(self, data: dict):
        """Process a trade update message"""
        try:
            logger.info("🔄 Processing trade update...")
            
            # Extract relevant information
            if "params" in data:
                params = data["params"]
                
                # Log key trade information
                if "coinAddress" in params:
                    logger.info(f"🪙 Token: {params['coinAddress']}")
                
                if "price" in params:
                    logger.info(f"💰 Price: {params['price']}")
                
                if "volume" in params:
                    logger.info(f"📊 Volume: {params['volume']}")
                
                if "timestamp" in params:
                    logger.info(f"⏰ Timestamp: {params['timestamp']}")
                
                # Log the full trade data for inspection
                logger.info(f"📋 Full trade data: {json.dumps(params, indent=2)}")
            
        except Exception as e:
            logger.error(f"❌ Error processing trade update: {e}")
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("🔌 WebSocket connection closed")
            except Exception as e:
                logger.error(f"❌ Error closing WebSocket: {e}")
            finally:
                self.websocket = None
                self.is_connected = False
    
    async def run_test(self, test_duration: int = 60):
        """Run the complete test"""
        try:
            logger.info("🚀 Starting NoLimitNodes WebSocket test...")
            
            # Connect to WebSocket
            await self.connect()
            
            # Wait a moment for connection to stabilize
            await asyncio.sleep(2)
            
            # Subscribe to all tokens
            # await self.subscribe_to_all_tokens()
            
            # Wait a moment for subscription to process
            await asyncio.sleep(2)
            
            # Subscribe to a specific test token
            test_token = self.test_tokens[0]  # Use WSOL as test
            await self.subscribe_to_specific_token(test_token)
            
            # Wait a moment for subscription to process
            await asyncio.sleep(2)
            
            # Listen for messages
            await self.listen_for_messages(test_duration)
            
            logger.info("✅ Test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
        finally:
            # Always disconnect
            await self.disconnect()

async def main():
    """Main test function"""
    # Replace with your actual API key
    API_KEY = "ZI9I8ZnqHBXuuVOCMjYvQEdOO0X5cGdD"
    
    if API_KEY == "YOUR_API_KEY_HERE":
        logger.error("❌ Please replace 'YOUR_API_KEY_HERE' with your actual NoLimitNodes API key")
        logger.info("🔑 Get your API key from: https://nolimitnodes.com/")
        return
    
    # Create test instance
    test = NoLimitNodesWebSocketTest(API_KEY)
    
    # Run test for 60 seconds
    await test.run_test(test_duration=60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}") 