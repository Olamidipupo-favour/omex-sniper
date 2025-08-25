#!/usr/bin/env python3
"""
Test script for Solscan API integration
"""

import asyncio
import aiohttp
import logging
import ssl
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SSL context configuration for macOS compatibility
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class SolscanAPITester:
    """Test the Solscan API integration"""
    
    def __init__(self):
        self.base_url = "https://api-v2.solscan.io/v2/token/holder/total"
        self.headers = {
            "Origin": "https://solscan.io",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    async def test_token_holders(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """Test getting token holder information from Solscan API"""
        try:
            url = f"{self.base_url}?address={mint_address}"
            
            logger.info(f"🔍 Testing Solscan API for token: {mint_address}")
            logger.info(f"📡 URL: {url}")
            
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                async with session.get(url, headers=self.headers, timeout=10) as response:
                    logger.info(f"📡 Response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Success! Response: {data}")
                        return data
                    else:
                        error_body = await response.text()
                        logger.error(f"❌ HTTP {response.status} error: {error_body}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error testing Solscan API: {e}")
            return None
    
    async def test_holder_count_extraction(self, mint_address: str) -> Optional[int]:
        """Test extracting holder count from Solscan API response"""
        try:
            holder_data = await self.test_token_holders(mint_address)
            if not holder_data:
                return None
            
            # Extract holder count from Solscan response
            if 'success' in holder_data and holder_data['success'] and 'data' in holder_data:
                # Solscan API returns data as direct integer for holder count
                if isinstance(holder_data['data'], int):
                    count = holder_data['data']
                    logger.info(f"📊 Token {mint_address} has {count} holders (direct count)")
                    return int(count)
                elif isinstance(holder_data['data'], dict) and 'total' in holder_data['data']:
                    # Fallback for other response formats
                    count = holder_data['data']['total']
                    logger.info(f"📊 Token {mint_address} has {count} holders (from total)")
                    return int(count)
                elif isinstance(holder_data['data'], dict) and 'holders' in holder_data['data']:
                    # If total not available, count the holders array
                    count = len(holder_data['data']['holders'])
                    logger.info(f"📊 Token {mint_address} has {count} holders (from array)")
                    return int(count)
            else:
                logger.warning(f"⚠️ No holder count available for {mint_address}")
                logger.debug(f"📋 Full response structure: {holder_data}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error extracting holder count: {e}")
            return None
    
    async def test_multiple_tokens(self):
        """Test multiple different token types"""
        test_tokens = [
            # USDC (well-known token)
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            # SOL (wrapped)
            "So11111111111111111111111111111111111111112",
            # Random pump token
            "7C2DVGUgTQacpTxkkrobAnYMvof5ZoJMhSvocq4apump",
            # Another random token
            "92Dr8bwh6UyW6U9XrEiC5hsuoL9uuc3qkjVJyG7fpump"
        ]
        
        results = {}
        
        for mint in test_tokens:
            logger.info(f"\n{'='*60}")
            logger.info(f"🧪 Testing token: {mint}")
            logger.info(f"{'='*60}")
            
            holder_count = await self.test_holder_count_extraction(mint)
            results[mint] = holder_count
            
            # Small delay between requests to be respectful
            await asyncio.sleep(0.5)
        
        return results
    
    async def test_rate_limiting(self):
        """Test rate limiting behavior"""
        logger.info(f"\n{'='*60}")
        logger.info("🧪 Testing Rate Limiting")
        logger.info(f"{'='*60}")
        
        # Test rapid requests
        test_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        start_time = asyncio.get_event_loop().time()
        
        for i in range(5):
            logger.info(f"📡 Rapid request {i+1}/5")
            holder_count = await self.test_holder_count_extraction(test_mint)
            logger.info(f"   Result: {holder_count} holders")
            
            # Very small delay
            await asyncio.sleep(0.1)
        
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        
        logger.info(f"📊 Rate limiting test completed in {total_time:.2f} seconds")
        logger.info(f"   Average time per request: {total_time/5:.2f} seconds")
    
    async def test_error_handling(self):
        """Test error handling with invalid tokens"""
        logger.info(f"\n{'='*60}")
        logger.info("🧪 Testing Error Handling")
        logger.info(f"{'='*60}")
        
        invalid_tokens = [
            "invalid_mint_address",
            "1234567890abcdef",
            "",
            "not_a_real_token"
        ]
        
        for invalid_mint in invalid_tokens:
            logger.info(f"🔍 Testing invalid token: {invalid_mint}")
            result = await self.test_holder_count_extraction(invalid_mint)
            logger.info(f"   Result: {result}")
            await asyncio.sleep(0.2)

async def main():
    """Main test function"""
    logger.info("🔍 Solscan API Integration Test")
    logger.info("=" * 60)
    
    try:
        # Create tester
        tester = SolscanAPITester()
        
        # Test single token
        logger.info("🚀 Testing single token...")
        usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        holder_count = await tester.test_holder_count_extraction(usdc_mint)
        
        if holder_count is not None:
            logger.info(f"✅ Single token test successful: {holder_count} holders")
        else:
            logger.error("❌ Single token test failed")
        
        # Test multiple tokens
        logger.info("\n🚀 Testing multiple tokens...")
        results = await tester.test_multiple_tokens()
        
        # Test rate limiting
        await tester.test_rate_limiting()
        
        # Test error handling
        await tester.test_error_handling()
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("📊 Test Summary")
        logger.info(f"{'='*60}")
        
        successful_tests = sum(1 for count in results.values() if count is not None)
        total_tests = len(results)
        
        logger.info(f"✅ Successful tests: {successful_tests}/{total_tests}")
        
        for mint, count in results.items():
            status = "✅" if count is not None else "❌"
            logger.info(f"   {status} {mint[:8]}...: {count if count is not None else 'Failed'}")
        
        if successful_tests == total_tests:
            logger.info("\n🎉 All tests passed! Solscan API integration is working correctly.")
        else:
            logger.warning(f"\n⚠️ {total_tests - successful_tests} tests failed. Check the logs above.")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main())
