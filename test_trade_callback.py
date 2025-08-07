#!/usr/bin/env python3
"""
Test trade callback flow
"""

import asyncio
import logging
from pump_fun_monitor import PumpPortalMonitor, TradeInfo
from sniper_bot import SniperBot

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_trade_callback():
    """Test the trade callback flow"""
    
    # Create a mock UI callback to track updates
    ui_updates = []
    
    def mock_ui_callback(event_type: str, data: dict):
        ui_updates.append({
            'event_type': event_type,
            'data': data
        })
        logger.info(f"📱 UI Update: {event_type} - {data}")
    
    # Create bot instance
    bot = SniperBot()
    bot.set_ui_callback(mock_ui_callback)
    
    # Create monitor instance
    monitor = PumpPortalMonitor()
    
    # Set up the trade callback
    monitor.set_trade_callback(bot._handle_pumpportal_trade)
    
    # Start the callback processor
    await monitor.start_callback_processor()
    
    # Create a test trade
    test_trade_info = TradeInfo(
        signature="test_signature",
        mint="F6KBNmbwFvhGeNssAjy8DWo6T2yWNp1JNRBrfx9ipump",
        trader="952LPLt7zzU4RGUmBoPV7zQwsCire85P12Ht6Tp8Dno9",
        is_buy=True,
        amount=0.00001,
        token_amount=263.804423,
        price=0.000000037907,
        market_cap=37.90709362561473,
        timestamp=1234567890,
        token_symbol="TEST",
        token_name="Test Token"
    )
    
    try:
        logger.info("🧪 Testing trade callback flow...")
        logger.info(f"📊 Test trade: {test_trade_info}")
        
        # Simulate the trade processing
        logger.info("🧪 Simulating trade processing...")
        monitor._process_trade_sync({
            "signature": test_trade_info.signature,
            "mint": test_trade_info.mint,
            "traderPublicKey": test_trade_info.trader,
            "txType": "buy",
            "tokenAmount": test_trade_info.token_amount,
            "solAmount": test_trade_info.amount,
            "pool": "pump"
        })
        
        # Wait a bit for the callback to be processed
        logger.info("⏳ Waiting for callback processing...")
        await asyncio.sleep(2)
        
        # Check if the callback was processed
        logger.info(f"📊 UI updates received: {len(ui_updates)}")
        for i, update in enumerate(ui_updates):
            logger.info(f"📱 Update {i+1}: {update['event_type']} - {update['data']}")
        
        # Check if position was created
        if test_trade_info.mint in bot.positions:
            position = bot.positions[test_trade_info.mint]
            logger.info(f"✅ Position created: {position}")
        else:
            logger.warning("⚠️ Position was not created")
        
        logger.info("✅ Test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_trade_callback()) 