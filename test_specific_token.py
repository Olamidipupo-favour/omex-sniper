#!/usr/bin/env python3
"""
Simple Test Script - Test buy/sell with a specific token
Usage: python3 test_specific_token.py <token_mint> <action> [amount]
"""

import asyncio
import sys
import logging
import base58
import os
from solders.keypair import Keypair
from pumpportal_trader import PumpPortalTrader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_specific_token():
    """Test with a specific token"""
    
    # Parse command line arguments
    if len(sys.argv) < 3:
        print("Usage: python3 test_specific_token.py <token_mint> <action> [amount]")
        print("Actions: build_buy, build_sell, buy, sell, balance")
        print("Example: python3 test_specific_token.py <mint> build_buy 0.1")
        return
    
    token_mint = sys.argv[1]
    action = sys.argv[2]
    amount = float(sys.argv[3]) if len(sys.argv) > 3 else 0.1
    
    # Setup test wallet
    test_private_key = os.getenv("TEST_PRIVATE_KEY", "")
    
    if test_private_key:
        try:
            decoded_key = base58.b58decode(test_private_key)
            keypair = Keypair.from_bytes(decoded_key)
            logger.info(f"✅ Using test wallet: {str(keypair.pubkey())}")
        except Exception as e:
            logger.error(f"❌ Invalid private key: {e}")
            return
    else:
        # Generate new test wallet
        keypair = Keypair()
        test_private_key = base58.b58encode(keypair.secret()).decode()
        logger.info(f"✅ Generated new test wallet: {str(keypair.pubkey())}")
        logger.info(f"🔑 Private key: {test_private_key}")
        logger.info("💡 Set TEST_PRIVATE_KEY env var to reuse this wallet")
    
    # Initialize trader
    trader = PumpPortalTrader(
        private_key=base58.b58decode(test_private_key),  # Pass decoded bytes
        rpc_url="https://api.devnet.solana.com"  # Use testnet
    )
    
    # Check balance
    balance = trader.get_wallet_balance()
    logger.info(f"💰 Current balance: {balance:.4f} SOL")
    
    if action == "balance":
        return
    
    # Request airdrop if balance is low
    if balance < 1.0:
        logger.info("💰 Balance too low, requesting airdrop...")
        await request_airdrop(keypair)
        balance = trader.get_wallet_balance()
        logger.info(f"💰 New balance: {balance:.4f} SOL")
    
    # Execute requested action
    if action == "build_buy":
        logger.info(f"🔧 Building buy transaction for {amount} SOL of {token_mint}")
        tx_data = await trader.build_transaction("buy", token_mint, amount)
        if tx_data:
            logger.info("✅ Buy transaction built successfully")
        else:
            logger.error("❌ Failed to build buy transaction")
    
    elif action == "build_sell":
        logger.info(f"🔧 Building sell transaction for {amount} tokens of {token_mint}")
        tx_data = await trader.build_transaction("sell", token_mint, amount)
        if tx_data:
            logger.info("✅ Sell transaction built successfully")
        else:
            logger.error("❌ Failed to build sell transaction")
    
    elif action == "buy":
        logger.info(f"🛒 Buying {amount} SOL of {token_mint}")
        success, signature, token_amount = await trader.buy_token(token_mint, amount)
        if success:
            logger.info(f"✅ Buy successful! Signature: {signature}")
            logger.info(f"🪙 Tokens received: {token_amount:,.0f}")
        else:
            logger.error("❌ Buy failed")
    
    elif action == "sell":
        logger.info(f"💸 Selling {amount:,.0f} tokens of {token_mint}")
        success, signature, sol_received = await trader.sell_token(token_mint, amount)
        if success:
            logger.info(f"✅ Sell successful! Signature: {signature}")
            logger.info(f"💰 SOL received: {sol_received:.4f}")
        else:
            logger.error("❌ Sell failed")
    
    else:
        logger.error(f"❌ Unknown action: {action}")

async def request_airdrop(keypair: Keypair, amount: float = 2.0):
    """Request SOL airdrop on testnet"""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            url = "https://api.devnet.solana.com"
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "requestAirdrop",
                "params": [
                    str(keypair.pubkey()),
                    int(amount * 1e9)
                ]
            }
            
            async with session.post(url, json=payload) as response:
                result = await response.json()
                if "result" in result:
                    logger.info(f"✅ Airdrop successful! Signature: {result['result']}")
                    await asyncio.sleep(5)  # Wait for confirmation
                else:
                    logger.error(f"❌ Airdrop failed: {result}")
                    
    except Exception as e:
        logger.error(f"❌ Error requesting airdrop: {e}")

if __name__ == "__main__":
    asyncio.run(test_specific_token()) 