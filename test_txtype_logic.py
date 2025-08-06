#!/usr/bin/env python3
"""
Test the simplified txType-based message handling logic
"""

import json
import logging
from pump_fun_monitor import PumpPortalMonitor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_txtype_logic():
    """Test the simplified txType-based logic"""
    monitor = PumpPortalMonitor()
    
    # Test data samples
    test_messages = [
        # Token creation
        {
            "signature": "test_sig_1",
            "mint": "test_token_1",
            "symbol": "TEST1",
            "name": "Test Token 1",
            "txType": "create",
            "pool": "pump"
        },
        # Buy trade
        {
            "signature": "test_sig_2",
            "mint": "test_token_2",
            "traderPublicKey": "trader_1",
            "txType": "buy",
            "tokenAmount": 1000000,
            "solAmount": 0.1,
            "pool": "pump"
        },
        # Sell trade
        {
            "signature": "test_sig_3",
            "mint": "test_token_2",
            "traderPublicKey": "trader_2",
            "txType": "sell",
            "tokenAmount": 500000,
            "solAmount": 0.05,
            "pool": "pump"
        },
        # Unknown txType
        {
            "signature": "test_sig_4",
            "mint": "test_token_3",
            "txType": "unknown",
            "pool": "pump"
        },
        # Non-pump pool
        {
            "signature": "test_sig_5",
            "mint": "test_token_4",
            "txType": "buy",
            "pool": "other"
        }
    ]
    
    logger.info("🧪 Testing simplified txType-based logic...")
    
    for i, test_data in enumerate(test_messages):
        logger.info(f"\n--- Test {i+1} ---")
        logger.info(f"Input data: {json.dumps(test_data, indent=2)}")
        
        # Simulate the message handling logic
        tx_type = test_data.get('txType', '')
        pool = test_data.get('pool', '')
        
        logger.info(f"txType: {tx_type}")
        logger.info(f"pool: {pool}")
        
        if pool != "pump":
            logger.info("⏭️ SKIPPING - Not a pump pool")
            continue
            
        if tx_type == 'create':
            logger.info("🆕 PROCESSING NEW TOKEN")
        elif tx_type in ['buy', 'sell']:
            logger.info(f"📊 PROCESSING TRADE: {tx_type}")
        else:
            logger.info(f"⏭️ Unknown txType: {tx_type}, skipping")
    
    logger.info("\n✅ Test completed!")

if __name__ == "__main__":
    test_txtype_logic() 