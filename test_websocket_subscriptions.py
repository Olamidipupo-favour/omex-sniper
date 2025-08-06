#!/usr/bin/env python3
"""
Test WebSocket subscriptions to verify they work properly
"""

import asyncio
import logging
from pump_fun_monitor import PumpPortalMonitor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_websocket_subscriptions():
    """Test WebSocket subscriptions"""
    monitor = PumpPortalMonitor()
    
    # Test initial subscriptions
    logger.info("🧪 Testing initial subscriptions...")
    
    initial_subscriptions = {
        # 'subscribe_new_tokens': True,
        # 'account_addresses': ['952LPLt7zzU4RGUmBoPV7zQwsCire85P12Ht6Tp8Dno9'],  # Test wallet
        'token_mints': ['91WNez8D22NwBssQbkzjy4s2ipFrzpmn5hfvWVe2aY5p']  # Test tokens
    }
    
    try:
        # Start monitoring with initial subscriptions
        logger.info("🚀 Starting monitoring with initial subscriptions...")
        
        # Start monitoring in background
        monitoring_task = asyncio.create_task(
            monitor.start_monitoring(initial_subscriptions)
        )
        
        # Wait a bit for WebSocket to connect and send subscriptions
        logger.info("⏳ Waiting for WebSocket to connect and send subscriptions...")
        await asyncio.sleep(5)
        
        # Test adding more subscriptions after WebSocket is running
        logger.info("🧪 Testing additional subscriptions...")
        
        # # Add more token trades subscription
        success = await monitor.add_token_trades_subscription(['91WNez8D22NwBssQbkzjy4s2ipFrzpmn5hfvWVe2aY5p'])
        logger.info(f"✅ Added token trades subscription: {success}")
        
        # Add more account trades subscription
        # success = await monitor.add_account_trades_subscription(['another_wallet'])
        # logger.info(f"✅ Added account trades subscription: {success}")
        
        # Wait a bit more to see if subscriptions work
        logger.info("⏳ Waiting to see if subscriptions are working...")
        await asyncio.sleep(10)
        
        # Stop monitoring
        logger.info("🛑 Stopping monitoring...")
        monitor.stop_monitoring()
        
        # Cancel the monitoring task
        monitoring_task.cancel()
        
        logger.info("✅ Test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
    finally:
        # Ensure monitoring is stopped
        monitor.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(test_websocket_subscriptions()) 