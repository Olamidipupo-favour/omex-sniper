#!/usr/bin/env python3
"""
Direct monitor test - exactly what the bot should do
"""
import asyncio
import websockets
import json
import ssl
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def direct_monitor():
    """Connect and monitor tokens directly"""
    url = "wss://pumpportal.fun/api/data"
    
    # SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    logger.info(f"🔌 Connecting to {url}...")
    
    try:
        # Connect with timeout
        websocket = await asyncio.wait_for(
            websockets.connect(url, ssl=ssl_context),
            timeout=15
        )
        logger.info("✅ Connected!")
        
        # Subscribe to new tokens
        subscription = {"method": "subscribeNewToken"}
        logger.info(f"📤 Sending subscription: {subscription}")
        await websocket.send(json.dumps(subscription))
        logger.info("✅ Subscription sent")
        
        # Listen for messages
        logger.info("👂 Listening for messages...")
        message_count = 0
        
        try:
            while message_count < 10:  # Stop after 10 messages for testing
                # Wait for message with timeout
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    message_count += 1
                    
                    logger.info(f"\n📨 MESSAGE #{message_count}:")
                    logger.info(f"RAW: {message}")
                    
                    # Try to parse
                    try:
                        data = json.loads(message)
                        logger.info(f"PARSED KEYS: {list(data.keys())}")
                        
                        # Check for token fields
                        if all(field in data for field in ['mint', 'symbol', 'name']):
                            logger.info(f"🆕 TOKEN FOUND: {data['symbol']} ({data['name']})")
                            logger.info(f"   Mint: {data['mint']}")
                            logger.info(f"   txType: {data.get('txType', 'N/A')}")
                            
                    except json.JSONDecodeError:
                        logger.info("   Not JSON")
                        
                except asyncio.TimeoutError:
                    logger.info("⏰ No message in 10 seconds...")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Error in message loop: {e}")
            
        await websocket.close()
        logger.info("🔌 Connection closed")
        
    except Exception as e:
        logger.error(f"❌ Connection error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(direct_monitor()) 