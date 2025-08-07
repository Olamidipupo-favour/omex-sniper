#!/usr/bin/env python3
"""
Test position updates
"""

import asyncio
import logging
from sniper_bot import SniperBot
from pump_fun_monitor import TradeInfo

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_position_updates():
    """Test position updates from WebSocket trade data"""
    
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
    
    # Create a test position first (simulate a successful buy)
    test_mint = "7C2DVGUgTQacpTxkkrobAnYMvof5ZoJMhSvocq4apump"
    
    # Simulate position creation (this would happen after a successful buy)
    from sniper_bot import Position
    position = Position(
        token_mint=test_mint,
        token_symbol="Unknown",
        token_name="Unknown",
        entry_price=0.0,
        entry_timestamp=int(time.time()),
        sol_amount=0.00001,
        token_amount=0.0
    )
    bot.positions[test_mint] = position
    
    logger.info(f"📊 Created test position for {test_mint}")
    
    # Create a test TradeInfo object (simulating WebSocket data from your buy)
    test_trade_info = TradeInfo(
        signature="2gYreniQbNZQCnjSexm5vVdyN2kzEmEuv72aLWrJDFVGPQY6oUs6woQtCRakfeWeSvXXq8iEw9UdSmHj17zZtaBC",
        mint=test_mint,
        trader="952LPLt7zzU4RGUmBoPV7zQwsCire85P12Ht6Tp8Dno9",
        is_buy=True,
        amount=0.00001,  # SOL amount
        token_amount=354.840158,  # Token amount from your WebSocket data
        price=0.000000028182,  # SOL per token
        market_cap=2818.1712452836344,  # USD market cap
        timestamp=1234567890,
        token_symbol="TEST",  # Add token metadata
        token_name="Test Token"  # Add token metadata
    )
    
    try:
        logger.info("🧪 Testing position update from WebSocket trade data...")
        
        # Test the trade handler
        await bot._handle_pumpportal_trade(test_trade_info)
        
        # Check if position was updated
        if test_mint in bot.positions:
            updated_position = bot.positions[test_mint]
            logger.info(f"📊 Updated position:")
            logger.info(f"   Token Amount: {updated_position.token_amount:,.0f}")
            logger.info(f"   Entry Price: ${updated_position.entry_price:.8f}")
            logger.info(f"   Token Symbol: {updated_position.token_symbol}")
            logger.info(f"   Token Name: {updated_position.token_name}")
        
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
    import time
    asyncio.run(test_position_updates()) 