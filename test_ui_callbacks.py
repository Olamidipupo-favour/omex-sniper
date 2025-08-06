#!/usr/bin/env python3
"""
Test UI callback functionality
"""

import asyncio
import logging
from sniper_bot import SniperBot

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_ui_callbacks():
    """Test all UI callback types"""
    
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
    
    try:
        logger.info("🧪 Testing UI callbacks...")
        
        # Test 1: New token callback
        logger.info("📝 Testing new_token callback...")
        await bot.ui_callback('new_token', {
            'mint': 'test123',
            'symbol': 'TEST',
            'name': 'Test Token',
            'price': 0.0001,
            'market_cap': 1000
        })
        
        # Test 2: Position update callback
        logger.info("📝 Testing position_update callback...")
        await bot.ui_callback('position_update', {
            'action': 'buy',
            'mint': 'test123',
            'sol_amount': 0.1,
            'token_amount': 1000000,
            'entry_price': 0.0001
        })
        
        # Test 3: Transaction callback
        logger.info("📝 Testing transaction callback...")
        await bot.ui_callback('transaction', {
            'action': 'buy',
            'mint': 'test123',
            'sol_amount': 0.1,
            'signature': 'test_signature_123'
        })
        
        # Test 4: Transaction update callback
        logger.info("📝 Testing transaction_update callback...")
        await bot.ui_callback('transaction_update', {
            'mint': 'test123',
            'token_amount': 1000000,
            'token_amount_formatted': '1,000,000'
        })
        
        # Test 5: Price update callback
        logger.info("📝 Testing price_update callback...")
        await bot.ui_callback('price_update', {
            'mint': 'test123',
            'current_price': 0.00012,
            'current_pnl': 0.02,
            'current_pnl_percent': 20.0,
            'entry_price': 0.0001,
            'token_amount': 1000000,
            'token_symbol': 'TEST',
            'token_name': 'Test Token'
        })
        
        # Test 6: Trade update callback
        logger.info("📝 Testing trade_update callback...")
        await bot.ui_callback('trade_update', {
            'mint': 'test123',
            'txType': 'buy',
            'traderPublicKey': 'trader123',
            'solAmount': 0.1,
            'tokenAmount': 1000000
        })
        
        # Test 7: Auto buy success callback
        logger.info("📝 Testing auto_buy_success callback...")
        await bot.ui_callback('auto_buy_success', {
            'token_symbol': 'TEST',
            'token_mint': 'test123',
            'sol_amount': 0.1
        })
        
        # Test 8: Auto buy error callback
        logger.info("📝 Testing auto_buy_error callback...")
        await bot.ui_callback('auto_buy_error', {
            'token_symbol': 'TEST',
            'token_mint': 'test123',
            'error': 'insufficient_balance',
            'message': 'Not enough SOL'
        })
        
        # Check results
        logger.info(f"📊 Total UI updates received: {len(ui_updates)}")
        for i, update in enumerate(ui_updates):
            logger.info(f"📱 Update {i+1}: {update['event_type']} - {update['data']}")
        
        # Verify all expected events were received
        expected_events = [
            'new_token', 'position_update', 'transaction', 'transaction_update',
            'price_update', 'trade_update', 'auto_buy_success', 'auto_buy_error'
        ]
        
        received_events = [update['event_type'] for update in ui_updates]
        missing_events = [event for event in expected_events if event not in received_events]
        
        if missing_events:
            logger.error(f"❌ Missing events: {missing_events}")
        else:
            logger.info("✅ All expected events received!")
        
        logger.info("✅ Test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_ui_callbacks()) 