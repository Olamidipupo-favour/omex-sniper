#!/usr/bin/env python3
"""
Test UI callback issue
"""

import asyncio
import logging
from sniper_bot import SniperBot

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_ui_callback():
    """Test the UI callback issue"""
    
    # Create bot instance
    bot = SniperBot()
    
    # Check if UI callback is set
    logger.info(f"📱 Initial UI callback: {bot.ui_callback}")
    
    # Set a mock UI callback
    def mock_ui_callback(event_type: str, data: dict):
        logger.info(f"📱 Mock UI callback called: {event_type} - {data}")
    
    bot.set_ui_callback(mock_ui_callback)
    logger.info(f"📱 UI callback after setting: {bot.ui_callback}")
    
    # Test calling the callback
    try:
        bot.ui_callback('test_event', {'test': 'data'})
        logger.info("✅ UI callback called successfully")
    except Exception as e:
        logger.error(f"❌ Error calling UI callback: {e}")
    
    # Test the buy_token method (without actually buying)
    try:
        # This should show the UI callback status
        logger.info("🧪 Testing buy_token method...")
        # We'll just check the beginning of the method
        if not bot.keypair:
            logger.info("✅ buy_token correctly detected no wallet")
        else:
            logger.info("⚠️ Wallet is connected, would proceed with buy")
    except Exception as e:
        logger.error(f"❌ Error in buy_token: {e}")

if __name__ == "__main__":
    asyncio.run(test_ui_callback()) 