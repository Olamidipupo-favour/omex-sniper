#!/usr/bin/env python3
"""
Test price monitoring functionality
"""

import asyncio
import logging
from sniper_bot import SniperBot

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_price_monitoring():
    """Test price monitoring functionality"""
    
    # Create a mock UI callback
    ui_updates = []
    
    def mock_ui_callback(event_type: str, data: dict):
        ui_updates.append({
            'event_type': event_type,
            'data': data
        })
        logger.info(f"📱 UI Update: {event_type} - {data}")
    
    # Create sniper bot instance
    bot = SniperBot()
    bot.set_ui_callback(mock_ui_callback)
    
    # Test token
    test_mint = "CixKrsVtDxsCjAvWf6J8LeJcti4cxmHJvRp2pwcepump"
    
    try:
        logger.info("🧪 Testing price monitoring...")
        
        # Simulate starting price monitoring
        await bot._start_price_monitoring_for_token(test_mint)
        
        # Wait a bit to see if price updates come in
        logger.info("⏳ Waiting for price updates...")
        await asyncio.sleep(10)
        
        # Check if we got any UI updates
        logger.info(f"📊 Total UI updates received: {len(ui_updates)}")
        for i, update in enumerate(ui_updates):
            logger.info(f"📱 Update {i+1}: {update['event_type']} - {update['data']}")
        
        # Test stopping price monitoring
        logger.info("🛑 Stopping price monitoring...")
        await bot._stop_price_monitoring_for_token(test_mint)
        
        logger.info("✅ Test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
    finally:
        # Clean up
        if hasattr(bot, 'price_monitoring_tasks'):
            for mint, task in bot.price_monitoring_tasks.items():
                if not task.done():
                    task.cancel()
            bot.price_monitoring_tasks.clear()

if __name__ == "__main__":
    asyncio.run(test_price_monitoring()) 