#!/usr/bin/env python3
"""
Test Token Filter Service - Comprehensive testing for token age filtering and discovery
"""

import asyncio
import logging
import time
from token_filter_service import TokenFilterService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TokenFilterTester:
    """Test class for TokenFilterService"""
    
    def __init__(self):
        # Initialize with public Solana RPC for testing
        self.token_filter = TokenFilterService(helius_rpc_url="https://api.mainnet-beta.solana.com")
        
    async def test_age_calculation(self):
        """Test token age calculation"""
        logger.info("🧪 Testing age calculation...")
        
        # Test current time
        current_time = int(time.time())
        age_info = await self.token_filter.get_token_age_info(
            mint="test_mint",
            symbol="TEST",
            name="Test Token",
            created_timestamp=current_time
        )
        
        logger.info(f"✅ Current time token age: {age_info.age_days:.2f} days")
        
        # Test 1 day old token
        one_day_ago = current_time - (24 * 3600)
        age_info = await self.token_filter.get_token_age_info(
            mint="test_mint_1day",
            symbol="TEST1",
            name="Test Token 1 Day",
            created_timestamp=one_day_ago
        )
        
        logger.info(f"✅ 1 day old token age: {age_info.age_days:.2f} days")
        
        # Test 7 days old token
        seven_days_ago = current_time - (7 * 24 * 3600)
        age_info = await self.token_filter.get_token_age_info(
            mint="test_mint_7days",
            symbol="TEST7",
            name="Test Token 7 Days",
            created_timestamp=seven_days_ago
        )
        
        logger.info(f"✅ 7 days old token age: {age_info.age_days:.2f} days")
    
    async def test_age_filtering(self):
        """Test age-based token filtering"""
        logger.info("🧪 Testing age filtering...")
        
        # Create test tokens with different ages
        current_time = int(time.time())
        test_tokens = [
            {
                'mint': 'token_new',
                'symbol': 'NEW',
                'name': 'New Token',
                'created_timestamp': current_time - 1800,  # 30 minutes ago
                'market_cap': 1000,
                'price': 0.001,
                'liquidity': 100,
                'holders': 10
            },
            {
                'mint': 'token_1day',
                'symbol': 'DAY1',
                'name': '1 Day Token',
                'created_timestamp': current_time - (24 * 3600),  # 1 day ago
                'market_cap': 2000,
                'price': 0.002,
                'liquidity': 200,
                'holders': 20
            },
            {
                'mint': 'token_7days',
                'symbol': 'DAY7',
                'name': '7 Days Token',
                'created_timestamp': current_time - (7 * 24 * 3600),  # 7 days ago
                'market_cap': 3000,
                'price': 0.003,
                'liquidity': 300,
                'holders': 30
            },
            {
                'mint': 'token_old',
                'symbol': 'OLD',
                'name': 'Old Token',
                'created_timestamp': current_time - (30 * 24 * 3600),  # 30 days ago
                'market_cap': 4000,
                'price': 0.004,
                'liquidity': 400,
                'holders': 40
            }
        ]
        
        # Test different filter types
        filter_tests = [
            ("new_only", "Newly created only"),
            ("last_1_day", "Last 1 day"),
            ("last_7_days", "Last 7 days"),
            ("last_30_days", "Last 30 days"),
            ("custom_days", "Custom 5 days")
        ]
        
        for filter_type, description in filter_tests:
            if filter_type == "custom_days":
                filtered = self.token_filter.filter_tokens_by_age(test_tokens, filter_type, custom_days=5)
            else:
                filtered = self.token_filter.filter_tokens_by_age(test_tokens, filter_type)
            
            logger.info(f"✅ {description}: {len(filtered)} tokens passed filter")
            for token in filtered:
                logger.info(f"   - {token['symbol']}: {token.get('age_days', 0):.1f} days old")
    
    async def test_simple_token_discovery(self):
        """Test simple token discovery"""
        logger.info("🧪 Testing simple token discovery...")
        
        # Test different time ranges
        for days in [1, 3, 7, 14]:
            tokens = await self.token_filter.get_recent_tokens_simple(days)
            logger.info(f"✅ Simple discovery ({days} days): Found {len(tokens)} tokens")
            
            for token in tokens:
                age_days = (time.time() - token['created_timestamp']) / (24 * 3600)
                logger.info(f"   - {token['symbol']}: {age_days:.1f} days old, Source: {token['source']}")
    
    async def test_pump_fun_api(self):
        """Test Pump.fun API integration"""
        logger.info("🧪 Testing Pump.fun API...")
        
        # Test with a known token (Wrapped SOL)
        wsol_mint = "So11111111111111111111111111111111111111112"
        pump_info = await self.token_filter.get_pump_token_info(wsol_mint)
        
        if pump_info:
            logger.info(f"✅ Pump.fun API: Found WSOL token")
            logger.info(f"   - Data: {pump_info}")
        else:
            logger.info(f"ℹ️ Pump.fun API: WSOL not found (this is normal)")
        
        # Test with a non-existent token
        fake_mint = "FakeTokenMintAddress123456789"
        pump_info = await self.token_filter.get_pump_token_info(fake_mint)
        
        if pump_info is None:
            logger.info(f"✅ Pump.fun API: Correctly returned None for fake token")
        else:
            logger.warning(f"⚠️ Pump.fun API: Unexpectedly found fake token")
    
    async def test_hybrid_discovery(self):
        """Test hybrid token discovery"""
        logger.info("🧪 Testing hybrid token discovery...")
        
        # Test with different configurations
        test_configs = [
            (7, False, "7 days, include all sources"),
            (14, True, "14 days, pump.fun only"),
            (3, False, "3 days, include all sources")
        ]
        
        for days, pump_only, description in test_configs:
            logger.info(f"🔍 Testing: {description}")
            tokens = await self.token_filter.get_hybrid_recent_tokens(days, include_pump_only=pump_only)
            
            logger.info(f"✅ Hybrid discovery: Found {len(tokens)} tokens")
            
            # Group by source
            sources = {}
            for token in tokens:
                source = token.get('source', 'unknown')
                if source not in sources:
                    sources[source] = []
                sources[source].append(token['symbol'])
            
            for source, symbols in sources.items():
                logger.info(f"   - {source}: {len(symbols)} tokens ({', '.join(symbols[:3])}{'...' if len(symbols) > 3 else ''})")
    
    async def test_token_enrichment(self):
        """Test token enrichment with age info"""
        logger.info("🧪 Testing token enrichment...")
        
        # Test token data
        test_token = {
            'mint': 'test_enrichment_mint',
            'symbol': 'ENRICH',
            'name': 'Enrichment Test Token',
            'created_timestamp': int(time.time()) - (2 * 24 * 3600),  # 2 days ago
            'market_cap': 5000,
            'price': 0.005,
            'liquidity': 500,
            'holders': 50
        }
        
        # Enrich the token
        enriched = await self.token_filter.enrich_token_with_age_info(test_token)
        
        logger.info(f"✅ Token enrichment completed")
        logger.info(f"   - Original: {test_token}")
        logger.info(f"   - Enriched: {enriched}")
        logger.info(f"   - Age: {enriched.get('age_days', 0):.1f} days")
        logger.info(f"   - On Pump.fun: {enriched.get('is_on_pump', False)}")
    
    async def test_filter_descriptions(self):
        """Test filter description generation"""
        logger.info("🧪 Testing filter descriptions...")
        
        filter_types = [
            "new_only",
            "last_1_day", 
            "last_3_days",
            "last_7_days",
            "last_14_days",
            "last_30_days",
            "custom_days"
        ]
        
        for filter_type in filter_types:
            if filter_type == "custom_days":
                description = self.token_filter.get_filter_description(filter_type, custom_days=10)
            else:
                description = self.token_filter.get_filter_description(filter_type)
            
            logger.info(f"✅ {filter_type}: {description}")
    
    async def test_helius_integration(self):
        """Test Helius RPC integration (basic connectivity)"""
        logger.info("🧪 Testing Helius RPC integration...")
        
        try:
            # Test basic connectivity
            test_mint = "So11111111111111111111111111111111111111112"  # WSOL
            creation_time = await self.token_filter.get_token_creation_time_from_helius(test_mint)
            
            if creation_time:
                age_days = (time.time() - creation_time) / (24 * 3600)
                logger.info(f"✅ Helius RPC: Got creation time for WSOL")
                logger.info(f"   - Creation time: {creation_time}")
                logger.info(f"   - Age: {age_days:.1f} days")
            else:
                logger.info(f"ℹ️ Helius RPC: No creation time found for WSOL (this is normal)")
                
        except Exception as e:
            logger.warning(f"⚠️ Helius RPC test failed: {e}")
            logger.info("   This is expected when using public Solana RPC")
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("🚀 Starting TokenFilterService tests...")
        logger.info("=" * 60)
        
        try:
            # Run all test methods
            await self.test_age_calculation()
            logger.info("-" * 40)
            
            await self.test_age_filtering()
            logger.info("-" * 40)
            
            await self.test_simple_token_discovery()
            logger.info("-" * 40)
            
            await self.test_pump_fun_api()
            logger.info("-" * 40)
            
            await self.test_hybrid_discovery()
            logger.info("-" * 40)
            
            await self.test_token_enrichment()
            logger.info("-" * 40)
            
            await self.test_filter_descriptions()
            logger.info("-" * 40)
            
            await self.test_helius_integration()
            logger.info("-" * 40)
            
            logger.info("🎉 All tests completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")

async def main():
    """Main test function"""
    tester = TokenFilterTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    print("🧪 TokenFilterService Test Suite")
    print("=" * 50)
    print("This script tests all functionality of the TokenFilterService")
    print("including age filtering, token discovery, and API integration.")
    print("=" * 50)
    
    # Run the tests
    asyncio.run(main()) 