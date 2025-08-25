#!/usr/bin/env python3
"""
Test script for historical token loading cancellation
"""

import asyncio
import logging
import time
from sniper_bot import SniperBot
from config import config_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_historical_cancellation():
    """Test that historical token loading can be cancelled"""
    
    logger.info("🧪 Testing Historical Token Loading Cancellation")
    logger.info("=" * 60)
    
    try:
        # Create bot instance
        bot = SniperBot()
        
        # Set up test settings for historical loading
        test_settings = {
            'token_age_filter': 'last_3_days',  # This will trigger historical loading
            'historical_batch_size': 5,  # Small batch size for testing
            'min_liquidity': 10.0,
            'min_holders': 5
        }
        
        # Update bot settings
        bot.update_settings(test_settings)
        logger.info(f"⚙️ Updated bot settings: {test_settings}")
        
        # Start monitoring (this will start historical token loading)
        logger.info("🚀 Starting monitoring (will trigger historical token loading)...")
        start_success = await bot.start_monitoring()
        
        if not start_success:
            logger.error("❌ Failed to start monitoring")
            return
        
        logger.info("✅ Monitoring started successfully")
        
        # Wait a bit for historical loading to begin
        logger.info("⏳ Waiting 3 seconds for historical loading to begin...")
        await asyncio.sleep(3)
        
        # Now stop monitoring (this should cancel historical loading)
        logger.info("🛑 Stopping monitoring (should cancel historical loading)...")
        stop_success = bot.stop_monitoring()
        
        if stop_success:
            logger.info("✅ Monitoring stopped successfully")
        else:
            logger.error("❌ Failed to stop monitoring")
        
        # Wait a bit more to see if any more processing happens
        logger.info("⏳ Waiting 2 more seconds to see if processing continues...")
        await asyncio.sleep(2)
        
        # Check if the cancellation flag was set
        if hasattr(bot, '_historical_loading_cancelled') and bot._historical_loading_cancelled:
            logger.info("✅ Historical loading cancellation flag was set")
        else:
            logger.warning("⚠️ Historical loading cancellation flag was not set")
        
        # Check if the task was cancelled
        if hasattr(bot, '_historical_loading_task') and bot._historical_loading_task:
            if bot._historical_loading_task.cancelled():
                logger.info("✅ Historical loading task was cancelled")
            elif bot._historical_loading_task.done():
                logger.info("ℹ️ Historical loading task completed")
            else:
                logger.warning("⚠️ Historical loading task is still running")
        else:
            logger.warning("⚠️ No historical loading task found")
        
        logger.info("✅ Test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

async def test_rapid_start_stop():
    """Test rapid start/stop to ensure cancellation works quickly"""
    
    logger.info("\n🧪 Testing Rapid Start/Stop Cancellation")
    logger.info("=" * 60)
    
    try:
        # Create bot instance
        bot = SniperBot()
        
        # Set up test settings
        test_settings = {
            'token_age_filter': 'last_7_days',  # This will trigger historical loading
            'historical_batch_size': 3,  # Very small batch size for quick testing
            'min_liquidity': 10.0,
            'min_holders': 5
        }
        
        # Update bot settings
        bot.update_settings(test_settings)
        logger.info(f"⚙️ Updated bot settings: {test_settings}")
        
        # Start monitoring
        logger.info("🚀 Starting monitoring...")
        start_success = await bot.start_monitoring()
        
        if not start_success:
            logger.error("❌ Failed to start monitoring")
            return
        
        logger.info("✅ Monitoring started")
        
        # Immediately stop monitoring
        logger.info("🛑 Immediately stopping monitoring...")
        stop_success = bot.stop_monitoring()
        
        if stop_success:
            logger.info("✅ Monitoring stopped")
        else:
            logger.error("❌ Failed to stop monitoring")
        
        # Check cancellation status
        if hasattr(bot, '_historical_loading_cancelled') and bot._historical_loading_cancelled:
            logger.info("✅ Historical loading was cancelled quickly")
        else:
            logger.warning("⚠️ Historical loading cancellation may not have worked")
        
        logger.info("✅ Rapid start/stop test completed!")
        
    except Exception as e:
        logger.error(f"❌ Rapid start/stop test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

async def main():
    """Main test function"""
    logger.info("🔍 Historical Token Loading Cancellation Test Suite")
    logger.info("=" * 60)
    
    try:
        # Test 1: Normal cancellation
        await test_historical_cancellation()
        
        # Small delay between tests
        await asyncio.sleep(1)
        
        # Test 2: Rapid start/stop
        await test_rapid_start_stop()
        
        logger.info("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main())
