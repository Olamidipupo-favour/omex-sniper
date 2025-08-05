#!/usr/bin/env python3
"""
Token Fetching Test Script
Tests all token fetching methods to verify functionality
"""

import asyncio
import json
import logging
import time
from typing import Dict, List
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the token filter service
from token_filter_service import TokenFilterService
from config import HELIUS_RPC_URL

class TokenFetchingTester:
    """Test class for token fetching functionality"""
    
    def __init__(self):
        self.token_service = TokenFilterService(helius_rpc_url=HELIUS_RPC_URL)
        self.test_results = {}
    
    async def test_pump_fun_api(self) -> Dict:
        """Test Pump.fun API token fetching"""
        logger.info("🧪 Testing Pump.fun API...")
        
        try:
            # Test 1: Get recent Pump.fun tokens
            pump_tokens = await self.token_service.get_recent_pump_tokens(days=7)
            
            result = {
                "success": True,
                "tokens_found": len(pump_tokens),
                "sample_tokens": pump_tokens[:3] if pump_tokens else [],
                "error": None
            }
            
            logger.info(f"✅ Pump.fun API: Found {len(pump_tokens)} tokens")
            if pump_tokens:
                logger.info(f"📋 Sample tokens: {json.dumps(pump_tokens[:2], indent=2)}")
            
            return result
            
        except Exception as e:
            error_msg = f"Pump.fun API test failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "tokens_found": 0,
                "sample_tokens": [],
                "error": error_msg
            }
    
    async def test_helius_rpc(self) -> Dict:
        """Test Helius RPC token fetching"""
        logger.info("🧪 Testing Helius RPC...")
        
        try:
            # Test 1: Get recent tokens from Helius
            helius_tokens = await self.token_service.get_recent_tokens_from_helius(days=7)
            
            result = {
                "success": True,
                "tokens_found": len(helius_tokens),
                "sample_tokens": helius_tokens[:3] if helius_tokens else [],
                "error": None
            }
            
            logger.info(f"✅ Helius RPC: Found {len(helius_tokens)} tokens")
            if helius_tokens:
                logger.info(f"📋 Sample tokens: {json.dumps(helius_tokens[:2], indent=2)}")
            
            return result
            
        except Exception as e:
            error_msg = f"Helius RPC test failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "tokens_found": 0,
                "sample_tokens": [],
                "error": error_msg
            }
    
    async def test_simple_fallback(self) -> Dict:
        """Test simple fallback token fetching"""
        logger.info("🧪 Testing Simple Fallback...")
        
        try:
            # Test 1: Get simple fallback tokens
            simple_tokens = await self.token_service.get_recent_tokens_simple(days=7)
            
            result = {
                "success": True,
                "tokens_found": len(simple_tokens),
                "sample_tokens": simple_tokens[:3] if simple_tokens else [],
                "error": None
            }
            
            logger.info(f"✅ Simple Fallback: Found {len(simple_tokens)} tokens")
            if simple_tokens:
                logger.info(f"📋 Sample tokens: {json.dumps(simple_tokens[:2], indent=2)}")
            
            return result
            
        except Exception as e:
            error_msg = f"Simple fallback test failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "tokens_found": 0,
                "sample_tokens": [],
                "error": error_msg
            }
    
    async def test_hybrid_approach(self) -> Dict:
        """Test hybrid token fetching approach"""
        logger.info("🧪 Testing Hybrid Approach...")
        
        try:
            # Test 1: Get hybrid tokens (Pump.fun + Helius)
            hybrid_tokens = await self.token_service.get_hybrid_recent_tokens(days=7, include_pump_only=False)
            
            result = {
                "success": True,
                "tokens_found": len(hybrid_tokens),
                "sample_tokens": hybrid_tokens[:3] if hybrid_tokens else [],
                "error": None
            }
            
            logger.info(f"✅ Hybrid Approach: Found {len(hybrid_tokens)} tokens")
            if hybrid_tokens:
                logger.info(f"📋 Sample tokens: {json.dumps(hybrid_tokens[:2], indent=2)}")
            
            return result
            
        except Exception as e:
            error_msg = f"Hybrid approach test failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "tokens_found": 0,
                "sample_tokens": [],
                "error": error_msg
            }
    
    async def test_token_filtering(self, tokens: List[Dict]) -> Dict:
        """Test token filtering functionality"""
        logger.info("🧪 Testing Token Filtering...")
        
        try:
            if not tokens:
                return {
                    "success": False,
                    "filtered_tokens": 0,
                    "error": "No tokens to filter"
                }
            
            # Test different filter types
            filter_types = ["new_only", "last_1_day", "last_3_days", "last_7_days"]
            filter_results = {}
            
            for filter_type in filter_types:
                filtered = self.token_service.filter_tokens_by_age(
                    tokens, filter_type, custom_days=7, include_pump_tokens=True
                )
                filter_results[filter_type] = len(filtered)
                logger.info(f"📊 Filter '{filter_type}': {len(filtered)} tokens")
            
            result = {
                "success": True,
                "original_count": len(tokens),
                "filter_results": filter_results,
                "error": None
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Token filtering test failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "filtered_tokens": 0,
                "error": error_msg
            }
    
    async def test_individual_token_info(self, mint: str) -> Dict:
        """Test getting individual token information"""
        logger.info(f"🧪 Testing Individual Token Info for {mint}...")
        
        try:
            # Test 1: Get Pump.fun token info
            pump_info = await self.token_service.get_pump_token_info(mint)
            
            # Test 2: Get token age info
            age_info = await self.token_service.get_token_age_info(
                mint=mint,
                symbol="TEST",
                name="Test Token",
                created_timestamp=int(time.time()) - (24 * 3600),  # 1 day ago
                include_pump_check=True
            )
            
            result = {
                "success": True,
                "pump_info": pump_info is not None,
                "age_info": {
                    "mint": age_info.mint,
                    "symbol": age_info.symbol,
                    "name": age_info.name,
                    "age_days": age_info.age_days,
                    "is_on_pump": age_info.is_on_pump
                },
                "error": None
            }
            
            logger.info(f"✅ Individual Token Info: Success for {mint}")
            logger.info(f"📋 Age Info: {json.dumps(result['age_info'], indent=2)}")
            
            return result
            
        except Exception as e:
            error_msg = f"Individual token info test failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "pump_info": False,
                "age_info": None,
                "error": error_msg
            }
    
    async def run_all_tests(self) -> Dict:
        """Run all token fetching tests"""
        logger.info("🚀 Starting Token Fetching Tests...")
        logger.info(f"🔧 Using RPC URL: {self.token_service.helius_rpc_url}")
        
        start_time = time.time()
        
        # Run all tests
        tests = {
            "pump_fun_api": await self.test_pump_fun_api(),
            "helius_rpc": await self.test_helius_rpc(),
            "simple_fallback": await self.test_simple_fallback(),
            "hybrid_approach": await self.test_hybrid_approach()
        }
        
        # Test filtering with tokens from hybrid approach
        if tests["hybrid_approach"]["success"] and tests["hybrid_approach"]["tokens_found"] > 0:
            # Get the actual tokens for filtering test
            hybrid_tokens = await self.token_service.get_hybrid_recent_tokens(days=7, include_pump_only=False)
            tests["token_filtering"] = await self.test_token_filtering(hybrid_tokens)
        else:
            tests["token_filtering"] = {"success": False, "error": "No tokens available for filtering test"}
        
        # Test individual token info with a sample token
        if tests["hybrid_approach"]["success"] and tests["hybrid_approach"]["tokens_found"] > 0:
            sample_token = tests["hybrid_approach"]["sample_tokens"][0]
            mint = sample_token.get("mint", "So11111111111111111111111111111111111111112")  # WSOL as fallback
            tests["individual_token_info"] = await self.test_individual_token_info(mint)
        else:
            tests["individual_token_info"] = {"success": False, "error": "No tokens available for individual test"}
        
        # Calculate summary
        total_time = time.time() - start_time
        successful_tests = sum(1 for test in tests.values() if test.get("success", False))
        total_tests = len(tests)
        
        summary = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": total_tests - successful_tests,
            "success_rate": (successful_tests / total_tests) * 100 if total_tests > 0 else 0,
            "total_time_seconds": total_time,
            "tests": tests
        }
        
        # Log summary
        logger.info("📊 Test Summary:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Successful: {successful_tests}")
        logger.info(f"   Failed: {total_tests - successful_tests}")
        logger.info(f"   Success Rate: {summary['success_rate']:.1f}%")
        logger.info(f"   Total Time: {total_time:.2f} seconds")
        
        return summary
    
    def save_test_results(self, results: Dict, filename: str = "token_test_results.json"):
        """Save test results to a JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"💾 Test results saved to {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to save test results: {e}")

async def main():
    """Main test function"""
    print("🔍 Token Fetching Test Suite")
    print("=" * 50)
    
    # Create tester instance
    tester = TokenFetchingTester()
    
    # Run all tests
    results = await tester.run_all_tests()
    
    # Save results
    tester.save_test_results(results)
    
    # Print detailed results
    print("\n📋 Detailed Results:")
    print("=" * 50)
    
    for test_name, test_result in results["tests"].items():
        status = "✅ PASS" if test_result.get("success", False) else "❌ FAIL"
        print(f"{test_name.upper()}: {status}")
        
        if test_result.get("success", False):
            if "tokens_found" in test_result:
                print(f"  Tokens Found: {test_result['tokens_found']}")
            if "sample_tokens" in test_result and test_result["sample_tokens"]:
                print(f"  Sample Token: {test_result['sample_tokens'][0].get('mint', 'N/A')}")
        else:
            print(f"  Error: {test_result.get('error', 'Unknown error')}")
        print()
    
    print(f"🎯 Overall Success Rate: {results['success_rate']:.1f}%")
    print(f"⏱️ Total Time: {results['total_time_seconds']:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main()) 