#!/usr/bin/env python3
"""
Simple Pump.fun Helius Endpoint Test
"""

import asyncio
import aiohttp
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_pump_helius_endpoint():
    """Simple test of the Pump.fun Helius endpoint"""
    
    url = "https://pump-fe.helius-rpc.com/?api-key=1b8db865-a5a1-4535-9aec-01061440523b"
    
    print("🔍 Testing Pump.fun Helius Endpoint")
    print("=" * 50)
    print(f"URL: {url}")
    
    # Test 1: Basic connectivity
    print("\n1️⃣ Testing Basic Connectivity...")
    try:
        async with aiohttp.ClientSession() as session:
            # Simple health check
            async with session.get(url.replace("/?api-key=", "/health"), timeout=10) as response:
                print(f"   Health endpoint status: {response.status}")
                if response.status == 200:
                    print("   ✅ Health endpoint accessible")
                else:
                    print(f"   ⚠️ Health endpoint returned {response.status}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
    
    # Test 2: Basic RPC call
    print("\n2️⃣ Testing Basic RPC Call...")
    try:
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSlot",
            "params": []
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            ) as response:
                print(f"   RPC call status: {response.status}")
                
                if response.status == 200:
                    response_data = await response.json()
                    print(f"   ✅ RPC call successful")
                    print(f"   Response: {json.dumps(response_data, indent=2)}")
                else:
                    print(f"   ❌ RPC call failed with status {response.status}")
                    try:
                        error_text = await response.text()
                        print(f"   Error response: {error_text}")
                    except:
                        print("   Could not read error response")
                        
    except Exception as e:
        print(f"   ❌ RPC call failed: {e}")
    
    # Test 3: Check if it's a valid Helius endpoint
    print("\n3️⃣ Testing Helius-Specific Methods...")
    
    helius_methods = [
        "getAssetsByGroup",
        "getAssetsByOwner", 
        "getAsset",
        "searchAssets"
    ]
    
    for method in helius_methods:
        try:
            request_data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": []
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        if "error" in response_data:
                            error_msg = response_data["error"].get("message", "Unknown error")
                            print(f"   ⚠️ {method}: {error_msg}")
                        else:
                            print(f"   ✅ {method}: Available")
                    else:
                        print(f"   ❌ {method}: HTTP {response.status}")
                        
        except Exception as e:
            print(f"   ❌ {method}: {e}")
    
    # Test 4: Check for Pump.fun specific functionality
    print("\n4️⃣ Testing Pump.fun Specific Methods...")
    
    pump_methods = [
        "getPumpTokens",
        "getPumpTokenList",
        "getPumpRecentTokens",
        "getPumpTokenInfo"
    ]
    
    for method in pump_methods:
        try:
            request_data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": []
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        if "error" in response_data:
                            error_msg = response_data["error"].get("message", "Unknown error")
                            print(f"   ⚠️ {method}: {error_msg}")
                        else:
                            print(f"   ✅ {method}: Available")
                            print(f"   Data: {json.dumps(response_data.get('result', {}), indent=2)[:200]}...")
                    else:
                        print(f"   ❌ {method}: HTTP {response.status}")
                        
        except Exception as e:
            print(f"   ❌ {method}: {e}")

async def main():
    await test_pump_helius_endpoint()

if __name__ == "__main__":
    asyncio.run(main()) 