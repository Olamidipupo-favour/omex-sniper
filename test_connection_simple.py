#!/usr/bin/env python3
"""
Simple connection test with detailed logging
"""
import asyncio
import websockets
import ssl
import logging
import sys

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# SSL context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

async def test_urls():
    """Test different WebSocket URLs"""
    urls = [
        "wss://pumpportal.fun/api/data",
        "wss://frontend-api-v3.pump.fun/socket",
        "ws://echo.websocket.org"  # Known working test server
    ]
    
    for url in urls:
        logger.info(f"\n{'='*50}")
        logger.info(f"🔌 Testing URL: {url}")
        logger.info(f"{'='*50}")
        
        try:
            # Add detailed logging for each step
            logger.info("📡 Creating WebSocket connection...")
            
            if url.startswith("wss://"):
                logger.info("🔒 Using SSL context")
                websocket = await asyncio.wait_for(
                    websockets.connect(url, ssl=ssl_context), 
                    timeout=10
                )
            else:
                logger.info("🔓 No SSL")
                websocket = await asyncio.wait_for(
                    websockets.connect(url), 
                    timeout=10
                )
            
            logger.info("✅ Connection successful!")
            
            # Try to send a ping
            logger.info("📤 Sending ping...")
            await websocket.ping()
            logger.info("✅ Ping successful!")
            
            # Close connection
            await websocket.close()
            logger.info("🔌 Connection closed successfully")
            
            # If we get here, this URL works
            logger.info(f"🎉 SUCCESS: {url} is working!")
            return url
            
        except asyncio.TimeoutError:
            logger.error(f"❌ TIMEOUT: {url} - Connection timed out after 10 seconds")
        except websockets.exceptions.InvalidURI:
            logger.error(f"❌ INVALID URI: {url}")
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"❌ WEBSOCKET ERROR: {url} - {e}")
        except Exception as e:
            logger.error(f"❌ GENERAL ERROR: {url} - {type(e).__name__}: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
    
    logger.error("❌ No working WebSocket URLs found!")
    return None

if __name__ == "__main__":
    working_url = asyncio.run(test_urls())
    if working_url:
        print(f"\n🎉 Use this URL: {working_url}")
    else:
        print("\n❌ No working URLs found - network/firewall issue?") 