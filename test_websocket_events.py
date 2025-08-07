#!/usr/bin/env python3
"""
Test WebSocket events for position updates and price updates
"""

import asyncio
import logging
from sniper_bot import SniperBot

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_websocket_events():
    """Test WebSocket events for position and price updates"""
    
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
    test_mint = "afvmCcbmWSMtziQwf8rSDWdh6zpgXFcLsLV9w5mpump"
    test_symbol = "Tradwife"
    test_name = "Tradwife Token"
    test_amount = 0.00001
    
    try:
        logger.info("🧪 Testing WebSocket events...")
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
                logger.info(f"   Entry Price: {position.entry_price}")
                
                # Simulate a WebSocket trade event (metadata update)
                from pump_fun_monitor import TradeInfo
                test_trade_info = TradeInfo(
                    signature="test_signature",
                    mint=test_mint,
                    trader="952LPLt7zzU4RGUmBoPV7zQwsCire85P12Ht6Tp8Dno9",
                    is_buy=True,
                    amount=test_amount,
                    token_amount=29.559227,  # Real token amount
                    price=0.000000033830,  # Real price
                    market_cap=2818.1712452836344,
                    timestamp=1234567890,
                    token_symbol=test_symbol,
                    token_name=test_name
                )
                
                logger.info("🧪 Simulating WebSocket trade event...")
                await bot._handle_pumpportal_trade(test_trade_info)
                
                # Check if position was updated
                updated_position = bot.positions[test_mint]
                logger.info(f"📊 Updated position:")
                logger.info(f"   Token Amount: {updated_position.token_amount}")
                logger.info(f"   Entry Price: {updated_position.entry_price}")
                logger.info(f"   Token Symbol: {updated_position.token_symbol}")
                
                # Simulate a price update
                logger.info("🧪 Simulating price update...")
                await bot.helius_api.monitor_token_price(test_mint, 
                    lambda mint, price: logger.info(f"💰 Price callback: {mint} = ${price}"), 
                    interval=1)
                
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
                elif data.get('action') == 'metadata_update':
                    logger.info("✅ Position metadata update event detected!")
                    logger.info(f"   Entry Price: {data.get('entry_price')}")
                    logger.info(f"   Token Amount: {data.get('token_amount')}")
            
            # Verify the price_update event
            elif update['event_type'] == 'price_update':
                logger.info("✅ Price update event detected!")
                logger.info(f"   Current Price: {update['data'].get('current_price')}")
                logger.info(f"   P&L Percent: {update['data'].get('current_pnl_percent')}")
        
        logger.info("✅ Test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_websocket_events()) 