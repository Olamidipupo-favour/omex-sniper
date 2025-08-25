#!/usr/bin/env python3
"""
Test script for price updates from websocket trades
"""

import asyncio
import logging
import time
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockWebSocketData:
    """Mock websocket data for testing price calculations"""
    
    @staticmethod
    def get_buy_trade_data():
        """Get sample buy trade data"""
        return {
            "signature": "test_signature_123",
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
            "pool": "pump",
            "symbol": "TEST",
            "name": "Test Token"
        }
    
    @staticmethod
    def get_sell_trade_data():
        """Get sample sell trade data"""
        return {
            "signature": "test_signature_456",
            "mint": "7C2DVGUgTQacpTxkkrobAnYMvof5ZoJMhSvocq4apump",
            "traderPublicKey": "952LPLt7zzU4RGUmBoPV7zQwsCire85P12Ht6Tp8Dno9",
            "txType": "sell",
            "tokenAmount": 100.0,
            "solAmount": 0.005,
            "newTokenBalance": 254.840158,
            "bondingCurveKey": "4NpdiJWdvbQReo6WQ7PKn32EM1ZjuPwJBJBgr5Qx8jRA",
            "vTokensInBondingCurve": 1068751551.098624,
            "vSolInBondingCurve": 30.124251714755496,
            "marketCapSol": 28.186712452836344,
            "pool": "pump",
            "symbol": "TEST",
            "name": "Test Token"
        }

class MockPriceUpdateHandler:
    """Mock price update handler for testing"""
    
    def __init__(self):
        self.price_updates = []
        self.sol_price_usd = 100.0  # Mock SOL price
    
    def handle_price_update(self, mint: str, price_sol: float, price_usd: float):
        """Handle price updates"""
        update = {
            'mint': mint,
            'price_sol': price_sol,
            'price_usd': price_usd,
            'timestamp': int(time.time())
        }
        self.price_updates.append(update)
        logger.info(f"💰 Price update: {mint} = {price_sol:.12f} SOL (${price_usd:.8f})")
    
    def calculate_price_from_bonding_curve(self, v_sol: float, v_tokens: float) -> tuple[float, float]:
        """Calculate price from bonding curve data"""
        if v_sol > 0 and v_tokens > 0:
            price_sol = v_sol / v_tokens
            price_usd = price_sol * self.sol_price_usd
            return price_sol, price_usd
        return 0.0, 0.0
    
    def process_trade_data(self, data: Dict[str, Any]):
        """Process trade data and calculate price immediately"""
        mint = data.get("mint", "")
        if not mint:
            logger.error("❌ No mint address in trade data")
            return
        
        # Extract bonding curve data
        v_sol_in_bonding_curve = data.get("vSolInBondingCurve", 0.0)
        v_tokens_in_bonding_curve = data.get("vTokensInBondingCurve", 0.0)
        
        # Calculate price immediately
        if v_sol_in_bonding_curve > 0 and v_tokens_in_bonding_curve > 0:
            current_price_sol, current_price_usd = self.calculate_price_from_bonding_curve(
                v_sol_in_bonding_curve, v_tokens_in_bonding_curve
            )
            
            logger.info(f"💰 IMMEDIATE PRICE CALCULATION for {mint}:")
            logger.info(f"   vSolInBondingCurve: {v_sol_in_bonding_curve:.6f} SOL")
            logger.info(f"   vTokensInBondingCurve: {v_tokens_in_bonding_curve:,.0f}")
            logger.info(f"   Current Price: {current_price_sol:.12f} SOL (${current_price_usd:.8f})")
            
            # Handle price update immediately
            self.handle_price_update(mint, current_price_sol, current_price_usd)
            
            return current_price_sol, current_price_usd
        else:
            logger.warning(f"⚠️ No bonding curve data available for price calculation: {mint}")
            return 0.0, 0.0

async def test_price_calculations():
    """Test price calculations from websocket data"""
    logger.info("🚀 Starting Price Calculation Test")
    
    # Create mock handler
    handler = MockPriceUpdateHandler()
    
    # Test buy trade
    logger.info("\n" + "="*60)
    logger.info("🧪 Testing BUY trade price calculation")
    logger.info("="*60)
    
    buy_data = MockWebSocketData.get_buy_trade_data()
    buy_price_sol, buy_price_usd = handler.process_trade_data(buy_data)
    
    # Verify price calculation
    expected_price_sol = buy_data["vSolInBondingCurve"] / buy_data["vTokensInBondingCurve"]
    expected_price_usd = expected_price_sol * handler.sol_price_usd
    
    logger.info(f"📊 Buy Trade Results:")
    logger.info(f"   Calculated Price: {buy_price_sol:.12f} SOL")
    logger.info(f"   Expected Price: {expected_price_sol:.12f} SOL")
    logger.info(f"   Price Match: {'✅' if abs(buy_price_sol - expected_price_sol) < 1e-12 else '❌'}")
    
    # Test sell trade
    logger.info("\n" + "="*60)
    logger.info("🧪 Testing SELL trade price calculation")
    logger.info("="*60)
    
    sell_data = MockWebSocketData.get_sell_trade_data()
    sell_price_sol, sell_price_usd = handler.process_trade_data(sell_data)
    
    # Verify price calculation
    expected_price_sol = sell_data["vSolInBondingCurve"] / sell_data["vTokensInBondingCurve"]
    expected_price_usd = expected_price_sol * handler.sol_price_usd
    
    logger.info(f"📊 Sell Trade Results:")
    logger.info(f"   Calculated Price: {sell_price_sol:.12f} SOL")
    logger.info(f"   Expected Price: {expected_price_sol:.12f} SOL")
    logger.info(f"   Price Match: {'✅' if abs(sell_price_sol - expected_price_sol) < 1e-12 else '❌'}")
    
    # Test price change
    logger.info("\n" + "="*60)
    logger.info("🧪 Testing Price Change Analysis")
    logger.info("="*60)
    
    if buy_price_sol > 0 and sell_price_sol > 0:
        price_change_sol = sell_price_sol - buy_price_sol
        price_change_percent = (price_change_sol / buy_price_sol) * 100 if buy_price_sol > 0 else 0
        
        logger.info(f"📊 Price Change Analysis:")
        logger.info(f"   Buy Price: {buy_price_sol:.12f} SOL")
        logger.info(f"   Sell Price: {sell_price_sol:.12f} SOL")
        logger.info(f"   Change: {price_change_sol:+.12f} SOL ({price_change_percent:+.2f}%)")
        
        if price_change_sol > 0:
            logger.info("📈 Price increased (positive change)")
        elif price_change_sol < 0:
            logger.info("📉 Price decreased (negative change)")
        else:
            logger.info("➡️ Price unchanged")
    
    # Test multiple price updates
    logger.info("\n" + "="*60)
    logger.info("🧪 Testing Multiple Price Updates")
    logger.info("="*60)
    
    # Simulate multiple trades with different prices
    test_prices = [
        (30.119251714755496, 1068751651.098624),  # Original
        (30.124251714755496, 1068751551.098624),  # After sell
        (30.129251714755496, 1068751451.098624),  # After another trade
        (30.134251714755496, 1068751351.098624),  # After another trade
    ]
    
    for i, (v_sol, v_tokens) in enumerate(test_prices):
        price_sol, price_usd = handler.calculate_price_from_bonding_curve(v_sol, v_tokens)
        handler.handle_price_update("TEST_MINT", price_sol, price_usd)
        
        logger.info(f"   Update {i+1}: {price_sol:.12f} SOL (${price_usd:.8f})")
        await asyncio.sleep(0.1)  # Small delay
    
    logger.info(f"📊 Total price updates received: {len(handler.price_updates)}")
    
    return handler.price_updates

async def test_performance():
    """Test performance of price calculations"""
    logger.info("\n🚀 Starting Performance Test")
    
    handler = MockPriceUpdateHandler()
    
    # Test data
    v_sol = 30.119251714755496
    v_tokens = 1068751651.098624
    
    # Performance test
    iterations = 1000
    start_time = time.time()
    
    for i in range(iterations):
        price_sol, price_usd = handler.calculate_price_from_bonding_curve(v_sol, v_tokens)
        handler.handle_price_update(f"TEST_MINT_{i}", price_sol, price_usd)
    
    end_time = time.time()
    total_time = end_time - start_time
    operations_per_second = iterations / total_time
    
    logger.info(f"📊 Performance Results:")
    logger.info(f"   Iterations: {iterations}")
    logger.info(f"   Total Time: {total_time:.4f} seconds")
    logger.info(f"   Operations/Second: {operations_per_second:.2f}")
    logger.info(f"   Average Time per Operation: {(total_time/iterations)*1000:.4f} ms")

async def main():
    """Main test function"""
    logger.info("🔍 WebSocket Price Update Test")
    logger.info("=" * 60)
    
    try:
        # Test price calculations
        price_updates = await test_price_calculations()
        
        # Test performance
        await test_performance()
        
        logger.info("\n✅ All tests completed successfully!")
        logger.info(f"📊 Total price updates processed: {len(price_updates)}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main())
