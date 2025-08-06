#!/usr/bin/env python3
"""
Test script to debug the amount issue
"""

import asyncio
import base58
import logging
from pumpportal_trader import PumpPortalTrader
from config import PUMPPORTAL_API_KEY

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_amount_debug():
    """Test amount handling"""
    
    # Your test private key (replace with your actual key)
    test_private_key = "23qVxyrvL1RjZE7q6TusWxqpc6oNNM4hA2vX9Lja2TBa1aaJE8dTJwAQxh7yfRrn1yDTywMujDJzLp6JkLzD1q1R"
    
    # Test token mint (replace with a real Pump.fun token)
    test_mint = "7zt1NddFfGNgsxrrVNW7HTTRLEpFp3EcWy9kewEypump"
    
    # Test amounts
    test_amounts = [0.001, 0.005, 0.01, 0.1]
    
    # Decode private key
    decoded_key = base58.b58decode(test_private_key)
    
    # Create trader instance
    trader = PumpPortalTrader(private_key=decoded_key)
    
    print("🔧 Testing Amount Handling")
    print("=" * 50)
    
    for amount in test_amounts:
        print(f"\n💰 Testing amount: {amount} SOL")
        print("-" * 40)
        
        # Test local transaction build
        print(f"📤 Testing local transaction build with amount: {amount}")
        try:
            tx_data = await trader.build_transaction("buy", test_mint, amount, 5.0)
            if tx_data:
                print(f"✅ Local transaction build successful for amount: {amount}")
            else:
                print(f"❌ Local transaction build failed for amount: {amount}")
        except Exception as e:
            print(f"❌ Local transaction build error for amount {amount}: {e}")
        
        # Test lightning transaction
        print(f"⚡ Testing lightning transaction with amount: {amount}")
        try:
            success, signature, token_amount = await trader.lightning_transaction(
                "buy", 
                test_mint, 
                amount, 
                5.0,
                pool="auto",
                skip_preflight="true",
                jito_only="false"
            )
            
            if success:
                print(f"✅ Lightning transaction successful for amount: {amount}")
                print(f"📝 Signature: {signature}")
                print(f"🪙 Token amount: {token_amount:,.0f}")
            else:
                print(f"❌ Lightning transaction failed for amount: {amount}")
                print(f"📝 Signature: {signature}")
                
        except Exception as e:
            print(f"❌ Lightning transaction error for amount {amount}: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Amount testing completed")

if __name__ == "__main__":
    # Check if API key is configured
    if not PUMPPORTAL_API_KEY:
        print("❌ PUMPPORTAL_API_KEY not configured in .env file")
        print("Please add your PumpPortal API key to the .env file")
        exit(1)
    
    print("🚀 Starting amount debug tests...")
    print(f"🔑 API Key configured: {'Yes' if PUMPPORTAL_API_KEY else 'No'}")
    
    # Run the tests
    asyncio.run(test_amount_debug()) 