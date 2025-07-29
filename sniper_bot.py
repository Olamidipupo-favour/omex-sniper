#!/usr/bin/env python3
"""
Pump.Fun Sniper Bot - Main implementation
Integrates PumpPortal monitoring with Helius RPC trading
"""

import asyncio
import logging
import base58
from typing import Optional, Callable
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from dataclasses import dataclass
from datetime import datetime

from config import config_manager, HELIUS_RPC_URL
from pump_fun_monitor import PumpPortalMonitor, TokenInfo
from pumpportal_trader import PumpPortalTrader

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more details
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Represents an active token position"""
    token_mint: str
    token_symbol: str
    token_name: str
    entry_price: float
    entry_timestamp: int
    sol_amount: float
    token_amount: float
    current_price: float = 0.0
    current_pnl: float = 0.0
    current_pnl_percent: float = 0.0
    is_active: bool = True

class SniperBot:
    """Main sniper bot class"""
    
    def __init__(self):
        self.keypair = None
        self.monitor = PumpPortalMonitor()
        self.trader = PumpPortalTrader()
        self.positions = {}
        self.monitoring_task = None
        self.position_monitoring_task = None
        self.ui_callback = None
        
        # Set up monitor callback to handle new tokens
        self.monitor.set_new_token_callback(self._handle_new_token)
        
        # Check if wallet is already configured
        self._check_wallet_on_startup()
    
    def _check_wallet_on_startup(self):
        """Check if wallet is configured and connect automatically"""
        if config_manager.has_private_key():
            try:
                private_key = config_manager.get_private_key()
                success, message = self.connect_wallet_from_key(private_key)
                if success:
                    logger.info("🔗 Wallet auto-connected from config")
                else:
                    logger.warning(f"⚠️ Failed to auto-connect wallet: {message}")
                    config_manager.update_bot_state(wallet_connected=False)
            except Exception as e:
                logger.error(f"❌ Error auto-connecting wallet: {e}")
                config_manager.update_bot_state(wallet_connected=False)
    
    def connect_wallet_from_key(self, private_key: str) -> tuple[bool, str]:
        """Connect wallet from private key string"""
        try:
            # Decode the private key
            try:
                decoded_key = base58.b58decode(private_key)
            except Exception:
                return False, "Invalid Base58 private key format"
            
            # Create keypair
            self.keypair = Keypair.from_bytes(decoded_key)
            
            # Initialize Solana client
            self.solana_client = AsyncClient(HELIUS_RPC_URL)
            
            # Get wallet info
            wallet_address = str(self.keypair.pubkey())
            
            # Update config
            config_manager.set_private_key(private_key)
            config_manager.update_bot_state(
                wallet_connected=True,
                wallet_address=wallet_address
            )
            
            # Get balance immediately using sync method
            balance = self.get_wallet_balance_sync()
            
            logger.info(f"✅ Wallet connected: {wallet_address}")
            logger.info(f"💰 Current balance: {balance:.4f} SOL")
            
            return True, f"Wallet connected successfully"
            
        except Exception as e:
            logger.error(f"❌ Error connecting wallet: {e}")
            return False, f"Error connecting wallet: {str(e)}"
    
    async def _update_wallet_balance(self):
        """Update wallet balance"""
        try:
            if self.solana_client and self.keypair:
                # Check if the current event loop is running
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_closed():
                        logger.warning("Event loop is closed, cannot update balance")
                        return
                except RuntimeError:
                    # No running event loop
                    logger.warning("No running event loop, cannot update balance")
                    return
                
                balance_response = await self.solana_client.get_balance(self.keypair.pubkey())
                if balance_response.value is not None:
                    balance_sol = balance_response.value / 10**9  # Convert lamports to SOL
                    config_manager.update_bot_state(sol_balance=balance_sol)
                    logger.info(f"💰 Wallet balance updated: {balance_sol:.4f} SOL")
                else:
                    logger.warning("Failed to get balance from RPC")
        except Exception as e:
            logger.error(f"❌ Error updating wallet balance: {e}")
            # If it's an API error, give a helpful message
            if "401" in str(e) or "Unauthorized" in str(e):
                logger.error("💡 Check your HELIUS_API_KEY in the .env file")
    
    def set_ui_callback(self, callback: Callable):
        """Set callback for UI updates"""
        self.ui_callback = callback
    
    def get_bot_status(self) -> dict:
        """Get current bot status"""
        return {
            'is_running': config_manager.config.bot_state.is_running,
            'wallet_connected': config_manager.config.bot_state.wallet_connected,
            'wallet_address': config_manager.config.bot_state.wallet_address,
            'sol_balance': config_manager.config.bot_state.sol_balance,
            'total_pnl': config_manager.config.bot_state.total_pnl,
            'active_positions': len([p for p in self.positions if p.is_active]),
            'settings': {
                'sol_per_snipe': config_manager.config.bot_settings.sol_per_snipe,
                'max_positions': config_manager.config.bot_settings.max_positions,
                'profit_target_percent': config_manager.config.bot_settings.profit_target_percent,
                'stop_loss_percent': config_manager.config.bot_settings.stop_loss_percent,
                'min_market_cap': config_manager.config.bot_settings.min_market_cap,
                'max_market_cap': config_manager.config.bot_settings.max_market_cap,
                'auto_buy': config_manager.config.bot_settings.auto_buy,
                'auto_sell': config_manager.config.bot_settings.auto_sell,
            }
        }
    
    def update_settings(self, settings: dict) -> bool:
        """Update bot settings"""
        try:
            config_manager.update_bot_settings(**settings)
            logger.info(f"⚙️ Settings updated: {settings}")
            return True
        except Exception as e:
            logger.error(f"❌ Error updating settings: {e}")
            return False
    
    async def start_monitoring(self) -> bool:
        """Start the monitoring system"""
        try:
            if not config_manager.config.bot_state.wallet_connected:
                logger.error("❌ Cannot start monitoring: No wallet connected")
                return False
            
            logger.info("🚀 Starting monitoring system...")
            config_manager.update_bot_state(is_running=True)
            
            # Update wallet balance now that we have an event loop
            await self._update_wallet_balance()
            
            # Start monitoring
            self.monitoring_task = asyncio.create_task(self.monitor.start_monitoring())
            
            # Start position monitoring
            self.position_monitoring_task = asyncio.create_task(self._monitor_positions())
            
            logger.info("✅ Monitoring system started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error starting monitoring: {e}")
            config_manager.update_bot_state(is_running=False)
            return False
    
    def stop_monitoring(self) -> bool:
        """Stop the monitoring system"""
        try:
            logger.info("🛑 Stopping monitoring system...")
            config_manager.update_bot_state(is_running=False)
            
            # Stop monitor
            try:
                self.monitor.stop_monitoring()
            except Exception as e:
                logger.warning(f"⚠️ Error stopping monitor: {e}")
            
            # Cancel tasks with error handling
            try:
                if self.monitoring_task and not self.monitoring_task.done():
                    self.monitoring_task.cancel()
            except Exception as e:
                logger.warning(f"⚠️ Error canceling monitoring task: {e}")
            
            try:
                if self.position_monitoring_task and not self.position_monitoring_task.done():
                    self.position_monitoring_task.cancel()
            except Exception as e:
                logger.warning(f"⚠️ Error canceling position monitoring task: {e}")
            
            logger.info("✅ Monitoring system stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping monitoring: {e}")
            return False
    
    async def _handle_new_token(self, token: TokenInfo):
        """Handle new token detection"""
        try:
            logger.info(f"🔍 New token detected: {token.symbol} - Market Cap: ${token.market_cap:,.0f}")
            
            # Check market cap filters
            settings = config_manager.config.bot_settings
            if token.market_cap < settings.min_market_cap or token.market_cap > settings.max_market_cap:
                logger.info(f"⏭️ Token {token.symbol} filtered out by market cap: ${token.market_cap:,.0f}")
                return
            
            # Emit to UI
            if self.ui_callback:
                self.ui_callback('new_token', {
                    'mint': token.mint,
                    'symbol': token.symbol,
                    'name': token.name,
                    'market_cap': token.market_cap,
                    'price': token.price,
                    'sol_in_pool': token.sol_in_pool,
                    'tokens_in_pool': token.tokens_in_pool,
                    'initial_buy': token.initial_buy,
                    'created_timestamp': token.created_timestamp
                })
            
            # Auto-buy logic
            if settings.auto_buy and len([p for p in self.positions if p.is_active]) < settings.max_positions:
                logger.info(f"🎯 Auto-buying {token.symbol}...")
                success = await self.buy_token(token.mint, settings.sol_per_snipe)
                if success:
                    logger.info(f"✅ Auto-buy successful for {token.symbol}")
                else:
                    logger.warning(f"⚠️ Auto-buy failed for {token.symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error handling new token: {e}")
    
    async def buy_token(self, mint: str, sol_amount: float) -> bool:
        """Buy a token"""
        try:
            if not self.keypair:
                logger.error("❌ No wallet connected")
                return False
            
            logger.info(f"💰 Buying {sol_amount} SOL worth of {mint}")
            
            # Use trader to execute buy
            success = await self.trader.buy_token(self.keypair, mint, sol_amount)
            
            if success:
                logger.info(f"✅ Buy successful for {mint}")
                # Update balance
                await self._update_wallet_balance()
                return True
            else:
                logger.error(f"❌ Buy failed for {mint}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error buying token: {e}")
            return False
    
    async def sell_token(self, mint: str) -> bool:
        """Sell a token position"""
        try:
            if not self.keypair:
                logger.error("❌ No wallet connected")
                return False
            
            logger.info(f"💸 Selling position for {mint}")
            
            # Use trader to execute sell
            success = await self.trader.sell_token(self.keypair, mint)
            
            if success:
                logger.info(f"✅ Sell successful for {mint}")
                # Update balance
                await self._update_wallet_balance()
                return True
            else:
                logger.error(f"❌ Sell failed for {mint}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error selling token: {e}")
            return False
    
    async def _monitor_positions(self):
        """Monitor active positions for profit/loss targets"""
        try:
            settings = config_manager.config.bot_settings
            
            while config_manager.config.bot_state.is_running:
                for position in self.positions:
                    if not position.is_active:
                        continue
                    
                    # Calculate current P&L
                    if position.current_price > 0:
                        pnl_percent = ((position.current_price - position.entry_price) / position.entry_price) * 100
                        position.current_pnl_percent = pnl_percent
                        
                        # Check auto-sell conditions
                        if settings.auto_sell:
                            if pnl_percent >= settings.profit_target_percent:
                                logger.info(f"🎯 Profit target reached for {position.token_symbol}: {pnl_percent:.1f}%")
                                await self.sell_token(position.token_mint)
                            elif pnl_percent <= -settings.stop_loss_percent:
                                logger.info(f"🛑 Stop loss triggered for {position.token_symbol}: {pnl_percent:.1f}%")
                                await self.sell_token(position.token_mint)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except asyncio.CancelledError:
            logger.info("📊 Position monitoring stopped")
        except Exception as e:
            logger.error(f"❌ Error monitoring positions: {e}") 

    def get_wallet_balance_sync(self) -> float:
        """Get wallet balance synchronously (for startup/status checks)"""
        try:
            if not self.keypair:
                return 0.0
            
            # Use a simple sync client for one-off balance checks
            from solana.rpc.api import Client
            sync_client = Client(HELIUS_RPC_URL)
            
            balance_response = sync_client.get_balance(self.keypair.pubkey())
            if balance_response.value is not None:
                balance_sol = balance_response.value / 10**9
                # Update the config with the fresh balance
                config_manager.update_bot_state(sol_balance=balance_sol)
                logger.info(f"💰 Balance fetched: {balance_sol:.4f} SOL")
                return balance_sol
            return 0.0
        except Exception as e:
            logger.error(f"❌ Error getting balance: {e}")
            if "401" in str(e) or "Unauthorized" in str(e):
                logger.error("💡 Check your HELIUS_API_KEY in the .env file")
            return config_manager.config.bot_state.sol_balance  # Return cached balance 