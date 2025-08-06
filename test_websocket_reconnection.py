#!/usr/bin/env python3
"""
Test WebSocket reconnection behavior
"""

import asyncio
import logging
from pump_fun_monitor import PumpPortalMonitor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_websocket_reconnection():
    """Test WebSocket reconnection behavior"""
    monitor = PumpPortalMonitor()
    
    initial_subscriptions = {
        'subscribe_new_tokens': True,
        'account_addresses': ['952LPLt7zzU4RGUmBoPV7zQwsCire85P12Ht6Tp8Dno9'],
        'token_mints': ['91WNez8D22NwBssQbkzjy4s2ipFrzpmn5hfvWVe2aY5p']
    }
    
    try:
        # First start
        logger.info("🚀 Starting monitoring for the first time...")
        monitoring_task1 = asyncio.create_task(
            monitor.start_monitoring(initial_subscriptions)
        )
        
        # Wait for connection
        await asyncio.sleep(5)
        
        # Check if connected
        connected = monitor.is_websocket_connected()
        logger.info(f"🔌 WebSocket connected: {connected}")
        
        # Stop monitoring (but keep WebSocket alive)
        logger.info("🛑 Stopping monitoring (keeping WebSocket alive)...")
        monitor.stop_monitoring()
        monitoring_task1.cancel()
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Check if still connected
        connected = monitor.is_websocket_connected()
        logger.info(f"🔌 WebSocket still connected after stop: {connected}")
        
        # Start monitoring again (should reuse existing connection)
        logger.info("🚀 Starting monitoring again (should reuse connection)...")
        monitoring_task2 = asyncio.create_task(
            monitor.start_monitoring(initial_subscriptions)
        )
        
        # Wait for resubscription
        await asyncio.sleep(5)
        
        # Check if still connected
        connected = monitor.is_websocket_connected()
        logger.info(f"🔌 WebSocket connected after restart: {connected}")
        
        # Stop again
        logger.info("🛑 Stopping monitoring again...")
        monitor.stop_monitoring()
        monitoring_task2.cancel()
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Now completely close the connection
        logger.info("🔌 Completely closing WebSocket connection...")
        monitor.close_websocket_connection()
        
        # Check if disconnected
        connected = monitor.is_websocket_connected()
        logger.info(f"🔌 WebSocket connected after close: {connected}")
        
        logger.info("✅ Test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
    finally:
        # Ensure everything is cleaned up
        monitor.stop_monitoring()
        monitor.close_websocket_connection()

if __name__ == "__main__":
    asyncio.run(test_websocket_reconnection()) 