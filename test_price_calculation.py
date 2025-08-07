#!/usr/bin/env python3
"""
Test price calculation using bonding curve data
"""

import json
from pump_fun_monitor import PumpPortalMonitor

# Sample WebSocket data from your logs
sample_data = {
    "signature": "2gYreniQbNZQCnjSexm5vVdyN2kzEmEuv72aLWrJDFVGPQY6oUs6woQtCRakfeWeSvXXq8iEw9UdSmHj17zZtaBC",
    "mint": "7C2DVGUgTQacpTxkkrobAnYMvof5ZoJMhSvocq4apump",
    "traderPublicKey": "952LPLt7zzU4RGUmBoPV7zQwsCire85P12Ht6Tp8Dno9",
    "txType": "buy",
    "tokenAmount": 354.840158,
    "solAmount": 0.00001,
    "newTokenBalance": 354.840158,
    "bondingCurveKey": "4NpdiJWdvbQReo6WQ7PKn32EM1ZjuPwJBJBgr5Qx8jRA",
    "vTokensInBondingCurve": 1068751651.098624,
    "vSolInBondingCurve": 30.119251714755496,
    "marketCapSol": 28.181712452836344,
    "pool": "pump"
}

def test_price_calculation():
    """Test price calculation methods"""
    
    # Method 1: Using bonding curve data (recommended)
    v_sol_in_bonding_curve = sample_data.get("vSolInBondingCurve", 0.0)
    v_tokens_in_bonding_curve = sample_data.get("vTokensInBondingCurve", 0.0)
    
    if v_sol_in_bonding_curve > 0 and v_tokens_in_bonding_curve > 0:
        bonding_curve_price = v_sol_in_bonding_curve / v_tokens_in_bonding_curve
        print(f"💰 Bonding Curve Price: {bonding_curve_price:.12f} SOL")
        print(f"   vSolInBondingCurve: {v_sol_in_bonding_curve}")
        print(f"   vTokensInBondingCurve: {v_tokens_in_bonding_curve:,.0f}")
    
    # Method 2: Using transaction data (fallback)
    sol_amount = sample_data.get("solAmount", 0.0)
    token_amount = sample_data.get("tokenAmount", 0.0)
    
    if token_amount > 0:
        transaction_price = sol_amount / token_amount
        print(f"💰 Transaction Price: {transaction_price:.12f} SOL")
        print(f"   solAmount: {sol_amount}")
        print(f"   tokenAmount: {token_amount:,.0f}")
    
    # Method 3: Market cap based (for reference)
    market_cap_sol = sample_data.get("marketCapSol", 0.0)
    print(f"💰 Market Cap (SOL): {market_cap_sol:.6f} SOL")
    
    # Compare methods
    print(f"\n📊 Comparison:")
    print(f"   Bonding Curve Price: {bonding_curve_price:.12f} SOL")
    print(f"   Transaction Price:   {transaction_price:.12f} SOL")
    print(f"   Difference:          {abs(bonding_curve_price - transaction_price):.12f} SOL")
    
    # Test the actual parsing function
    monitor = PumpPortalMonitor()
    trade_info = monitor.parse_trade_data(sample_data)
    
    print(f"\n🎯 Parsed TradeInfo:")
    print(f"   Price: {trade_info.price:.12f} SOL")
    print(f"   Method used: {'Bonding Curve' if v_sol_in_bonding_curve > 0 and v_tokens_in_bonding_curve > 0 else 'Transaction'}")

if __name__ == "__main__":
    test_price_calculation() 