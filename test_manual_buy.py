#!/usr/bin/env python3
"""
Test manual buy with token metadata
"""

import asyncio
import logging
from sniper_bot import SniperBot

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_manual_buy():
    """Test manual buy with token metadata"""
    
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
    
    # Test token data
    test_mint = "7C2DVGUgTQacpTxkkrobAnYMvof5ZoJMhSvocq4apump"
    test_symbol = "TEST"
    test_name = "Test Token"
    test_amount = 0.00001
    
    try:
        logger.info("🧪 Testing manual buy with token metadata...")
        logger.info(f"📊 Test data: mint={test_mint}, symbol={test_symbol}, name={test_name}, amount={test_amount}")
        
        # Test the buy_token method directly
        success = await bot.buy_token(test_mint, test_amount, test_symbol, test_name)
        
        if success:
            logger.info("✅ Manual buy test successful!")
            
            # Check if position was created with correct metadata
            if test_mint in bot.positions:
                position = bot.positions[test_mint]
                logger.info(f"📊 Position created:")
                logger.info(f"   Token Symbol: {position.token_symbol}")
                logger.info(f"   Token Name: {position.token_name}")
                logger.info(f"   SOL Amount: {position.sol_amount}")
                logger.info(f"   Entry Price: {position.entry_price}")
                logger.info(f"   Token Amount: {position.token_amount}")
                
                # Verify metadata was set correctly
                if position.token_symbol == test_symbol and position.token_name == test_name:
                    logger.info("✅ Token metadata correctly set in position!")
                else:
                    logger.error("❌ Token metadata not set correctly!")
            else:
                logger.error("❌ Position was not created!")
        else:
            logger.error("❌ Manual buy test failed!")
        
        # Check UI updates
        logger.info(f"📱 Total UI updates received: {len(ui_updates)}")
        for i, update in enumerate(ui_updates):
            logger.info(f"📱 Update {i+1}: {update['event_type']} - {update['data']}")
        
        logger.info("✅ Test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_manual_buy()) 