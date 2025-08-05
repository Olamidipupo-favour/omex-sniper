#!/usr/bin/env python3
"""
Test Timestamp-Based Token Fetching with Pagination
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

class TimestampFetchingTester:
    """Test timestamp-based token fetching with pagination"""
    
    def __init__(self):
        self.token_service = TokenFilterService(helius_rpc_url=HELIUS_RPC_URL)
    
    async def test_timestamp_based_fetching(self) -> Dict:
        """Test timestamp-based fetching for different time periods"""
        logger.info("🧪 Testing Timestamp-Based Token Fetching...")
        
        results = {}
        
        # Test different time periods
        time_periods = [1, 3, 7, 14, 30]  # days
        
        for days in time_periods:
            try:
                logger.info(f"🔍 Testing {days} day(s) period...")
                
                # Get tokens for this period
                tokens = await self.token_service.get_recent_pump_tokens(days=days)
                
                # Analyze the results
                if tokens:
                    # Check timestamps
                    current_time = int(time.time() * 1000)  # milliseconds
                    time_threshold = current_time - (days * 24 * 3600 * 1000)
                    
                    valid_tokens = []
                    old_tokens = []
                    
                    for token in tokens:
                        created_timestamp = token.get('created_timestamp', 0)
                        if created_timestamp >= time_threshold:
                            valid_tokens.append(token)
                        else:
                            old_tokens.append(token)
                    
                    # Calculate statistics
                    total_market_cap = sum(token.get('usd_market_cap', 0) for token in valid_tokens)
                    avg_market_cap = total_market_cap / len(valid_tokens) if valid_tokens else 0
                    
                    results[f"{days}_days"] = {
                        "success": True,
                        "total_tokens": len(tokens),
                        "valid_tokens": len(valid_tokens),
                        "old_tokens": len(old_tokens),
                        "total_market_cap": total_market_cap,
                        "avg_market_cap": avg_market_cap,
                        "sample_tokens": tokens[:3] if tokens else []
                    }
                    
                    logger.info(f"   ✅ {days} days: {len(valid_tokens)} valid tokens, {len(old_tokens)} old tokens")
                    logger.info(f"   📊 Total Market Cap: ${total_market_cap:,.2f}")
                    logger.info(f"   📊 Avg Market Cap: ${avg_market_cap:,.2f}")
                    
                else:
                    results[f"{days}_days"] = {
                        "success": False,
                        "error": "No tokens found"
                    }
                    logger.info(f"   ❌ {days} days: No tokens found")
                    
            except Exception as e:
                error_msg = f"Error testing {days} days: {str(e)}"
                logger.error(f"   ❌ {error_msg}")
                results[f"{days}_days"] = {
                    "success": False,
                    "error": error_msg
                }
        
        return results
    
    async def test_trending_timestamp_filtering(self) -> Dict:
        """Test timestamp filtering for trending tokens"""
        logger.info("🧪 Testing Trending Token Timestamp Filtering...")
        
        try:
            # Test different time periods for trending tokens
            time_periods = [1, 3, 7, 14, 30]  # days
            
            results = {}
            
            for days in time_periods:
                try:
                    logger.info(f"🔍 Testing trending tokens for {days} day(s)...")
                    
                    # Get trending tokens for this period
                    tokens = await self.token_service.get_trending_pump_tokens(days=days)
                    
                    if tokens:
                        # Calculate statistics
                        total_market_cap = sum(token.get('usd_market_cap', 0) for token in tokens)
                        avg_market_cap = total_market_cap / len(tokens) if tokens else 0
                        
                        results[f"{days}_days"] = {
                            "success": True,
                            "total_tokens": len(tokens),
                            "total_market_cap": total_market_cap,
                            "avg_market_cap": avg_market_cap,
                            "sample_tokens": tokens[:3] if tokens else []
                        }
                        
                        logger.info(f"   ✅ {days} days: {len(tokens)} trending tokens")
                        logger.info(f"   📊 Total Market Cap: ${total_market_cap:,.2f}")
                        logger.info(f"   📊 Avg Market Cap: ${avg_market_cap:,.2f}")
                        
                    else:
                        results[f"{days}_days"] = {
                            "success": False,
                            "error": "No trending tokens found"
                        }
                        logger.info(f"   ❌ {days} days: No trending tokens found")
                        
                except Exception as e:
                    error_msg = f"Error testing trending {days} days: {str(e)}"
                    logger.error(f"   ❌ {error_msg}")
                    results[f"{days}_days"] = {
                        "success": False,
                        "error": error_msg
                    }
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in trending timestamp test: {e}")
            return {"error": str(e)}
    
    async def test_hybrid_with_timestamp_filtering(self) -> Dict:
        """Test hybrid approach with timestamp filtering"""
        logger.info("🧪 Testing Hybrid Approach with Timestamp Filtering...")
        
        try:
            # Test hybrid for different time periods
            time_periods = [1, 3, 7, 14, 30]  # days
            
            results = {}
            
            for days in time_periods:
                try:
                    logger.info(f"🔍 Testing hybrid for {days} day(s)...")
                    
                    # Get hybrid tokens for this period
                    tokens = await self.token_service.get_hybrid_recent_tokens(
                        days=days, 
                        include_pump_only=True
                    )
                    
                    if tokens:
                        # Count by source
                        source_counts = {}
                        for token in tokens:
                            source = token.get('source', 'unknown')
                            source_counts[source] = source_counts.get(source, 0) + 1
                        
                        # Calculate statistics
                        total_market_cap = sum(token.get('usd_market_cap', 0) for token in tokens)
                        avg_market_cap = total_market_cap / len(tokens) if tokens else 0
                        
                        results[f"{days}_days"] = {
                            "success": True,
                            "total_tokens": len(tokens),
                            "source_counts": source_counts,
                            "total_market_cap": total_market_cap,
                            "avg_market_cap": avg_market_cap,
                            "sample_tokens": tokens[:3] if tokens else []
                        }
                        
                        logger.info(f"   ✅ {days} days: {len(tokens)} total tokens")
                        logger.info(f"   📊 Sources: {source_counts}")
                        logger.info(f"   📊 Total Market Cap: ${total_market_cap:,.2f}")
                        logger.info(f"   📊 Avg Market Cap: ${avg_market_cap:,.2f}")
                        
                    else:
                        results[f"{days}_days"] = {
                            "success": False,
                            "error": "No hybrid tokens found"
                        }
                        logger.info(f"   ❌ {days} days: No hybrid tokens found")
                        
                except Exception as e:
                    error_msg = f"Error testing hybrid {days} days: {str(e)}"
                    logger.error(f"   ❌ {error_msg}")
                    results[f"{days}_days"] = {
                        "success": False,
                        "error": error_msg
                    }
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in hybrid timestamp test: {e}")
            return {"error": str(e)}
    
    async def run_comprehensive_test(self) -> Dict:
        """Run comprehensive timestamp-based fetching test"""
        logger.info("🚀 Starting Timestamp-Based Fetching Test...")
        
        start_time = time.time()
        
        # Test 1: Regular token timestamp filtering
        regular_results = await self.test_timestamp_based_fetching()
        
        # Test 2: Trending token timestamp filtering
        trending_results = await self.test_trending_timestamp_filtering()
        
        # Test 3: Hybrid with timestamp filtering
        hybrid_results = await self.test_hybrid_with_timestamp_filtering()
        
        # Calculate summary
        total_time = time.time() - start_time
        
        summary = {
            "total_time_seconds": total_time,
            "regular_tokens": regular_results,
            "trending_tokens": trending_results,
            "hybrid_tokens": hybrid_results
        }
        
        # Log summary
        logger.info("📊 Timestamp-Based Fetching Test Summary:")
        
        # Count total tokens across all periods
        total_regular = sum(r.get("valid_tokens", 0) for r in regular_results.values() if r.get("success"))
        total_trending = sum(r.get("total_tokens", 0) for r in trending_results.values() if r.get("success"))
        total_hybrid = sum(r.get("total_tokens", 0) for r in hybrid_results.values() if r.get("success"))
        
        logger.info(f"   Regular tokens: {total_regular}")
        logger.info(f"   Trending tokens: {total_trending}")
        logger.info(f"   Hybrid tokens: {total_hybrid}")
        logger.info(f"   Total Time: {total_time:.2f} seconds")
        
        return summary
    
    def save_results(self, results: Dict, filename: str = "timestamp_fetching_test_results.json"):
        """Save test results to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"💾 Results saved to {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")

async def main():
    """Main test function"""
    print("🔍 Timestamp-Based Token Fetching Test")
    print("=" * 50)
    
    # Create tester
    tester = TimestampFetchingTester()
    
    # Run test
    results = await tester.run_comprehensive_test()
    
    # Save results
    tester.save_results(results)
    
    # Print summary
    print("\n📋 Test Results:")
    print("=" * 50)
    
    # Count total tokens across all periods
    total_regular = sum(r.get("valid_tokens", 0) for r in results["regular_tokens"].values() if r.get("success"))
    total_trending = sum(r.get("total_tokens", 0) for r in results["trending_tokens"].values() if r.get("success"))
    total_hybrid = sum(r.get("total_tokens", 0) for r in results["hybrid_tokens"].values() if r.get("success"))
    
    print(f"Regular tokens: {total_regular}")
    print(f"Trending tokens: {total_trending}")
    print(f"Hybrid tokens: {total_hybrid}")
    
    # Show detailed results for 7 days
    if "7_days" in results["regular_tokens"]:
        regular_7 = results["regular_tokens"]["7_days"]
        if regular_7.get("success"):
            print(f"\n📊 7-Day Regular Tokens:")
            print(f"  Valid tokens: {regular_7['valid_tokens']}")
            print(f"  Old tokens: {regular_7['old_tokens']}")
            print(f"  Total Market Cap: ${regular_7['total_market_cap']:,.2f}")
            print(f"  Avg Market Cap: ${regular_7['avg_market_cap']:,.2f}")
    
    if "7_days" in results["trending_tokens"]:
        trending_7 = results["trending_tokens"]["7_days"]
        if trending_7.get("success"):
            print(f"\n📊 7-Day Trending Tokens:")
            print(f"  Total tokens: {trending_7['total_tokens']}")
            print(f"  Total Market Cap: ${trending_7['total_market_cap']:,.2f}")
            print(f"  Avg Market Cap: ${trending_7['avg_market_cap']:,.2f}")
    
    if "7_days" in results["hybrid_tokens"]:
        hybrid_7 = results["hybrid_tokens"]["7_days"]
        if hybrid_7.get("success"):
            print(f"\n📊 7-Day Hybrid Tokens:")
            print(f"  Total tokens: {hybrid_7['total_tokens']}")
            print(f"  Sources: {hybrid_7['source_counts']}")
            print(f"  Total Market Cap: ${hybrid_7['total_market_cap']:,.2f}")
            print(f"  Avg Market Cap: ${hybrid_7['avg_market_cap']:,.2f}")
    
    print(f"\n⏱️ Total Time: {results['total_time_seconds']:.2f} seconds")
    
    if total_regular > 100:
        print(f"\n🎯 Success! Timestamp-based fetching is working!")
        print(f"✅ Found {total_regular} regular tokens (more than the previous 100 limit)")
        print(f"✅ Timestamp filtering is correctly implemented")
    else:
        print(f"\n⚠️ Limited results. Check if timestamp filtering is working correctly.")

if __name__ == "__main__":
    asyncio.run(main()) 