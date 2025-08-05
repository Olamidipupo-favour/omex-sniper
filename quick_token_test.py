#!/usr/bin/env python3
"""
Quick Token Test - Simple test to verify token fetching works
"""

import asyncio
import json
import logging
from token_filter_service import TokenFilterService
from config import HELIUS_RPC_URL

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def quick_test():
    """Quick test of token fetching"""
    print("🔍 Quick Token Fetching Test")
    print("=" * 40)
    
    # Initialize token service
    token_service = TokenFilterService(helius_rpc_url=HELIUS_RPC_URL)
    print(f"🔧 Using RPC: {token_service.helius_rpc_url}")
    
    try:
        # Test 1: Simple fallback (should always work)
        print("\n1️⃣ Testing Simple Fallback...")
        simple_tokens = await token_service.get_recent_tokens_simple(days=7)
        print(f"   ✅ Found {len(simple_tokens)} tokens")
        if simple_tokens:
            print(f"   📋 Sample: {simple_tokens[0].get('mint', 'N/A')}")
        
        # Test 2: Pump.fun API
        print("\n2️⃣ Testing Pump.fun API...")
        try:
            pump_tokens = await token_service.get_recent_pump_tokens(days=7)
            print(f"   ✅ Found {len(pump_tokens)} tokens")
            if pump_tokens:
                print(f"   📋 Sample: {pump_tokens[0].get('mint', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Failed: {str(e)[:100]}...")
        
        # Test 3: Helius RPC
        print("\n3️⃣ Testing Helius RPC...")
        try:
            helius_tokens = await token_service.get_recent_tokens_from_helius(days=7)
            print(f"   ✅ Found {len(helius_tokens)} tokens")
            if helius_tokens:
                print(f"   📋 Sample: {helius_tokens[0].get('mint', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Failed: {str(e)[:100]}...")
        
        # Test 4: Hybrid approach
        print("\n4️⃣ Testing Hybrid Approach...")
        try:
            hybrid_tokens = await token_service.get_hybrid_recent_tokens(days=7, include_pump_only=False)
            print(f"   ✅ Found {len(hybrid_tokens)} tokens")
            if hybrid_tokens:
                print(f"   📋 Sample: {hybrid_tokens[0].get('mint', 'N/A')}")
                
                # Test filtering
                print("\n5️⃣ Testing Token Filtering...")
                filtered_new = token_service.filter_tokens_by_age(hybrid_tokens, "new_only")
                filtered_7days = token_service.filter_tokens_by_age(hybrid_tokens, "last_7_days")
                print(f"   📊 New only: {len(filtered_new)} tokens")
                print(f"   📊 Last 7 days: {len(filtered_7days)} tokens")
        except Exception as e:
            print(f"   ❌ Failed: {str(e)[:100]}...")
        
        print("\n✅ Quick test completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(quick_test()) 