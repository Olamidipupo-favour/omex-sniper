#!/usr/bin/env python3
"""
Debug trader issue
"""

import asyncio
import logging
from pumpportal_trader import PumpPortalTrader
import base58

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_trader():
    """Test the trader buy_token method"""
    
    # Create trader instance
    trader = PumpPortalTrader()
    
    # Test without wallet set
    logger.info("🧪 Testing trader without wallet...")
    try:
        result = await trader.buy_token("test_mint", 0.1)
        logger.info(f"Result without wallet: {result}")
    except Exception as e:
        logger.error(f"Error without wallet: {e}")
    
    # Set a test wallet (you'll need to provide a real private key)
    # For testing, we'll just check if the method exists and can be called
    logger.info("🧪 Testing trader method signature...")
    
    # Check if the method exists
    if hasattr(trader, 'buy_token'):
        logger.info("✅ buy_token method exists")
        
        # Check the method signature
        import inspect
        sig = inspect.signature(trader.buy_token)
        logger.info(f"📋 Method signature: {sig}")
        
        # Check return type annotation
        return_annotation = trader.buy_token.__annotations__.get('return', 'No annotation')
        logger.info(f"📋 Return type annotation: {return_annotation}")
        
    else:
        logger.error("❌ buy_token method does not exist")

if __name__ == "__main__":
    asyncio.run(test_trader()) 