#!/usr/bin/env python3
"""
Test Holders Filtering - Test the new holders count and filtering functionality
"""

import asyncio
import logging
from token_filter_service import TokenFilterService
from pump_fun_monitor import PumpPortalMonitor, TokenInfo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_holders_count():
    """Test getting holders count for a specific token"""
    logger.info("🧪 Testing holders count functionality...")
    
    # Test with a known token (PUMP token from the search results)
    test_mint = "FYFHVP5ktPXxevbfD7Dqd2X6FhxRY28K4spcGFQwpump"
    
    # Test with TokenFilterService
    token_filter = TokenFilterService()
    holders_count = await token_filter.get_token_holders_count(test_mint)
    logger.info(f"✅ TokenFilterService: Found {holders_count} holders for {test_mint}")
    
    # Test with PumpPortalMonitor
    monitor = PumpPortalMonitor()
    holders_count = await monitor.get_token_holders_count(test_mint)
    logger.info(f"✅ PumpPortalMonitor: Found {holders_count} holders for {test_mint}")

async def test_token_filtering():
    """Test token filtering with holders and liquidity"""
    logger.info("🧪 Testing token filtering functionality...")
    
    # Create test tokens
    test_tokens = [
        {
            'mint': 'FYFHVP5ktPXxevbfD7Dqd2X6FhxRY28K4spcGFQwpump',
            'symbol': 'PUMP',
            'name': 'Pump Token',
            'liquidity': 150.0,  # 150 SOL
            'holders': 0,  # Will be updated by API
            'market_cap': 1000000,
            'price': 0.001,
            'created_timestamp': int(asyncio.get_event_loop().time()) - (2 * 24 * 3600)
        },
        {
            'mint': 'So11111111111111111111111111111111111111112',
            'symbol': 'WSOL',
            'name': 'Wrapped SOL',
            'liquidity': 50.0,  # 50 SOL (below threshold)
            'holders': 0,  # Will be updated by API
            'market_cap': 5000000,
            'price': 1.0,
            'created_timestamp': int(asyncio.get_event_loop().time()) - (1 * 24 * 3600)
        }
    ]
    
    # Test filtering with TokenFilterService
    token_filter = TokenFilterService()
    filtered_tokens = await token_filter.update_token_holders_and_filter(
        test_tokens, 
        min_liquidity=100.0,  # Minimum 100 SOL
        min_holders=5  # Minimum 5 holders
    )
    
    logger.info(f"✅ TokenFilterService: Filtered {len(test_tokens)} tokens to {len(filtered_tokens)}")
    for token in filtered_tokens:
        logger.info(f"   - {token['symbol']}: liquidity={token['liquidity']:.2f} SOL, holders={token['holders']}")

async def test_monitor_filtering():
    """Test filtering with PumpPortalMonitor"""
    logger.info("🧪 Testing PumpPortalMonitor filtering...")
    
    # Create test TokenInfo objects
    test_token1 = TokenInfo(
        mint='FYFHVP5ktPXxevbfD7Dqd2X6FhxRY28K4spcGFQwpump',
        symbol='PUMP',
        name='Pump Token',
        description='',
        image='',
        created_timestamp=int(asyncio.get_event_loop().time()) - (2 * 24 * 3600),
        usd_market_cap=1000000,
        market_cap=1000000,
        price=0.001,
        liquidity=150.0,  # 150 SOL
        holders=0  # Will be updated by API
    )
    
    test_token2 = TokenInfo(
        mint='So11111111111111111111111111111111111111112',
        symbol='WSOL',
        name='Wrapped SOL',
        description='',
        image='',
        created_timestamp=int(asyncio.get_event_loop().time()) - (1 * 24 * 3600),
        usd_market_cap=5000000,
        market_cap=5000000,
        price=1.0,
        liquidity=50.0,  # 50 SOL (below threshold)
        holders=0  # Will be updated by API
    )
    
    # Test filtering
    monitor = PumpPortalMonitor()
    
    # Test token 1 (should pass)
    passes1 = await monitor.update_token_holders_and_filter(
        test_token1, 
        min_liquidity=100.0, 
        min_holders=5
    )
    logger.info(f"✅ Token 1 ({test_token1.symbol}): {'PASSED' if passes1 else 'FAILED'} - liquidity={test_token1.liquidity:.2f} SOL, holders={test_token1.holders}")
    
    # Test token 2 (should fail due to low liquidity)
    passes2 = await monitor.update_token_holders_and_filter(
        test_token2, 
        min_liquidity=100.0, 
        min_holders=5
    )
    logger.info(f"✅ Token 2 ({test_token2.symbol}): {'PASSED' if passes2 else 'FAILED'} - liquidity={test_token2.liquidity:.2f} SOL, holders={test_token2.holders}")

async def main():
    """Run all tests"""
    logger.info("🚀 Starting Holders Filtering Tests...")
    logger.info("=" * 60)
    
    try:
        await test_holders_count()
        logger.info("-" * 40)
        
        await test_token_filtering()
        logger.info("-" * 40)
        
        await test_monitor_filtering()
        logger.info("-" * 40)
        
        logger.info("🎉 All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    print("🧪 Holders Filtering Test Suite")
    print("=" * 50)
    print("This script tests the new holders count and filtering functionality")
    print("including API calls to Pump.fun and filtering logic.")
    print("=" * 50)
    
    # Run the tests
    asyncio.run(main()) 