#!/usr/bin/env python3
"""
Test script to verify holder count update with SolanaTracker API
"""

import asyncio
import logging
from pump_fun_monitor import PumpFunMonitor, TokenInfo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_holders_update():
    """Test that holder count update works with SolanaTracker API"""
    try:
        logger.info("🔍 Testing holder count update with SolanaTracker API...")
        
        # Initialize the monitor
        monitor = PumpFunMonitor()
        
        # Create a test token (using a real token mint for testing)
        test_token = TokenInfo(
            mint="XszFNxKcZN5V3wocQh294xBUYYbMZxmgqodYcKzpump",  # The token from your log
            name="kidding",
            symbol="kidding",
            description="",
            image="",
            created_timestamp=1234567890,
            usd_market_cap=3591.0,
            market_cap=3591.0,
            price=0.00000359,
            liquidity=34.0,
            holders=0  # Will be updated
        )
        
        logger.info(f"📊 Initial token state:")
        logger.info(f"   Symbol: {test_token.symbol}")
        logger.info(f"   Mint: {test_token.mint}")
        logger.info(f"   Initial holders: {test_token.holders}")
        logger.info(f"   Liquidity: {test_token.liquidity} SOL")
        
        # Test the holder count update
        logger.info("🔄 Updating holder count...")
        passes_filter = await monitor.update_token_holders_and_filter(
            test_token,
            min_liquidity=10.0,  # Low threshold for testing
            min_holders=1        # Low threshold for testing
        )
        
        logger.info(f"📊 After update:")
        logger.info(f"   Updated holders: {test_token.holders}")
        logger.info(f"   Passes filter: {passes_filter}")
        
        if test_token.holders > 0:
            logger.info("✅ Holder count update successful!")
        else:
            logger.warning("⚠️ Holder count is still 0 - might be a new token or API issue")
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    logger.info("🚀 Starting holder count update test...")
    asyncio.run(test_holders_update())
    logger.info("✅ Test completed!") 