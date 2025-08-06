#!/usr/bin/env python3
"""
Quick test script for HeliusAPI get_token_price method
"""

import asyncio
import logging
import json
from helius_api import HeliusAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_token_price():
    """Test the get_token_price method"""
    try:
        # Initialize Helius API
        helius = HeliusAPI()
        
        # Test with a known token (USDC)
        test_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        logger.info(f"🔍 Testing SolanaTracker price for USDC: {test_mint}")
        price = await helius.get_token_price(test_mint)
        logger.info(f"💰 USDC Price (SolanaTracker): ${price}")
        
        # Test with SOL
        sol_mint = "So11111111111111111111111111111111111111112"
        logger.info(f"\n🔍 Testing SolanaTracker price for SOL: {sol_mint}")
        sol_price = await helius.get_token_price(sol_mint)
        logger.info(f"💰 SOL Price (SolanaTracker): ${sol_price}")
        
        # Test with the random token from your example
        random_mint = "3fMZL3tzEfmA5wy4GcLM6ndvLbusSp9WpHfVwPuypump"
        logger.info(f"\n🔍 Testing SolanaTracker price for random token: {random_mint}")
        random_price = await helius.get_token_price(random_mint)
        logger.info(f"💰 Random Token Price (SolanaTracker): ${random_price}")
        
        # Test price monitoring for 15 seconds (3 price checks)
        logger.info(f"\n⏱️ Testing price monitoring for {random_mint} (15 seconds)...")
        start_time = asyncio.get_event_loop().time()
        
        async def price_callback(mint, price):
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(f"📊 [{elapsed:.1f}s] Price update for {mint}: ${price}")
        
        # Start monitoring in background
        monitoring_task = asyncio.create_task(
            helius.monitor_token_price(random_mint, price_callback, interval=5)
        )
        
        # Let it run for 15 seconds
        await asyncio.sleep(15)
        
        # Cancel the monitoring task
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        
        # Test P&L calculation
        logger.info("\n🧮 Testing P&L calculation...")
        pnl_data = await helius.calculate_pnl(1.0, 1.5, 1000)  # Entry: $1, Current: $1.5, Amount: 1000
        
        if pnl_data:
            logger.info(f"✅ P&L Test: {pnl_data}")
        else:
            logger.error("❌ P&L calculation failed")
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    logger.info("🚀 Starting token price test...")
    asyncio.run(test_token_price())
    logger.info("✅ Test completed!") 