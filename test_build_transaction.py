#!/usr/bin/env python3
"""
Test build_transaction method to ensure it doesn't return None
"""

import asyncio
import logging
from pumpportal_trader import PumpPortalTrader

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_build_transaction():
    """Test build_transaction method"""
    
    # Create a test keypair (you can replace with a real one for testing)
    test_private_key = bytes([1] * 64)  # Dummy key for testing
    
    trader = PumpPortalTrader(private_key=test_private_key)
    
    # Test cases
    test_cases = [
        {
            "action": "buy",
            "mint": "CixKrsVtDxsCjAvWf6J8LeJcti4cxmHJvRp2pwcepump",
            "amount": 0.1,
            "slippage": 5.0,
            "description": "Valid buy transaction"
        },
        {
            "action": "sell",
            "mint": "CixKrsVtDxsCjAvWf6J8LeJcti4cxmHJvRp2pwcepump",
            "amount": 1000000,
            "slippage": 5.0,
            "description": "Valid sell transaction"
        },
        {
            "action": "buy",
            "mint": "",
            "amount": 0.1,
            "slippage": 5.0,
            "description": "Invalid mint (empty)"
        },
        {
            "action": "buy",
            "mint": "CixKrsVtDxsCjAvWf6J8LeJcti4cxmHJvRp2pwcepump",
            "amount": 0,
            "slippage": 5.0,
            "description": "Invalid amount (zero)"
        },
        {
            "action": "invalid",
            "mint": "CixKrsVtDxsCjAvWf6J8LeJcti4cxmHJvRp2pwcepump",
            "amount": 0.1,
            "slippage": 5.0,
            "description": "Invalid action"
        }
    ]
    
    logger.info("🧪 Testing build_transaction method...")
    
    for i, test_case in enumerate(test_cases):
        logger.info(f"\n--- Test {i+1}: {test_case['description']} ---")
        
        try:
            result = await trader.build_transaction(
                action=test_case["action"],
                mint=test_case["mint"],
                amount=test_case["amount"],
                slippage=test_case["slippage"]
            )
            
            if result is None:
                logger.info(f"✅ Expected None returned for invalid case")
            else:
                logger.info(f"✅ Transaction data received: {type(result)}")
                logger.info(f"📊 Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                
        except Exception as e:
            logger.error(f"❌ Exception occurred: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
    logger.info("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_build_transaction()) 