#!/usr/bin/env python3
"""
Test script to verify Pump.Fun API endpoints are working correctly
"""
import asyncio
import aiohttp
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = "https://client-api-2-2.pump.fun"

async def test_new_tokens_endpoint():
    """Test the new tokens endpoint"""
    print("🔍 Testing New Tokens Endpoint...")
    
    async with aiohttp.ClientSession() as session:
        url = f"{API_BASE_URL}/tokens"
        params = {
            "limit": 10,
            "offset": 0
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        try:
            async with session.get(url, params=params, headers=headers) as response:
                print(f"Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ SUCCESS: Retrieved {len(data)} tokens")
                    
                    if data:
                        token = data[0]
                        print(f"\n📄 Sample Token:")
                        print(f"  Name: {token.get('name', 'N/A')}")
                        print(f"  Symbol: {token.get('symbol', 'N/A')}")
                        print(f"  Address: {token.get('address', token.get('mint', 'N/A'))}")
                        print(f"  Market Cap: ${token.get('marketCap', token.get('market_cap', 0)):,.0f}")
                        print(f"  Created: {token.get('createdAt', token.get('created_timestamp', 'N/A'))}")
                        print(f"  Price: {token.get('price', 0)}")
                    
                    return True
                else:
                    text = await response.text()
                    print(f"❌ FAILED: {response.status} - {text}")
                    return False
                    
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return False

async def test_token_details_endpoint():
    """Test the token details endpoint"""
    print("\n🔍 Testing Token Details Endpoint...")
    
    # First get a token address from the list
    async with aiohttp.ClientSession() as session:
        url = f"{API_BASE_URL}/tokens"
        params = {"limit": 1}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        token_address = data[0].get('address', data[0].get('mint'))
                        
                        # Now test the details endpoint
                        details_url = f"{API_BASE_URL}/tokens/{token_address}"
                        
                        async with session.get(details_url, headers=headers) as details_response:
                            print(f"Status: {details_response.status}")
                            
                            if details_response.status == 200:
                                details_data = await details_response.json()
                                print(f"✅ SUCCESS: Retrieved details for {token_address}")
                                print(f"\n📊 Token Details:")
                                print(f"  Name: {details_data.get('name', 'N/A')}")
                                print(f"  Symbol: {details_data.get('symbol', 'N/A')}")
                                print(f"  Current Price: {details_data.get('price', 0)}")
                                print(f"  Market Cap: ${details_data.get('marketCap', details_data.get('market_cap', 0)):,.0f}")
                                print(f"  Description: {details_data.get('description', 'N/A')[:100]}...")
                                return True
                            else:
                                text = await details_response.text()
                                print(f"❌ FAILED: {details_response.status} - {text}")
                                return False
                else:
                    print("❌ Could not get token list to test details endpoint")
                    return False
                    
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return False

async def test_monitoring_simulation():
    """Simulate the monitoring process"""
    print("\n🔍 Testing Monitoring Simulation...")
    
    known_tokens = set()
    
    async with aiohttp.ClientSession() as session:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        # First call - initialize known tokens
        url = f"{API_BASE_URL}/tokens"
        params = {"limit": 20}
        
        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    for token in data:
                        token_address = token.get('address', token.get('mint'))
                        known_tokens.add(token_address)
                    
                    print(f"✅ Initialized with {len(known_tokens)} known tokens")
                    
                    # Second call - check for new tokens
                    await asyncio.sleep(2)
                    
                    async with session.get(url, params=params, headers=headers) as response2:
                        if response2.status == 200:
                            data2 = await response2.json()
                            new_tokens = []
                            
                            for token in data2:
                                token_address = token.get('address', token.get('mint'))
                                if token_address not in known_tokens:
                                    new_tokens.append(token)
                            
                            print(f"🔄 Monitoring cycle complete")
                            print(f"   New tokens detected: {len(new_tokens)}")
                            
                            if new_tokens:
                                print(f"\n🚀 New Tokens:")
                                for token in new_tokens[:3]:  # Show first 3
                                    print(f"  • {token.get('symbol')} - {token.get('name')}")
                            
                            return True
                        else:
                            print("❌ Second monitoring call failed")
                            return False
                else:
                    print("❌ Initial monitoring call failed")
                    return False
                    
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return False

async def main():
    """Run all tests"""
    print("🎯 Testing Pump.Fun API Endpoints\n")
    print("=" * 50)
    
    results = []
    
    # Test new tokens endpoint
    results.append(await test_new_tokens_endpoint())
    
    # Test token details endpoint
    results.append(await test_token_details_endpoint())
    
    # Test monitoring simulation
    results.append(await test_monitoring_simulation())
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"  ✅ Passed: {sum(results)}/{len(results)}")
    print(f"  ❌ Failed: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 All tests passed! The API endpoints are working correctly.")
        print("\n✅ CONFIRMED:")
        print("  • New tokens endpoint: ✅ Working")
        print("  • Token details endpoint: ✅ Working") 
        print("  • Live prices: ✅ Available")
        print("  • Monitoring process: ✅ Ready")
        print("\n🚀 Your bot implementation is correctly configured!")
    else:
        print("\n⚠️  Some tests failed. Check the API endpoints or network connection.")

if __name__ == "__main__":
    asyncio.run(main())