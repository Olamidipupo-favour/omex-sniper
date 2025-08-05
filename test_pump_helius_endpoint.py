#!/usr/bin/env python3
"""
Pump.fun Helius RPC Endpoint Test - Explore specialized Pump.fun RPC capabilities
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List
from solana.rpc.async_api import AsyncClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PumpHeliusEndpointTester:
    """Test the Pump.fun Helius RPC endpoint"""
    
    def __init__(self):
        self.pump_helius_url = "https://pump-fe.helius-rpc.com/?api-key=1b8db865-a5a1-4535-9aec-01061440523b"
        self.client = AsyncClient(self.pump_helius_url)
    
    async def test_basic_rpc_methods(self) -> Dict:
        """Test basic RPC methods to see if they work"""
        logger.info("🧪 Testing Basic RPC Methods...")
        
        results = {}
        
        try:
            # Test 1: Get slot
            logger.info("   Testing getSlot...")
            slot_response = await self.client.get_slot()
            results["get_slot"] = {
                "success": slot_response.value is not None,
                "slot": slot_response.value if slot_response.value else None
            }
            logger.info(f"   ✅ Slot: {slot_response.value}")
            
        except Exception as e:
            logger.error(f"   ❌ getSlot failed: {e}")
            results["get_slot"] = {"success": False, "error": str(e)}
        
        try:
            # Test 2: Get recent performance samples
            logger.info("   Testing getRecentPerformanceSamples...")
            perf_response = await self.client.get_recent_performance_samples(limit=5)
            results["get_recent_performance"] = {
                "success": perf_response.value is not None,
                "samples": len(perf_response.value) if perf_response.value else 0
            }
            logger.info(f"   ✅ Performance samples: {len(perf_response.value) if perf_response.value else 0}")
            
        except Exception as e:
            logger.error(f"   ❌ getRecentPerformanceSamples failed: {e}")
            results["get_recent_performance"] = {"success": False, "error": str(e)}
        
        try:
            # Test 3: Get version
            logger.info("   Testing getVersion...")
            version_response = await self.client.get_version()
            results["get_version"] = {
                "success": version_response.value is not None,
                "version": version_response.value if version_response.value else None
            }
            logger.info(f"   ✅ Version: {version_response.value}")
            
        except Exception as e:
            logger.error(f"   ❌ getVersion failed: {e}")
            results["get_version"] = {"success": False, "error": str(e)}
        
        return results
    
    async def test_pump_specific_methods(self) -> Dict:
        """Test Pump.fun specific methods that might be available"""
        logger.info("🧪 Testing Pump.fun Specific Methods...")
        
        results = {}
        
        # Test custom RPC methods that might be available on Pump.fun endpoint
        custom_methods = [
            "getPumpTokens",
            "getPumpTokenList", 
            "getPumpRecentTokens",
            "getPumpTokenInfo",
            "getPumpTrendingTokens",
            "getPumpTokenHolders",
            "getPumpTokenTransactions"
        ]
        
        for method in custom_methods:
            try:
                logger.info(f"   Testing {method}...")
                
                # Create custom RPC request
                request_data = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": []
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.pump_helius_url,
                        json=request_data,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    ) as response:
                        response_data = await response.json()
                        
                        if "error" in response_data:
                            logger.info(f"   ⚠️ {method}: Method not available")
                            results[method] = {"success": False, "error": response_data.get("error", {}).get("message", "Method not found")}
                        else:
                            logger.info(f"   ✅ {method}: Success")
                            results[method] = {"success": True, "data": response_data.get("result")}
                
            except Exception as e:
                logger.error(f"   ❌ {method} failed: {e}")
                results[method] = {"success": False, "error": str(e)}
        
        return results
    
    async def test_token_program_queries(self) -> Dict:
        """Test token program related queries"""
        logger.info("🧪 Testing Token Program Queries...")
        
        results = {}
        
        try:
            # Test getting recent token program transactions
            logger.info("   Testing getSignaturesForAddress (Token Program)...")
            token_program_id = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            
            from solders.pubkey import Pubkey
            signatures_response = await self.client.get_signatures_for_address(
                Pubkey.from_string(token_program_id),
                limit=5
            )
            
            results["token_program_signatures"] = {
                "success": signatures_response.value is not None,
                "count": len(signatures_response.value) if signatures_response.value else 0,
                "signatures": [sig.signature for sig in signatures_response.value[:3]] if signatures_response.value else []
            }
            
            logger.info(f"   ✅ Token program signatures: {len(signatures_response.value) if signatures_response.value else 0}")
            
        except Exception as e:
            logger.error(f"   ❌ Token program signatures failed: {e}")
            results["token_program_signatures"] = {"success": False, "error": str(e)}
        
        try:
            # Test getting account info for a known token
            logger.info("   Testing getAccountInfo (WSOL)...")
            wsol_mint = "So11111111111111111111111111111111111111112"
            
            from solders.pubkey import Pubkey
            account_response = await self.client.get_account_info(
                Pubkey.from_string(wsol_mint)
            )
            
            results["wsol_account_info"] = {
                "success": account_response.value is not None,
                "has_data": account_response.value.data is not None if account_response.value else False
            }
            
            logger.info(f"   ✅ WSOL account info: {'Found' if account_response.value else 'Not found'}")
            
        except Exception as e:
            logger.error(f"   ❌ WSOL account info failed: {e}")
            results["wsol_account_info"] = {"success": False, "error": str(e)}
        
        return results
    
    async def test_enhanced_methods(self) -> Dict:
        """Test enhanced methods that might be available on Pump.fun endpoint"""
        logger.info("🧪 Testing Enhanced Methods...")
        
        results = {}
        
        # Test enhanced methods that might be available
        enhanced_methods = [
            "getEnhancedTokenAccounts",
            "getTokenAccountsByOwner",
            "getMultipleAccounts",
            "getProgramAccounts",
            "getTokenSupply",
            "getTokenLargestAccounts"
        ]
        
        for method in enhanced_methods:
            try:
                logger.info(f"   Testing {method}...")
                
                # Create custom RPC request with appropriate parameters
                if method == "getTokenSupply":
                    params = ["So11111111111111111111111111111111111111112"]
                elif method == "getTokenLargestAccounts":
                    params = ["So11111111111111111111111111111111111111112"]
                elif method == "getTokenAccountsByOwner":
                    # Use a sample owner address
                    params = ["11111111111111111111111111111112", {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}]
                else:
                    params = []
                
                request_data = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.pump_helius_url,
                        json=request_data,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    ) as response:
                        response_data = await response.json()
                        
                        if "error" in response_data:
                            logger.info(f"   ⚠️ {method}: Method not available")
                            results[method] = {"success": False, "error": response_data.get("error", {}).get("message", "Method not found")}
                        else:
                            logger.info(f"   ✅ {method}: Success")
                            results[method] = {"success": True, "data": response_data.get("result")}
                
            except Exception as e:
                logger.error(f"   ❌ {method} failed: {e}")
                results[method] = {"success": False, "error": str(e)}
        
        return results
    
    async def run_comprehensive_test(self) -> Dict:
        """Run comprehensive test of the Pump.fun Helius endpoint"""
        logger.info("🚀 Starting Pump.fun Helius Endpoint Test...")
        
        start_time = asyncio.get_event_loop().time()
        
        # Run all tests
        basic_results = await self.test_basic_rpc_methods()
        pump_specific_results = await self.test_pump_specific_methods()
        token_program_results = await self.test_token_program_queries()
        enhanced_results = await self.test_enhanced_methods()
        
        total_time = asyncio.get_event_loop().time() - start_time
        
        # Compile results
        all_results = {
            "basic_rpc": basic_results,
            "pump_specific": pump_specific_results,
            "token_program": token_program_results,
            "enhanced": enhanced_results,
            "total_time": total_time
        }
        
        # Calculate success rates
        total_tests = len(basic_results) + len(pump_specific_results) + len(token_program_results) + len(enhanced_results)
        successful_tests = sum(1 for r in basic_results.values() if r.get("success", False))
        successful_tests += sum(1 for r in pump_specific_results.values() if r.get("success", False))
        successful_tests += sum(1 for r in token_program_results.values() if r.get("success", False))
        successful_tests += sum(1 for r in enhanced_results.values() if r.get("success", False))
        
        all_results["summary"] = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0
        }
        
        logger.info(f"📊 Test Summary:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Successful: {successful_tests}")
        logger.info(f"   Success Rate: {all_results['summary']['success_rate']:.1f}%")
        logger.info(f"   Total Time: {total_time:.2f} seconds")
        
        return all_results
    
    def save_results(self, results: Dict, filename: str = "pump_helius_test_results.json"):
        """Save test results to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"💾 Results saved to {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")

async def main():
    """Main test function"""
    print("🔍 Pump.fun Helius RPC Endpoint Test")
    print("=" * 50)
    
    # Create tester
    tester = PumpHeliusEndpointTester()
    
    # Run comprehensive test
    results = await tester.run_comprehensive_test()
    
    # Save results
    tester.save_results(results)
    
    # Print summary
    print("\n📋 Test Results:")
    print("=" * 50)
    
    summary = results["summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Successful: {summary['successful_tests']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    
    # Show what's working
    print(f"\n✅ Working Methods:")
    
    basic_rpc = results["basic_rpc"]
    for method, result in basic_rpc.items():
        if result.get("success", False):
            print(f"  Basic RPC: {method}")
    
    pump_specific = results["pump_specific"]
    for method, result in pump_specific.items():
        if result.get("success", False):
            print(f"  Pump Specific: {method}")
    
    token_program = results["token_program"]
    for method, result in token_program.items():
        if result.get("success", False):
            print(f"  Token Program: {method}")
    
    enhanced = results["enhanced"]
    for method, result in enhanced.items():
        if result.get("success", False):
            print(f"  Enhanced: {method}")
    
    print(f"\n⏱️ Total Time: {results['total_time']:.2f} seconds")
    print(f"💾 Results saved to: pump_helius_test_results.json")

if __name__ == "__main__":
    asyncio.run(main()) 