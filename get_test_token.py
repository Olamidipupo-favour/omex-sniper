#!/usr/bin/env python3
"""
Get Test Token - Find a real Pump.Fun token for testing
This script helps you find a token that actually exists on Pump.Fun
"""

import asyncio
import aiohttp
import json
import logging
import ssl
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SSL context for macOS
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

async def get_recent_tokens():
    """Get recent tokens from PumpPortal API"""
    try:
        url = "https://pumpportal.fun/api/tokens"
        
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"❌ Failed to get tokens: {response.status}")
                    return None
                    
    except Exception as e:
        logger.error(f"❌ Error getting tokens: {e}")
        return None

async def get_token_info(mint: str):
    """Get detailed info for a specific token"""
    try:
        url = f"https://pumpportal.fun/api/token/{mint}"
        
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"❌ Failed to get token info: {response.status}")
                    return None
                    
    except Exception as e:
        logger.error(f"❌ Error getting token info: {e}")
        return None

async def monitor_new_tokens():
    """Monitor for new tokens in real-time"""
    try:
        url = "wss://pumpportal.fun/api/data"
        
        import websocket
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if 'mint' in data and 'symbol' in data and 'name' in data:
                    logger.info(f"🆕 NEW TOKEN: {data['symbol']} ({data['name']})")
                    logger.info(f"   Mint: {data['mint']}")
                    logger.info(f"   Market Cap: ${data.get('marketCapSol', 0) * 100:.2f}")
                    logger.info(f"   Pool: {data.get('pool', 'unknown')}")
                    logger.info(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
                    logger.info("   " + "="*50)
            except Exception as e:
                logger.debug(f"Error parsing message: {e}")
        
        def on_error(ws, error):
            logger.error(f"❌ WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("🔌 WebSocket closed")
        
        def on_open(ws):
            logger.info("✅ WebSocket connected!")
            # Subscribe to new tokens
            subscription = {"method": "subscribeNewToken"}
            ws.send(json.dumps(subscription))
            logger.info("📡 Subscribed to new tokens")
        
        # Create WebSocket connection
        ws = websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        logger.info("🎯 Monitoring for new tokens...")
        logger.info("Press Ctrl+C to stop")
        
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        
    except KeyboardInterrupt:
        logger.info("🛑 Monitoring stopped")
    except Exception as e:
        logger.error(f"❌ Error monitoring tokens: {e}")

async def main():
    """Main function"""
    print("🔍 Pump.Fun Token Finder")
    print("=" * 50)
    print("1. Get recent tokens")
    print("2. Monitor for new tokens")
    print("3. Get info for specific token")
    print("=" * 50)
    
    choice = input("Choose option (1-3): ").strip()
    
    if choice == "1":
        logger.info("📊 Getting recent tokens...")
        tokens = await get_recent_tokens()
        
        if tokens:
            logger.info(f"✅ Found {len(tokens)} recent tokens")
            print("\nRecent tokens:")
            print("-" * 80)
            
            for i, token in enumerate(tokens[:10]):  # Show first 10
                mint = token.get('mint', 'N/A')
                symbol = token.get('symbol', 'N/A')
                name = token.get('name', 'N/A')
                market_cap = token.get('marketCapSol', 0) * 100  # Approximate USD
                
                print(f"{i+1:2d}. {symbol:10} | {name[:30]:30} | ${market_cap:8.2f} | {mint}")
            
            print("\n💡 Use one of these mint addresses for testing!")
            
        else:
            logger.error("❌ Failed to get tokens")
    
    elif choice == "2":
        await monitor_new_tokens()
    
    elif choice == "3":
        mint = input("Enter token mint address: ").strip()
        if mint:
            logger.info(f"🔍 Getting info for {mint}...")
            info = await get_token_info(mint)
            
            if info:
                logger.info("✅ Token info:")
                print(json.dumps(info, indent=2))
            else:
                logger.error("❌ Failed to get token info")
    
    else:
        logger.error("❌ Invalid choice")

if __name__ == "__main__":
    asyncio.run(main()) 