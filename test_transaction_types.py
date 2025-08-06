#!/usr/bin/env python3
"""
Test script to verify both local and lightning transaction types work
"""

import asyncio
import base58
import logging
from pumpportal_trader import PumpPortalTrader
from config import PUMPPORTAL_API_KEY

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_transaction_types():
    """Test both local and lightning transaction types"""
    
    # Your test private key (replace with your actual key)
    test_private_key = "23qVxyrvL1RjZE7q6TusWxqpc6oNNM4hA2vX9Lja2TBa1aaJE8dTJwAQxh7yfRrn1yDTywMujDJzLp6JkLzD1q1R"
    
    # Test token mint (replace with a real Pump.fun token)
    test_mint = "7zt1NddFfGNgsxrrVNW7HTTRLEpFp3EcWy9kewEypump"
    
    # Decode private key
    decoded_key = base58.b58decode(test_private_key)
    
    # Create trader instance
    trader = PumpPortalTrader(private_key=decoded_key)
    
    print("🔧 Testing Transaction Types")
    print("=" * 50)
    
    # Test 1: Local Transaction (Build only)
    print("\n📤 Test 1: Local Transaction (Build only)")
    print("-" * 40)
    
    try:
        # Build transaction locally (don't send)
        tx_data = await trader.build_transaction("buy", test_mint, 0.001, 5.0)
        if tx_data:
            print("✅ Local transaction build successful")
            print(f"📦 Transaction data type: {type(tx_data)}")
            if "transaction" in tx_data:
                tx = tx_data["transaction"]
                if isinstance(tx, str):
                    print(f"📦 Transaction length: {len(tx)} characters")
                elif isinstance(tx, bytes):
                    print(f"📦 Transaction length: {len(tx)} bytes")
        else:
            print("❌ Local transaction build failed")
    except Exception as e:
        print(f"❌ Local transaction build error: {e}")
    
    # Test 2: Lightning Transaction (API call only)
    print("\n⚡ Test 2: Lightning Transaction (API call only)")
    print("-" * 40)
    
    try:
        # Test lightning transaction (don't execute, just check API)
        success, signature, token_amount = await trader.lightning_transaction(
            "buy", 
            test_mint, 
            0.001, 
            5.0,
            pool="auto",
            skip_preflight="true",
            jito_only="false"
        )
        
        if success:
            print("✅ Lightning transaction successful")
            print(f"📝 Signature: {signature}")
            print(f"🪙 Token amount: {token_amount:,.0f}")
        else:
            print("❌ Lightning transaction failed")
            print(f"📝 Signature: {signature}")
            
    except Exception as e:
        print(f"❌ Lightning transaction error: {e}")
    
    # Test 3: Buy Token with Local Transaction
    print("\n💰 Test 3: Buy Token with Local Transaction")
    print("-" * 40)
    
    try:
        success, signature, token_amount = await trader.buy_token(
            test_mint, 
            0.001, 
            transaction_type="local"
        )
        
        if success:
            print("✅ Local buy successful")
            print(f"📝 Signature: {signature}")
            print(f"🪙 Token amount: {token_amount:,.0f}")
        else:
            print("❌ Local buy failed")
            print(f"📝 Signature: {signature}")
            
    except Exception as e:
        print(f"❌ Local buy error: {e}")
    
    # Test 4: Buy Token with Lightning Transaction
    print("\n⚡ Test 4: Buy Token with Lightning Transaction")
    print("-" * 40)
    
    try:
        success, signature, token_amount = await trader.buy_token(
            test_mint, 
            0.001, 
            transaction_type="lightning"
        )
        
        if success:
            print("✅ Lightning buy successful")
            print(f"📝 Signature: {signature}")
            print(f"🪙 Token amount: {token_amount:,.0f}")
        else:
            print("❌ Lightning buy failed")
            print(f"📝 Signature: {signature}")
            
    except Exception as e:
        print(f"❌ Lightning buy error: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Transaction type testing completed")

if __name__ == "__main__":
    # Check if API key is configured
    if not PUMPPORTAL_API_KEY:
        print("❌ PUMPPORTAL_API_KEY not configured in .env file")
        print("Please add your PumpPortal API key to the .env file")
        exit(1)
    
    print("🚀 Starting transaction type tests...")
    print(f"🔑 API Key configured: {'Yes' if PUMPPORTAL_API_KEY else 'No'}")
    
    # Run the tests
    asyncio.run(test_transaction_types()) 