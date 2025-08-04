#!/usr/bin/env python3
"""
Test PumpPortalTrader - Test buy/sell functionality with testnet
This script allows you to test the trading functionality safely
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
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestTrader:
    """Test class for PumpPortalTrader functionality"""
    
    def __init__(self):
        # Mainnet configuration (PumpPortal only works with mainnet)
        self.mainnet_rpc_url = "https://api.mainnet-beta.solana.com"
        self.pumpportal_url = "https://pumpportal.fun/api"
        
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
            logger.info("💡 Save this private key to TEST_PRIVATE_KEY env var for consistent testing")
        
        # Initialize trader with testnet configuration
        self.trader = PumpPortalTrader(
            private_key=base58.b58decode(self.test_private_key),  # Pass decoded bytes
            rpc_url=self.mainnet_rpc_url
        )
        
        return True
    
    async def get_testnet_balance(self) -> float:
        """Get SOL balance on testnet"""
        try:
            balance = self.trader.get_wallet_balance()
            logger.info(f"💰 Testnet balance: {balance:.4f} SOL")
            return balance
        except Exception as e:
            logger.error(f"❌ Error getting balance: {e}")
            return 0.0
    
    async def request_testnet_airdrop(self, amount: float = 2.0):
        """Request SOL airdrop on testnet"""
        try:
            logger.info(f"🪂 Requesting {amount} SOL airdrop...")
            
            # Use aiohttp to request airdrop
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"{self.mainnet_rpc_url}"
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "requestAirdrop",
                    "params": [
                        str(self.keypair.pubkey()),
                        int(amount * 1e9)  # Convert to lamports
                    ]
                }
                
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    if "result" in result:
                        signature = result["result"]
                        logger.info(f"✅ Airdrop successful! Signature: {signature}")
                        
                        # Wait for confirmation
                        await asyncio.sleep(5)
                        await self.get_testnet_balance()
                        return True
                    else:
                        logger.error(f"❌ Airdrop failed: {result}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Error requesting airdrop: {e}")
            return False
    
    async def test_build_transaction(self, action: str, mint: str, amount: float):
        """Test building a transaction"""
        try:
            logger.info(f"🔧 Testing build_transaction: {action} {amount} SOL of {mint}")
            
            tx_data = await self.trader.build_transaction(action, mint, amount, slippage=5.0)
            
            if tx_data:
                logger.info(f"✅ Transaction built successfully")
                logger.info(f"📦 Transaction data type: {type(tx_data)}")
                if "transaction" in tx_data:
                    logger.info(f"📦 Transaction length: {len(str(tx_data['transaction']))}")
                return True
            else:
                logger.error(f"❌ Failed to build transaction")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing build_transaction: {e}")
            return False
    
    async def test_buy_token(self, mint: str, amount: float):
        """Test buying a token"""
        try:
            logger.info(f"🛒 Testing buy_token: {amount} SOL of {mint}")
            
            success, signature, token_amount = await self.trader.buy_token(mint, amount)
            
            if success:
                logger.info(f"✅ Buy test successful!")
                logger.info(f"📝 Signature: {signature}")
                logger.info(f"🪙 Tokens received: {token_amount:,.0f}")
                return True, signature
            else:
                logger.error(f"❌ Buy test failed")
                return False, None
                
        except Exception as e:
            logger.error(f"❌ Error testing buy_token: {e}")
            return False, None
    
    async def test_sell_token(self, mint: str, token_amount: float):
        """Test selling a token"""
        try:
            logger.info(f"💸 Testing sell_token: {token_amount:,.0f} tokens of {mint}")
            
            success, signature, sol_received = await self.trader.sell_token(mint, token_amount)
            
            if success:
                logger.info(f"✅ Sell test successful!")
                logger.info(f"📝 Signature: {signature}")
                logger.info(f"💰 SOL received: {sol_received:.4f}")
                return True, signature
            else:
                logger.error(f"❌ Sell test failed")
                return False, None
                
        except Exception as e:
            logger.error(f"❌ Error testing sell_token: {e}")
            return False, None
    
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
    
    async def run_comprehensive_test(self):
        """Run comprehensive test of all trader functionality"""
        logger.info("🚀 Starting comprehensive PumpPortalTrader test...")
        
        # Setup
        if not self.setup_test_wallet():
            logger.error("❌ Failed to setup test wallet")
            return
        
        # Get token mint from user
        if not self.test_token_mint:
            print("\n🔍 You need to provide a real Pump.Fun token mint address")
            print("Run 'python3 get_test_token.py' to find recent tokens")
            self.test_token_mint = input("Enter token mint address: ").strip()
            
            if not self.test_token_mint:
                logger.error("❌ No token mint provided")
                return
        
        # Check initial balance
        initial_balance = await self.get_testnet_balance()
        
        # Check if we have enough SOL (no airdrop on mainnet)
        if initial_balance < 0.1:
            logger.error(f"❌ Insufficient balance: {initial_balance:.4f} SOL")
            logger.error("💡 You need at least 0.1 SOL on mainnet for testing")
            return
        
        # Test 1: Build buy transaction
        logger.info("\n" + "="*50)
        logger.info("TEST 1: Building buy transaction")
        logger.info("="*50)
        await self.test_build_transaction("buy", self.test_token_mint, 0.01)  # Small amount
        
        # Test 2: Build sell transaction
        logger.info("\n" + "="*50)
        logger.info("TEST 2: Building sell transaction")
        logger.info("="*50)
        await self.test_build_transaction("sell", self.test_token_mint, 1000)  # 1000 tokens
        
        # Test 3: Get token accounts
        logger.info("\n" + "="*50)
        logger.info("TEST 3: Getting token accounts")
        logger.info("="*50)
        await self.test_token_accounts()
        
        # Test 4: Actual buy (if you want to test real transactions)
        logger.info("\n" + "="*50)
        logger.info("TEST 4: Testing actual buy transaction")
        logger.info("="*50)
        logger.info("⚠️  This will execute a real transaction on mainnet!")
        logger.info("⚠️  Make sure you have enough SOL and want to spend it!")
        
        # Ask user if they want to proceed
        proceed = input("Do you want to proceed with real buy transaction? (y/N): ").strip().lower()
        
        if proceed == 'y':
            buy_success, buy_sig = await self.test_buy_token(self.test_token_mint, 0.01)
            if buy_success:
                logger.info("✅ Buy test completed successfully!")
                
                # Wait a bit before testing sell
                await asyncio.sleep(5)
                
                # Test sell
                sell_success, sell_sig = await self.test_sell_token(self.test_token_mint, 1000)
                if sell_success:
                    logger.info("✅ Sell test completed successfully!")
        else:
            logger.info("⏭️ Skipping real transaction test")
        
        logger.info("\n" + "="*50)
        logger.info("🎉 Test completed!")
        logger.info("="*50)
        
        # Final balance check
        final_balance = await self.get_testnet_balance()
        logger.info(f"💰 Final balance: {final_balance:.4f} SOL")
        if initial_balance > 0:
            change = final_balance - initial_balance
            logger.info(f"📊 Balance change: {change:+.4f} SOL")

async def main():
    """Main test function"""
    test_trader = TestTrader()
    await test_trader.run_comprehensive_test()

if __name__ == "__main__":
    print("🧪 PumpPortalTrader Test Suite")
    print("=" * 50)
    print("This script tests the PumpPortalTrader functionality")
    print("Make sure you have sufficient SOL on testnet")
    print("=" * 50)
    
    # Run the test
    asyncio.run(main()) 