#!/usr/bin/env python3
"""
Pump.fun API Endpoints Test - Find the correct API endpoints
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PumpAPIEndpointTester:
    """Test different Pump.fun API endpoints"""
    
    def __init__(self):
        self.base_urls = [
            "https://frontend-api-v3.pump.fun",
            "https://api.pump.fun",
            "https://pump.fun/api",
            "https://client-api-2-74b1891ee9f9.pump.fun"
        ]
        
        self.endpoints_to_test = [
            "/tokens",
            "/api/tokens",
            "/v1/tokens",
            "/v3/tokens",
            "/tokens/list",
            "/api/tokens/list",
            "/tokens/recent",
            "/api/tokens/recent",
            "/",
            "/api",
            "/health",
            "/status"
        ]
    
    async def test_endpoint(self, base_url: str, endpoint: str) -> Dict:
        """Test a specific endpoint"""
        try:
            url = f"{base_url}{endpoint}"
            logger.info(f"🔍 Testing: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    result = {
                        "url": url,
                        "status": response.status,
                        "success": response.status == 200,
                        "content_type": response.headers.get('content-type', ''),
                        "content_length": len(await response.read()) if response.status == 200 else 0
                    }
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            result["data_sample"] = str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
                        except:
                            result["data_sample"] = "Not JSON"
                    
                    logger.info(f"   Status: {response.status}, Content-Type: {result['content_type']}")
                    return result
                    
        except Exception as e:
            logger.error(f"   Error: {str(e)}")
            return {
                "url": f"{base_url}{endpoint}",
                "status": "ERROR",
                "success": False,
                "error": str(e)
            }
    
    async def test_all_endpoints(self) -> Dict:
        """Test all combinations of base URLs and endpoints"""
        logger.info("🚀 Starting Pump.fun API Endpoint Test...")
        
        results = []
        
        for base_url in self.base_urls:
            logger.info(f"\n🔧 Testing base URL: {base_url}")
            
            for endpoint in self.endpoints_to_test:
                result = await self.test_endpoint(base_url, endpoint)
                results.append(result)
                
                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.1)
        
        # Find successful endpoints
        successful = [r for r in results if r.get("success", False)]
        
        summary = {
            "total_tested": len(results),
            "successful": len(successful),
            "failed": len(results) - len(successful),
            "successful_endpoints": successful,
            "all_results": results
        }
        
        logger.info(f"\n📊 Summary:")
        logger.info(f"   Total tested: {summary['total_tested']}")
        logger.info(f"   Successful: {summary['successful']}")
        logger.info(f"   Failed: {summary['failed']}")
        
        if successful:
            logger.info(f"\n✅ Successful endpoints:")
            for endpoint in successful:
                logger.info(f"   {endpoint['url']} (Status: {endpoint['status']})")
        
        return summary
    
    async def test_known_pump_tokens(self) -> Dict:
        """Test with known Pump.fun token addresses"""
        logger.info("\n🧪 Testing with known Pump.fun tokens...")
        
        # Some known token addresses that might be on Pump.fun
        known_tokens = [
            "So11111111111111111111111111111111111111112",  # WSOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
        ]
        
        results = []
        
        for token in known_tokens:
            logger.info(f"🔍 Testing token: {token}")
            
            # Test individual token endpoint
            url = f"https://frontend-api-v3.pump.fun/token/{token}"
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as response:
                        result = {
                            "token": token,
                            "url": url,
                            "status": response.status,
                            "success": response.status == 200
                        }
                        
                        if response.status == 200:
                            try:
                                data = await response.json()
                                result["data"] = data
                                logger.info(f"   ✅ Found token data")
                            except:
                                logger.info(f"   ⚠️ Response not JSON")
                        else:
                            logger.info(f"   ❌ Status: {response.status}")
                        
                        results.append(result)
                        
            except Exception as e:
                logger.error(f"   ❌ Error: {str(e)}")
                results.append({
                    "token": token,
                    "url": url,
                    "status": "ERROR",
                    "success": False,
                    "error": str(e)
                })
        
        return results

async def main():
    """Main test function"""
    print("🔍 Pump.fun API Endpoints Test")
    print("=" * 50)
    
    # Create tester
    tester = PumpAPIEndpointTester()
    
    # Test all endpoints
    endpoint_results = await tester.test_all_endpoints()
    
    # Test known tokens
    token_results = await tester.test_known_pump_tokens()
    
    # Save results
    all_results = {
        "endpoint_test": endpoint_results,
        "token_test": token_results
    }
    
    with open("pump_api_test_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to pump_api_test_results.json")
    
    # Print summary
    print(f"\n📋 Endpoint Test Summary:")
    print(f"   Successful endpoints: {endpoint_results['successful']}")
    
    if endpoint_results['successful'] > 0:
        print(f"\n✅ Working endpoints found!")
        for endpoint in endpoint_results['successful_endpoints']:
            print(f"   {endpoint['url']}")
    
    print(f"\n📋 Token Test Summary:")
    successful_tokens = [r for r in token_results if r.get("success", False)]
    print(f"   Tokens with data: {len(successful_tokens)}")

if __name__ == "__main__":
    asyncio.run(main()) 