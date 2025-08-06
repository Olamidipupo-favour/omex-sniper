#!/usr/bin/env python3
"""
Test unsubscription functionality
"""

import asyncio
import logging
from pump_fun_monitor import PumpPortalMonitor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_unsubscription():
    """Test unsubscription functionality"""
    monitor = PumpPortalMonitor()
    
    initial_subscriptions = {
        'subscribe_new_tokens': True,
        'account_addresses': ['952LPLt7zzU4RGUmBoPV7zQwsCire85P12Ht6Tp8Dno9'],
        'token_mints': ['91WNez8D22NwBssQbkzjy4s2ipFrzpmn5hfvWVe2aY5p']
    }
    
    try:
        # Start monitoring
        logger.info("🚀 Starting monitoring...")
        monitoring_task = asyncio.create_task(
            monitor.start_monitoring(initial_subscriptions)
        )
        
        # Wait for connection and subscriptions
        await asyncio.sleep(5)
        
        # Check what we're monitoring
        logger.info(f"📊 Monitoring new tokens: {monitor.subscribed_to_new_tokens}")
        logger.info(f"📊 Monitoring tokens: {list(monitor.monitored_tokens)}")
        logger.info(f"📊 Monitoring accounts: {list(monitor.monitored_accounts)}")
        
        # Add more token subscriptions
        logger.info("🧪 Adding more token subscriptions...")
        await monitor.add_token_trades_subscription(['new_token_1', 'new_token_2'])
        
        # Check updated monitoring
        logger.info(f"📊 Updated monitoring tokens: {list(monitor.monitored_tokens)}")
        
        # Stop monitoring (should unsubscribe)
        logger.info("🛑 Stopping monitoring...")
        monitor.stop_monitoring()
        monitoring_task.cancel()
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Check what we're still monitoring
        logger.info(f"📊 After stop - Monitoring new tokens: {monitor.subscribed_to_new_tokens}")
        logger.info(f"📊 After stop - Monitoring tokens: {list(monitor.monitored_tokens)}")
        logger.info(f"📊 After stop - Monitoring accounts: {list(monitor.monitored_accounts)}")
        
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
    asyncio.run(test_unsubscription()) 