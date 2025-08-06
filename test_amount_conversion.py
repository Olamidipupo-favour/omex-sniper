#!/usr/bin/env python3
"""
Simple test to check amount conversion
"""

def test_amount_conversion():
    """Test amount conversion logic"""
    
    test_amounts = [0.001, 0.005, 0.01, 0.1, 1.0]
    
    print("🔧 Testing Amount Conversion")
    print("=" * 50)
    
    for amount in test_amounts:
        print(f"\n💰 Original amount: {amount} SOL")
        print(f"📊 Type: {type(amount)}")
        
        # Test the conversion logic
        lamports = int(amount * 1e9)
        print(f"🪙 Converted to lamports: {lamports}")
        print(f"📊 Lamports type: {type(lamports)}")
        
        # Test the problematic conversion
        try:
            problematic = int(amount) * 1e9
            print(f"❌ Problematic conversion: {problematic}")
        except Exception as e:
            print(f"❌ Error in problematic conversion: {e}")
        
        # Test the correct conversion
        try:
            correct = int(amount * 1e9)
            print(f"✅ Correct conversion: {correct}")
        except Exception as e:
            print(f"❌ Error in correct conversion: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Amount conversion testing completed")

if __name__ == "__main__":
    test_amount_conversion() 