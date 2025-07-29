#!/usr/bin/env python3
"""
Test synchronous WebSocket connection
"""
import websocket
import json
import ssl
import logging
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_sync_websocket():
    """Test synchronous WebSocket connection"""
    
    def on_message(ws, message):
        logger.info(f"📥 MESSAGE: {message[:100]}...")
        try:
            data = json.loads(message)
            if all(field in data for field in ['mint', 'symbol', 'name']):
                if data.get('txType') == 'create':
                    logger.info(f"🆕 TOKEN: {data['symbol']} ({data['name']})")
        except:
            pass
    
    def on_error(ws, error):
        logger.error(f"❌ WebSocket error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        logger.info("🔌 WebSocket closed")
    
    def on_open(ws):
        logger.info("✅ WebSocket opened")
        # Send subscription
        subscription = {"method": "subscribeNewToken"}
        logger.info(f"📤 Sending: {subscription}")
        ws.send(json.dumps(subscription))
        logger.info("✅ Subscription sent")
    
    # Create WebSocket
    logger.info("🔌 Creating sync WebSocket...")
    ws = websocket.WebSocketApp(
        "wss://pumpportal.fun/api/data",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Run in thread
    def run_ws():
        logger.info("🚀 Starting WebSocket in thread...")
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    
    thread = threading.Thread(target=run_ws)
    thread.daemon = True
    thread.start()
    
    logger.info("⏰ Waiting 30 seconds...")
    time.sleep(30)
    logger.info("⏹ Test complete")

if __name__ == "__main__":
    test_sync_websocket() 