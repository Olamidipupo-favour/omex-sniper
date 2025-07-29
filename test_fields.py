#!/usr/bin/env python3
"""
Test to see actual fields in PumpPortal messages
"""
import asyncio
import websockets
import json
import ssl
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

async def analyze_messages():
    """Analyze actual message structure"""
    url = "wss://pumpportal.fun/api/data"
    
    logger.info(f"🔌 Connecting to {url}...")
    
    try:
        websocket = await asyncio.wait_for(
            websockets.connect(url, ssl=ssl_context),
            timeout=10
        )
        
        logger.info("✅ Connected!")
        
        # Subscribe to new tokens
        subscription = {"method": "subscribeNewToken"}
        await websocket.send(json.dumps(subscription))
        logger.info("📤 Subscribed to new tokens")
        
        message_count = 0
        async for message in websocket:
            message_count += 1
            
            try:
                data = json.loads(message)
                
                if 'message' in data:
                    logger.info(f"📋 Confirmation: {data['message']}")
                    continue
                
                logger.info(f"\n📥 Message #{message_count}:")
                logger.info(f"   Keys: {list(data.keys())}")
                
                # Look for token-like data
                if 'mint' in data:
                    logger.info(f"   ✅ HAS MINT: {data['mint']}")
                if 'symbol' in data:
                    logger.info(f"   ✅ HAS SYMBOL: {data['symbol']}")
                if 'name' in data:
                    logger.info(f"   ✅ HAS NAME: {data['name']}")
                    
                # Show a few key fields
                for key in ['signature', 'traderPublicKey', 'txType', 'solAmount', 'marketCapSol']:
                    if key in data:
                        logger.info(f"   {key}: {data[key]}")
                
                if message_count >= 10:
                    break
                    
            except json.JSONDecodeError:
                logger.info(f"   Raw: {message[:100]}...")
        
        await websocket.close()
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(analyze_messages()) 