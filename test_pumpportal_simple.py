#!/usr/bin/env python3
"""
Simple PumpPortal WebSocket test
"""
import asyncio
import websockets
import json
import ssl

# SSL context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

async def test_pumpportal():
    """Test PumpPortal WebSocket connection"""
    url = "wss://pumpportal.fun/api/data"
    
    print(f"🔌 Connecting to {url}...")
    
    try:
        async with websockets.connect(url, ssl=ssl_context) as websocket:
            print("✅ Connected!")
            
            # Subscribe to new tokens
            subscription = {"method": "subscribeNewToken"}
            print(f"📤 Sending: {subscription}")
            await websocket.send(json.dumps(subscription))
            
            # Subscribe to all trades  
            trade_sub = {"method": "subscribeAccountTrade", "keys": ["all"]}
            print(f"📤 Sending: {trade_sub}")
            await websocket.send(json.dumps(trade_sub))
            
            print("🎯 Listening for messages...")
            
            message_count = 0
            async for message in websocket:
                message_count += 1
                print(f"\n📥 Message #{message_count}:")
                
                try:
                    data = json.loads(message)
                    print(f"   Type: {data.get('type', 'unknown')}")
                    print(f"   Keys: {list(data.keys())}")
                    
                    if len(data) < 10:
                        print(f"   Full data: {data}")
                    else:
                        print(f"   Sample: {str(data)[:200]}...")
                        
                except json.JSONDecodeError:
                    print(f"   Raw: {message[:200]}...")
                
                # Stop after 20 messages
                if message_count >= 20:
                    print("\n🛑 Stopping after 20 messages")
                    break
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_pumpportal()) 