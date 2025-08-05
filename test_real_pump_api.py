#!/usr/bin/env python3
"""
Test Real Pump.fun API Endpoint
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

class RealPumpAPITester:
    """Test the real Pump.fun API endpoint"""
    
    def __init__(self):
        self.token_service = TokenFilterService(helius_rpc_url=HELIUS_RPC_URL)
    
    async def test_real_pump_api(self) -> Dict:
        """Test the real Pump.fun API endpoint"""
        logger.info("🧪 Testing Real Pump.fun API...")
        
        try:
            # Test the real endpoint
            tokens = await self.token_service.get_recent_pump_tokens(days=7)
            
            result = {
                "success": True,
                "tokens_found": len(tokens),
                "tokens": tokens,
                "error": None
            }
            
            logger.info(f"✅ Real Pump.fun API: Found {len(tokens)} tokens")
            
            if tokens:
                logger.info("📋 Sample tokens:")
                for i, token in enumerate(tokens[:5]):  # Show first 5 tokens
                    logger.info(f"   {i+1}. {token.get('symbol', 'N/A')} ({token.get('name', 'N/A')})")
                    logger.info(f"      Mint: {token.get('mint', 'N/A')}")
                    logger.info(f"      Market Cap: ${token.get('usd_market_cap', 0):,.2f}")
                    logger.info(f"      Age: {token.get('age_days', 0):.1f} days")
                    logger.info(f"      Live: {token.get('is_currently_live', False)}")
                    logger.info(f"      Participants: {token.get('holders', 0)}")
                    logger.info("")
            
            return result
            
        except Exception as e:
            error_msg = f"Real Pump.fun API test failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "tokens_found": 0,
                "tokens": [],
                "error": error_msg
            }
    
    async def test_hybrid_with_real_api(self) -> Dict:
        """Test hybrid approach with real Pump.fun API"""
        logger.info("🧪 Testing Hybrid approach with Real Pump.fun API...")
        
        try:
            # Test hybrid with pump_only=True
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
            
            logger.info(f"✅ Hybrid with Real API: Found {len(pump_only_tokens)} tokens")
            
            if pump_only_tokens:
                logger.info("📋 Sample tokens:")
                for i, token in enumerate(pump_only_tokens[:3]):
                    logger.info(f"   {i+1}. {token.get('symbol', 'N/A')} ({token.get('name', 'N/A')})")
                    logger.info(f"      Source: {token.get('source', 'N/A')}")
                    logger.info(f"      Market Cap: ${token.get('usd_market_cap', 0):,.2f}")
                    logger.info(f"      Age: {token.get('age_days', 0):.1f} days")
            
            return result
            
        except Exception as e:
            error_msg = f"Hybrid with real API test failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "tokens_found": 0,
                "tokens": [],
                "error": error_msg
            }
    
    async def test_token_filtering(self, tokens: List[Dict]) -> Dict:
        """Test filtering on real Pump.fun tokens"""
        logger.info("🧪 Testing Token Filtering on Real Pump.fun Tokens...")
        
        if not tokens:
            return {"success": False, "error": "No tokens to filter"}
        
        try:
            # Test different filter types
            filter_types = ["new_only", "last_1_day", "last_3_days", "last_7_days"]
            filter_results = {}
            
            for filter_type in filter_types:
                filtered = self.token_service.filter_tokens_by_age(
                    tokens, filter_type, custom_days=7, include_pump_tokens=True
                )
                filter_results[filter_type] = {
                    "count": len(filtered),
                    "sample": filtered[:2] if filtered else []
                }
                logger.info(f"   Filter '{filter_type}': {len(filtered)} tokens")
            
            return {
                "success": True,
                "original_count": len(tokens),
                "filter_results": filter_results
            }
            
        except Exception as e:
            error_msg = f"Token filtering test failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    async def run_comprehensive_test(self) -> Dict:
        """Run comprehensive test of the real Pump.fun API"""
        logger.info("🚀 Starting Real Pump.fun API Test...")
        
        start_time = time.time()
        
        # Test 1: Real Pump.fun API
        real_api_result = await self.test_real_pump_api()
        
        # Test 2: Hybrid with real API
        hybrid_result = await self.test_hybrid_with_real_api()
        
        # Test 3: Token filtering (if we have tokens)
        filtering_result = None
        if real_api_result["success"] and real_api_result["tokens_found"] > 0:
            filtering_result = await self.test_token_filtering(real_api_result["tokens"])
        
        # Calculate summary
        total_time = time.time() - start_time
        
        summary = {
            "total_time_seconds": total_time,
            "real_api": real_api_result,
            "hybrid": hybrid_result,
            "filtering": filtering_result
        }
        
        # Log summary
        logger.info("📊 Real Pump.fun API Test Summary:")
        logger.info(f"   Real API: {real_api_result['tokens_found']} tokens")
        logger.info(f"   Hybrid: {hybrid_result['tokens_found']} tokens")
        logger.info(f"   Total Time: {total_time:.2f} seconds")
        
        return summary
    
    def save_results(self, results: Dict, filename: str = "real_pump_api_test_results.json"):
        """Save test results to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"💾 Results saved to {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")

async def main():
    """Main test function"""
    print("🔍 Real Pump.fun API Test")
    print("=" * 50)
    
    # Create tester
    tester = RealPumpAPITester()
    
    # Run test
    results = await tester.run_comprehensive_test()
    
    # Save results
    tester.save_results(results)
    
    # Print summary
    print("\n📋 Test Results:")
    print("=" * 50)
    
    real_api = results["real_api"]
    hybrid = results["hybrid"]
    
    print(f"Real Pump.fun API: {'✅ PASS' if real_api['success'] else '❌ FAIL'}")
    print(f"  Tokens Found: {real_api['tokens_found']}")
    
    print(f"Hybrid with Real API: {'✅ PASS' if hybrid['success'] else '❌ FAIL'}")
    print(f"  Tokens Found: {hybrid['tokens_found']}")
    
    if real_api['success'] and real_api['tokens_found'] > 0:
        print(f"\n🎯 Success! Found {real_api['tokens_found']} real Pump.fun tokens")
        print("✅ The real Pump.fun API is working correctly!")
        print("✅ Your frontend can now fetch live Pump.fun token data!")
        
        # Show sample token details
        sample_token = real_api['tokens'][0]
        print(f"\n📋 Sample Real Token:")
        print(f"  Symbol: {sample_token.get('symbol', 'N/A')}")
        print(f"  Name: {sample_token.get('name', 'N/A')}")
        print(f"  Mint: {sample_token.get('mint', 'N/A')}")
        print(f"  Market Cap: ${sample_token.get('usd_market_cap', 0):,.2f}")
        print(f"  Age: {sample_token.get('age_days', 0):.1f} days")
        print(f"  Live: {sample_token.get('is_currently_live', False)}")
        print(f"  Participants: {sample_token.get('holders', 0)}")
        print(f"  Description: {sample_token.get('description', 'N/A')[:100]}...")
    else:
        print(f"\n⚠️ No real Pump.fun tokens found. Check the error: {real_api.get('error', 'Unknown error')}")
    
    print(f"\n⏱️ Total Time: {results['total_time_seconds']:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main()) 