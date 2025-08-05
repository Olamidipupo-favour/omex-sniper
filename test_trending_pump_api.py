#!/usr/bin/env python3
"""
Test Pump.fun Trending/Runners API Endpoint
"""

import asyncio
import json
import logging
import time
from typing import Dict, List
from token_filter_service import TokenFilterService
from config import HELIUS_RPC_URL

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TrendingPumpAPITester:
    """Test the Pump.fun trending/runners API endpoint"""
    
    def __init__(self):
        self.token_service = TokenFilterService(helius_rpc_url=HELIUS_RPC_URL)
    
    async def test_trending_pump_api(self) -> Dict:
        """Test the Pump.fun trending/runners API endpoint"""
        logger.info("🧪 Testing Pump.fun Trending/Runners API...")
        
        try:
            # Test the trending endpoint
            tokens = await self.token_service.get_trending_pump_tokens(days=7)
            
            result = {
                "success": True,
                "tokens_found": len(tokens),
                "tokens": tokens,
                "error": None
            }
            
            logger.info(f"✅ Pump.fun Trending API: Found {len(tokens)} tokens")
            
            if tokens:
                logger.info("📋 Sample trending tokens:")
                for i, token in enumerate(tokens[:5]):  # Show first 5 tokens
                    logger.info(f"   {i+1}. {token.get('symbol', 'N/A')} ({token.get('name', 'N/A')})")
                    logger.info(f"      Mint: {token.get('mint', 'N/A')}")
                    logger.info(f"      Market Cap: ${token.get('usd_market_cap', 0):,.2f}")
                    logger.info(f"      Age: {token.get('age_days', 0):.1f} days")
                    logger.info(f"      Live: {token.get('is_currently_live', False)}")
                    logger.info(f"      Reply Count: {token.get('reply_count', 0)}")
                    logger.info(f"      Complete: {token.get('complete', False)}")
                    logger.info(f"      Trending Description: {token.get('runner_description', 'N/A')[:100]}...")
                    logger.info("")
            
            return result
            
        except Exception as e:
            error_msg = f"Pump.fun Trending API test failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "tokens_found": 0,
                "tokens": [],
                "error": error_msg
            }
    
    async def test_hybrid_with_trending(self) -> Dict:
        """Test hybrid approach with trending tokens included"""
        logger.info("🧪 Testing Hybrid approach with Trending Tokens...")
        
        try:
            # Test hybrid with pump_only=True (now includes trending tokens)
            pump_only_tokens = await self.token_service.get_hybrid_recent_tokens(
                days=7, 
                include_pump_only=True
            )
            
            result = {
                "success": True,
                "tokens_found": len(pump_only_tokens),
                "tokens": pump_only_tokens,
                "error": None
            }
            
            logger.info(f"✅ Hybrid with Trending: Found {len(pump_only_tokens)} tokens")
            
            # Count tokens by source
            source_counts = {}
            for token in pump_only_tokens:
                source = token.get('source', 'unknown')
                source_counts[source] = source_counts.get(source, 0) + 1
            
            logger.info("📊 Token sources:")
            for source, count in source_counts.items():
                logger.info(f"   {source}: {count} tokens")
            
            if pump_only_tokens:
                logger.info("📋 Sample tokens by source:")
                for source in ['pump_api', 'pump_runners']:
                    source_tokens = [t for t in pump_only_tokens if t.get('source') == source]
                    if source_tokens:
                        sample = source_tokens[0]
                        logger.info(f"   {source}: {sample.get('symbol', 'N/A')} ({sample.get('name', 'N/A')})")
                        logger.info(f"      Market Cap: ${sample.get('usd_market_cap', 0):,.2f}")
                        logger.info(f"      Age: {sample.get('age_days', 0):.1f} days")
            
            return result
            
        except Exception as e:
            error_msg = f"Hybrid with trending test failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "tokens_found": 0,
                "tokens": [],
                "error": error_msg
            }
    
    async def test_trending_vs_regular(self) -> Dict:
        """Compare trending tokens vs regular tokens"""
        logger.info("🧪 Comparing Trending vs Regular Pump.fun Tokens...")
        
        try:
            # Get regular tokens
            regular_tokens = await self.token_service.get_recent_pump_tokens(days=7)
            
            # Get trending tokens
            trending_tokens = await self.token_service.get_trending_pump_tokens(days=7)
            
            # Find overlapping tokens
            regular_mints = {token.get('mint') for token in regular_tokens}
            trending_mints = {token.get('mint') for token in trending_tokens}
            overlapping_mints = regular_mints.intersection(trending_mints)
            
            result = {
                "success": True,
                "regular_tokens": len(regular_tokens),
                "trending_tokens": len(trending_tokens),
                "overlapping_tokens": len(overlapping_mints),
                "regular_only": len(regular_mints - trending_mints),
                "trending_only": len(trending_mints - regular_mints),
                "overlapping_mints": list(overlapping_mints)
            }
            
            logger.info(f"📊 Comparison Results:")
            logger.info(f"   Regular tokens: {result['regular_tokens']}")
            logger.info(f"   Trending tokens: {result['trending_tokens']}")
            logger.info(f"   Overlapping tokens: {result['overlapping_tokens']}")
            logger.info(f"   Regular only: {result['regular_only']}")
            logger.info(f"   Trending only: {result['trending_only']}")
            
            if overlapping_mints:
                logger.info("📋 Overlapping tokens (appear in both lists):")
                for mint in list(overlapping_mints)[:3]:  # Show first 3
                    regular_token = next((t for t in regular_tokens if t.get('mint') == mint), None)
                    trending_token = next((t for t in trending_tokens if t.get('mint') == mint), None)
                    if regular_token and trending_token:
                        logger.info(f"   {regular_token.get('symbol', 'N/A')} ({mint})")
                        logger.info(f"      Regular Market Cap: ${regular_token.get('usd_market_cap', 0):,.2f}")
                        logger.info(f"      Trending Market Cap: ${trending_token.get('usd_market_cap', 0):,.2f}")
                        logger.info(f"      Trending Description: {trending_token.get('runner_description', 'N/A')[:100]}...")
            
            return result
            
        except Exception as e:
            error_msg = f"Trending vs regular comparison failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    async def run_comprehensive_test(self) -> Dict:
        """Run comprehensive test of the trending Pump.fun API"""
        logger.info("🚀 Starting Pump.fun Trending API Test...")
        
        start_time = time.time()
        
        # Test 1: Trending API
        trending_result = await self.test_trending_pump_api()
        
        # Test 2: Hybrid with trending
        hybrid_result = await self.test_hybrid_with_trending()
        
        # Test 3: Comparison
        comparison_result = await self.test_trending_vs_regular()
        
        # Calculate summary
        total_time = time.time() - start_time
        
        summary = {
            "total_time_seconds": total_time,
            "trending_api": trending_result,
            "hybrid_with_trending": hybrid_result,
            "comparison": comparison_result
        }
        
        # Log summary
        logger.info("📊 Pump.fun Trending API Test Summary:")
        logger.info(f"   Trending API: {trending_result['tokens_found']} tokens")
        logger.info(f"   Hybrid with Trending: {hybrid_result['tokens_found']} tokens")
        logger.info(f"   Total Time: {total_time:.2f} seconds")
        
        return summary
    
    def save_results(self, results: Dict, filename: str = "trending_pump_api_test_results.json"):
        """Save test results to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"💾 Results saved to {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")

async def main():
    """Main test function"""
    print("🔍 Pump.fun Trending/Runners API Test")
    print("=" * 50)
    
    # Create tester
    tester = TrendingPumpAPITester()
    
    # Run test
    results = await tester.run_comprehensive_test()
    
    # Save results
    tester.save_results(results)
    
    # Print summary
    print("\n📋 Test Results:")
    print("=" * 50)
    
    trending_api = results["trending_api"]
    hybrid = results["hybrid_with_trending"]
    comparison = results["comparison"]
    
    print(f"Trending Pump.fun API: {'✅ PASS' if trending_api['success'] else '❌ FAIL'}")
    print(f"  Tokens Found: {trending_api['tokens_found']}")
    
    print(f"Hybrid with Trending: {'✅ PASS' if hybrid['success'] else '❌ FAIL'}")
    print(f"  Tokens Found: {hybrid['tokens_found']}")
    
    if comparison['success']:
        print(f"\n📊 Comparison Results:")
        print(f"  Regular tokens: {comparison['regular_tokens']}")
        print(f"  Trending tokens: {comparison['trending_tokens']}")
        print(f"  Overlapping: {comparison['overlapping_tokens']}")
        print(f"  Regular only: {comparison['regular_only']}")
        print(f"  Trending only: {comparison['trending_only']}")
    
    if trending_api['success'] and trending_api['tokens_found'] > 0:
        print(f"\n🎯 Success! Found {trending_api['tokens_found']} trending Pump.fun tokens")
        print("✅ The Pump.fun Trending/Runners API is working correctly!")
        print("✅ Your frontend can now fetch trending token data!")
        
        # Show sample trending token
        sample_token = trending_api['tokens'][0]
        print(f"\n📋 Sample Trending Token:")
        print(f"  Symbol: {sample_token.get('symbol', 'N/A')}")
        print(f"  Name: {sample_token.get('name', 'N/A')}")
        print(f"  Mint: {sample_token.get('mint', 'N/A')}")
        print(f"  Market Cap: ${sample_token.get('usd_market_cap', 0):,.2f}")
        print(f"  Age: {sample_token.get('age_days', 0):.1f} days")
        print(f"  Complete: {sample_token.get('complete', False)}")
        print(f"  Trending Description: {sample_token.get('runner_description', 'N/A')[:100]}...")
    else:
        print(f"\n⚠️ No trending tokens found. Check the error: {trending_api.get('error', 'Unknown error')}")
    
    print(f"\n⏱️ Total Time: {results['total_time_seconds']:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main()) 