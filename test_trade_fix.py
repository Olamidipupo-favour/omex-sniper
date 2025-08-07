#!/usr/bin/env python3
"""
Test trade handling fix
"""

import asyncio
import logging
from sniper_bot import SniperBot
from pump_fun_monitor import TradeInfo

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_trade_handling():
    """Test that trade handling works properly with TradeInfo objects"""
    
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
    
    # Create a test TradeInfo object (simulating what comes from WebSocket)
    test_trade_info = TradeInfo(
        signature="test_signature_123",
        mint="test_mint_456",
        trader="test_trader_789",
        is_buy=True,
        amount=0.1,  # SOL amount
        price=0.000001,  # SOL per token
        market_cap=1000.0,  # USD market cap
        timestamp=1234567890
    )
    
    try:
        logger.info("🧪 Testing trade handling fix...")
        
        # Test the trade handler directly
        await bot._handle_pumpportal_trade(test_trade_info)
        
        # Check if we got any UI updates
        logger.info(f"📊 Total UI updates received: {len(ui_updates)}")
        for i, update in enumerate(ui_updates):
            logger.info(f"📱 Update {i+1}: {update['event_type']} - {update['data']}")
        
        # Verify the trade was added to history
        logger.info(f"📊 Trade history length: {len(bot.trade_history)}")
        if bot.trade_history:
            logger.info(f"📊 Last trade in history: {bot.trade_history[-1]}")
        
        logger.info("✅ Test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_trade_handling()) 