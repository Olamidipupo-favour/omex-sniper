#!/usr/bin/env python3
"""
Test the complete position update flow
"""

import asyncio
import logging
from sniper_bot import SniperBot
from web_server import WebSocketHandler

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_position_flow():
    """Test the complete position update flow"""
    
    # Create a mock UI callback to track updates
    ui_updates = []
    
    def mock_ui_callback(event_type: str, data: dict):
        ui_updates.append({
            'event_type': event_type,
            'data': data
        })
        logger.info(f"📱 UI Update: {event_type} - {data}")
        
        # Simulate WebSocket emission
        if event_type == 'position_update':
            logger.info(f"📡 Simulating WebSocket emission for position_update")
            # In a real scenario, this would be sent to the frontend via SocketIO
    
    # Create bot instance
    bot = SniperBot()
    bot.set_ui_callback(mock_ui_callback)
    
    # Test token data
    test_mint = "Gwc5W5mivb9MVaBkFwUjaW5R3UL9CZChnFC54GfYpump"
    test_symbol = "Dunny"
    test_name = "Dunny Token"
    test_amount = 0.000001
    
    try:
        logger.info("🧪 Testing complete position update flow...")
        logger.info(f"📊 Test data: mint={test_mint}, symbol={test_symbol}, name={test_name}, amount={test_amount}")
        
        # Test the buy_token method
        success = await bot.buy_token(test_mint, test_amount, test_symbol, test_name)
        
        if success:
            logger.info("✅ Buy successful!")
            
            # Check if position was created
            if test_mint in bot.positions:
                position = bot.positions[test_mint]
                logger.info(f"📊 Position created:")
                logger.info(f"   Token Symbol: {position.token_symbol}")
                logger.info(f"   Token Name: {position.token_name}")
                logger.info(f"   SOL Amount: {position.sol_amount}")
                logger.info(f"   Token Amount: {position.token_amount}")
                
                # Verify metadata was set correctly
                if position.token_symbol == test_symbol and position.token_name == test_name:
                    logger.info("✅ Token metadata correctly set in position!")
                else:
                    logger.error("❌ Token metadata not set correctly!")
            else:
                logger.error("❌ Position was not created!")
        else:
            logger.error("❌ Buy failed!")
        
        # Check UI updates
        logger.info(f"📱 Total UI updates received: {len(ui_updates)}")
        for i, update in enumerate(ui_updates):
            logger.info(f"📱 Update {i+1}: {update['event_type']} - {update['data']}")
            
            # Verify the position_update event has the correct data
            if update['event_type'] == 'position_update':
                data = update['data']
                if data.get('action') == 'buy':
                    logger.info("✅ Position creation event detected!")
                    logger.info(f"   Mint: {data.get('mint')}")
                    logger.info(f"   Symbol: {data.get('token_symbol')}")
                    logger.info(f"   Name: {data.get('token_name')}")
                    logger.info(f"   SOL Amount: {data.get('sol_amount')}")
                    logger.info(f"   Token Amount: {data.get('token_amount')}")
        
        logger.info("✅ Test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_position_flow()) 