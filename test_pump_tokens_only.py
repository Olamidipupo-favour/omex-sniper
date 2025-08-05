#!/usr/bin/env python3
"""
Pump.fun Tokens Only Test - Test only tokens published on Pump.fun
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

class PumpTokensTester:
    """Test class for Pump.fun tokens only"""
    
    def __init__(self):
        self.token_service = TokenFilterService(helius_rpc_url=HELIUS_RPC_URL)
    
    async def test_pump_fun_api_direct(self) -> Dict:
        """Test direct Pump.fun API calls"""
        logger.info("🧪 Testing Pump.fun API directly...")
        
        try:
            # Test 1: Get recent tokens from Pump.fun
            pump_tokens = await self.token_service.get_recent_pump_tokens(days=7)
            
            result = {
                "success": True,
                "tokens_found": len(pump_tokens),
                "tokens": pump_tokens,
                "error": None
            }
            
            logger.info(f"✅ Pump.fun API: Found {len(pump_tokens)} tokens")
            if pump_tokens:
                logger.info("📋 Sample tokens:")
                for i, token in enumerate(pump_tokens[:3]):
                    logger.info(f"   {i+1}. {token.get('symbol', 'N/A')} ({token.get('mint', 'N/A')})")
            
            return result
            
        except Exception as e:
            error_msg = f"Pump.fun API test failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "tokens_found": 0,
                "tokens": [],
                "error": error_msg
            }
    
    async def test_pump_fun_hybrid_only(self) -> Dict:
        """Test hybrid approach with pump_only=True"""
        logger.info("🧪 Testing Hybrid approach (Pump.fun only)...")
        
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
            
            logger.info(f"✅ Pump.fun Only: Found {len(pump_only_tokens)} tokens")
            if pump_only_tokens:
                logger.info("📋 Sample tokens:")
                for i, token in enumerate(pump_only_tokens[:3]):
                    logger.info(f"   {i+1}. {token.get('symbol', 'N/A')} ({token.get('mint', 'N/A')})")
            
            return result
            
        except Exception as e:
            error_msg = f"Pump.fun only test failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "tokens_found": 0,
                "tokens": [],
                "error": error_msg
            }
    
    async def test_individual_pump_tokens(self, tokens: List[Dict]) -> Dict:
        """Test individual Pump.fun token info"""
        logger.info("🧪 Testing individual Pump.fun token info...")
        
        if not tokens:
            return {"success": False, "error": "No tokens to test"}
        
        results = []
        test_count = min(3, len(tokens))  # Test first 3 tokens
        
        for i in range(test_count):
            token = tokens[i]
            mint = token.get('mint', '')
            
            try:
                # Get detailed Pump.fun info for this token
                pump_info = await self.token_service.get_pump_token_info(mint)
                
                result = {
                    "mint": mint,
                    "symbol": token.get('symbol', 'N/A'),
                    "pump_info_found": pump_info is not None,
                    "pump_info": pump_info
                }
                
                logger.info(f"   Token {i+1}: {token.get('symbol', 'N/A')} - Pump.fun info: {'✅' if pump_info else '❌'}")
                results.append(result)
                
            except Exception as e:
                logger.error(f"   Token {i+1}: Error - {str(e)}")
                results.append({
                    "mint": mint,
                    "symbol": token.get('symbol', 'N/A'),
                    "pump_info_found": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "tested_tokens": test_count,
            "results": results
        }
    
    async def test_token_filtering_pump_only(self, tokens: List[Dict]) -> Dict:
        """Test filtering on Pump.fun tokens only"""
        logger.info("🧪 Testing token filtering on Pump.fun tokens...")
        
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
    
    async def run_pump_tokens_test(self) -> Dict:
        """Run comprehensive Pump.fun tokens test"""
        logger.info("🚀 Starting Pump.fun Tokens Only Test...")
        
        start_time = time.time()
        
        # Test 1: Direct Pump.fun API
        direct_result = await self.test_pump_fun_api_direct()
        
        # Test 2: Hybrid with pump_only=True
        hybrid_result = await self.test_pump_fun_hybrid_only()
        
        # Test 3: Individual token info (if we have tokens)
        individual_result = None
        if direct_result["success"] and direct_result["tokens_found"] > 0:
            individual_result = await self.test_individual_pump_tokens(direct_result["tokens"])
        
        # Test 4: Token filtering (if we have tokens)
        filtering_result = None
        if direct_result["success"] and direct_result["tokens_found"] > 0:
            filtering_result = await self.test_token_filtering_pump_only(direct_result["tokens"])
        
        # Calculate summary
        total_time = time.time() - start_time
        
        summary = {
            "total_time_seconds": total_time,
            "direct_api": direct_result,
            "hybrid_pump_only": hybrid_result,
            "individual_tokens": individual_result,
            "token_filtering": filtering_result
        }
        
        # Log summary
        logger.info("📊 Pump.fun Tokens Test Summary:")
        logger.info(f"   Direct API: {direct_result['tokens_found']} tokens")
        logger.info(f"   Hybrid Pump-only: {hybrid_result['tokens_found']} tokens")
        logger.info(f"   Total Time: {total_time:.2f} seconds")
        
        return summary
    
    def save_results(self, results: Dict, filename: str = "pump_tokens_test_results.json"):
        """Save test results to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"💾 Results saved to {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")

async def main():
    """Main test function"""
    print("🔍 Pump.fun Tokens Only Test")
    print("=" * 50)
    
    # Create tester
    tester = PumpTokensTester()
    
    # Run test
    results = await tester.run_pump_tokens_test()
    
    # Save results
    tester.save_results(results)
    
    # Print summary
    print("\n📋 Test Results:")
    print("=" * 50)
    
    direct_api = results["direct_api"]
    hybrid = results["hybrid_pump_only"]
    
    print(f"Direct Pump.fun API: {'✅ PASS' if direct_api['success'] else '❌ FAIL'}")
    print(f"  Tokens Found: {direct_api['tokens_found']}")
    
    print(f"Hybrid Pump-only: {'✅ PASS' if hybrid['success'] else '❌ FAIL'}")
    print(f"  Tokens Found: {hybrid['tokens_found']}")
    
    if direct_api['success'] and direct_api['tokens_found'] > 0:
        print(f"\n🎯 Success! Found {direct_api['tokens_found']} Pump.fun tokens")
        print("This means your frontend should be able to fetch tokens.")
    else:
        print(f"\n⚠️ No Pump.fun tokens found. Check the error: {direct_api.get('error', 'Unknown error')}")
    
    print(f"\n⏱️ Total Time: {results['total_time_seconds']:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main()) 