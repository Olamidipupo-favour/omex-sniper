#!/usr/bin/env python3
"""
Quick test script for token holder functionality
"""

import asyncio
import logging
from helius_api import HeliusAPI
from token_filter_service import TokenFilterService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_holders():
    """Test the holder functionality"""
    try:
        # Initialize APIs
        helius = HeliusAPI()
        token_filter = TokenFilterService()
        
        # Test with the random token from your example
        test_mint = "3fMZL3tzEfmA5wy4GcLM6ndvLbusSp9WpHfVwPuypump"
        
        logger.info(f"🔍 Testing holder functionality for: {test_mint}")
        
        # Test HeliusAPI holder methods
        logger.info("\n📊 Testing HeliusAPI holder methods...")
        
        # Get full holder data
        holder_data = await helius.get_token_holders(test_mint)
        if holder_data:
            logger.info(f"✅ Full holder data: {holder_data}")
        else:
            logger.error("❌ Failed to get full holder data")
        
        # Get holder count
        holder_count = await helius.get_token_holder_count(test_mint)
        if holder_count is not None:
            logger.info(f"✅ Holder count (HeliusAPI): {holder_count}")
        else:
            logger.error("❌ Failed to get holder count from HeliusAPI")
        
        # Test TokenFilterService holder method
        logger.info("\n📊 Testing TokenFilterService holder method...")
        filter_holder_count = await token_filter.get_token_holders_count(test_mint)
        logger.info(f"✅ Holder count (TokenFilterService): {filter_holder_count}")
        
        # Test with a sample token list
        logger.info("\n📊 Testing holder filtering with sample tokens...")
        sample_tokens = [
            {
                'mint': test_mint,
                'symbol': 'TEST',
                'name': 'Test Token',
                'liquidity': 150.0  # 150 SOL liquidity
            }
        ]
        
        # Apply holder filtering
        filtered_tokens = await token_filter.update_token_holders_and_filter(
            sample_tokens, 
            min_liquidity=100.0, 
            min_holders=5
        )
        
        logger.info(f"📊 Original tokens: {len(sample_tokens)}")
        logger.info(f"📊 Filtered tokens: {len(filtered_tokens)}")
        
        for token in filtered_tokens:
            logger.info(f"✅ Token {token.get('symbol')}: {token.get('holders', 0)} holders, {token.get('liquidity', 0)} SOL liquidity")
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    logger.info("🚀 Starting holder test...")
    asyncio.run(test_holders())
    logger.info("✅ Test completed!") 