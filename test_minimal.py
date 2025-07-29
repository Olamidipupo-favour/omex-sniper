#!/usr/bin/env python3
"""
Minimal test to check WebSocket connection
"""
import asyncio
import websockets
import json
import ssl
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SSL context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

async def test_connection():
    """Minimal connection test"""
    url = "wss://pumpportal.fun/api/data"
    
    logger.info(f"🔌 Connecting to {url}...")
    
    try:
        # Add timeout to connection
        websocket = await asyncio.wait_for(
            websockets.connect(url, ssl=ssl_context),
            timeout=10
        )
        
        logger.info("✅ Connected successfully!")
        
        # Send subscription
        subscription = {"method": "subscribeNewToken"}
        logger.info(f"📤 Sending: {subscription}")
        await websocket.send(json.dumps(subscription))
        logger.info("✅ Subscription sent")
        
        # Listen for a few messages
        logger.info("👂 Listening for messages...")
        
        async def listen_with_timeout():
            message_count = 0
            async for message in websocket:
                message_count += 1
                logger.info(f"📥 Message #{message_count}: {message[:100]}...")
                
                if message_count >= 5:
                    logger.info("🛑 Got 5 messages, stopping")
                    break
        
        # Listen with timeout
        await asyncio.wait_for(listen_with_timeout(), timeout=30)
        
        await websocket.close()
        logger.info("🔌 Connection closed")
        
    except asyncio.TimeoutError:
        logger.error("❌ Timeout occurred")
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection()) 