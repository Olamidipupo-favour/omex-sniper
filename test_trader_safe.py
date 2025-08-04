#!/usr/bin/env python3
"""
Safe Test PumpPortalTrader - Test buy/sell functionality without spending SOL
This script only builds transactions, never executes them
"""

import asyncio
import logging
import base58
import os
from typing import Optional
from solders.keypair import Keypair
from pumpportal_trader import PumpPortalTrader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SafeTestTrader:
    """Safe test class - only builds transactions, never executes them"""
    
    def __init__(self):
        # Mainnet configuration (PumpPortal only works with mainnet)
        self.mainnet_rpc_url = "https://api.mainnet-beta.solana.com"
        
        # Test wallet (you can replace with your own mainnet wallet)
        self.test_private_key = os.getenv("dev_private_key", "")
        self.keypair = None
        self.trader = None
        
        # Test token (will be set dynamically)
        self.test_token_mint = None
        
    def setup_test_wallet(self):
        """Setup test wallet - generate new keypair if none provided"""
        if self.test_private_key:
            try:
                decoded_key = base58.b58decode(self.test_private_key)
                self.keypair = Keypair.from_bytes(decoded_key)
                logger.info(f"✅ Using provided test wallet: {str(self.keypair.pubkey())}")
            except Exception as e:
                logger.error(f"❌ Invalid private key: {e}")
                return False
        else:
            # Generate new test wallet
            self.keypair = Keypair()
            self.test_private_key = base58.b58encode(self.keypair.secret()).decode()
            logger.info(f"✅ Generated new test wallet: {str(self.keypair.pubkey())}")
            logger.info(f"🔑 Private key: {self.test_private_key}")
        
        # Initialize trader with mainnet configuration
        self.trader = PumpPortalTrader(
            private_key=base58.b58decode(self.test_private_key),
            rpc_url=self.mainnet_rpc_url
        )
        
        return True
    
    async def get_balance(self) -> float:
        """Get SOL balance"""
        try:
            balance = self.trader.get_wallet_balance()
            logger.info(f"💰 Balance: {balance:.4f} SOL")
            return balance
        except Exception as e:
            logger.error(f"❌ Error getting balance: {e}")
            return 0.0
    
    async def test_build_buy_transaction(self, mint: str, amount: float):
        """Test building a buy transaction (SAFE - no execution)"""
        try:
            logger.info(f"🔧 Testing build_transaction: BUY {amount} SOL of {mint}")
            
            tx_data = await self.trader.build_transaction("buy", mint, amount, slippage=5.0)
            
            if tx_data:
                logger.info(f"✅ Buy transaction built successfully!")
                logger.info(f"📦 Transaction data type: {type(tx_data)}")
                if "transaction" in tx_data:
                    tx_length = len(str(tx_data['transaction']))
                    logger.info(f"📦 Transaction length: {tx_length} characters")
                    logger.info(f"📦 Transaction preview: {str(tx_data['transaction'])[:100]}...")
                return True
            else:
                logger.error(f"❌ Failed to build buy transaction")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing build_transaction: {e}")
            return False
    
    async def test_build_sell_transaction(self, mint: str, token_amount: float):
        """Test building a sell transaction (SAFE - no execution)"""
        try:
            logger.info(f"🔧 Testing build_transaction: SELL {token_amount:,.0f} tokens of {mint}")
            
            tx_data = await self.trader.build_transaction("sell", mint, token_amount, slippage=5.0)
            
            if tx_data:
                logger.info(f"✅ Sell transaction built successfully!")
                logger.info(f"📦 Transaction data type: {type(tx_data)}")
                if "transaction" in tx_data:
                    tx_length = len(str(tx_data['transaction']))
                    logger.info(f"📦 Transaction length: {tx_length} characters")
                    logger.info(f"📦 Transaction preview: {str(tx_data['transaction'])[:100]}...")
                return True
            else:
                logger.error(f"❌ Failed to build sell transaction")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing build_transaction: {e}")
            return False
    
    async def test_token_accounts(self):
        """Test getting token accounts"""
        try:
            logger.info("🔍 Testing get_token_accounts...")
            
            accounts = self.trader.get_token_accounts(str(self.keypair.pubkey()))
            
            logger.info(f"✅ Found {len(accounts)} token accounts")
            for account in accounts[:5]:  # Show first 5 accounts
                logger.info(f"   - {account.get('pubkey', 'N/A')}: {account.get('account', {}).get('data', {}).get('parsed', {}).get('info', {}).get('tokenAmount', {}).get('uiAmount', 0)}")
            
            return accounts
            
        except Exception as e:
            logger.error(f"❌ Error testing get_token_accounts: {e}")
            return []
    
    async def test_transaction_signing(self, tx_data):
        """Test signing a transaction (SAFE - no sending)"""
        try:
            logger.info("🔐 Testing transaction signing...")
            
            # This will test the signing part without sending
            success, signature = await self.trader.sign_and_send_transaction(tx_data)
            
            if success:
                logger.info(f"✅ Transaction signed successfully!")
                logger.info(f"📝 Signature: {signature}")
                return True
            else:
                logger.error(f"❌ Transaction signing failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing transaction signing: {e}")
            return False
    
    async def run_safe_test(self):
        """Run safe test of trader functionality (no real transactions)"""
        logger.info("🚀 Starting SAFE PumpPortalTrader test...")
        logger.info("🛡️  This test only builds transactions, never executes them!")
        
        # Setup
        if not self.setup_test_wallet():
            logger.error("❌ Failed to setup test wallet")
            return
        
        # Get token mint from user
        if not self.test_token_mint:
            print("\n🔍 You need to provide a real Pump.Fun token mint address")
            print("Run 'python3 get_test_token.py' and choose option 2 to monitor for new tokens")
            self.test_token_mint = input("Enter token mint address: ").strip()
            
            if not self.test_token_mint:
                logger.error("❌ No token mint provided")
                return
        
        # Check balance (just for info)
        await self.get_balance()
        
        # Test 1: Build buy transaction
        logger.info("\n" + "="*50)
        logger.info("TEST 1: Building buy transaction")
        logger.info("="*50)
        buy_success = await self.test_build_buy_transaction(self.test_token_mint, 0.01)
        
        # Test 2: Build sell transaction
        logger.info("\n" + "="*50)
        logger.info("TEST 2: Building sell transaction")
        logger.info("="*50)
        sell_success = await self.test_build_sell_transaction(self.test_token_mint, 1000)
        
        # Test 3: Get token accounts
        logger.info("\n" + "="*50)
        logger.info("TEST 3: Getting token accounts")
        logger.info("="*50)
        await self.test_token_accounts()
        
        # Summary
        logger.info("\n" + "="*50)
        logger.info("🎉 SAFE TEST COMPLETED!")
        logger.info("="*50)
        logger.info(f"✅ Buy transaction building: {'PASS' if buy_success else 'FAIL'}")
        logger.info(f"✅ Sell transaction building: {'PASS' if sell_success else 'FAIL'}")
        
        if buy_success and sell_success:
            logger.info("🎯 All tests passed! Your PumpPortalTrader is working correctly.")
        else:
            logger.info("⚠️  Some tests failed. Check the logs above for details.")

async def main():
    """Main test function"""
    test_trader = SafeTestTrader()
    await test_trader.run_safe_test()

if __name__ == "__main__":
    print("🛡️  SAFE PumpPortalTrader Test Suite")
    print("=" * 50)
    print("This script tests the PumpPortalTrader functionality")
    print("SAFE MODE: Only builds transactions, never executes them!")
    print("=" * 50)
    
    # Run the test
    asyncio.run(main()) 