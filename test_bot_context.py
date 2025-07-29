#!/usr/bin/env python3
"""
Test WebSocket in bot context
"""
import asyncio
import threading
import time
import logging
from pump_fun_monitor import PumpPortalMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_in_thread():
    """Test monitoring in a thread like the bot does"""
    logger.info("🧵 Starting monitor in thread...")
    
    def run_monitor():
        """Run monitor in thread"""
        try:
            monitor = PumpPortalMonitor()
            
            # Set a simple callback
            def handle_token(token):
                logger.info(f"🆕 TOKEN IN THREAD: {token.symbol} ({token.name})")
            
            monitor.set_new_token_callback(handle_token)
            
            # Run monitoring
            logger.info("🚀 Starting monitoring in thread...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(monitor.start_monitoring())
            
        except Exception as e:
            logger.error(f"❌ Error in monitor thread: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Start in thread like the bot does
    thread = threading.Thread(target=run_monitor)
    thread.daemon = True
    thread.start()
    
    # Wait and see if it works
    logger.info("⏰ Waiting 30 seconds for tokens...")
    time.sleep(30)
    logger.info("⏹ Test complete")

if __name__ == "__main__":
    test_in_thread() 