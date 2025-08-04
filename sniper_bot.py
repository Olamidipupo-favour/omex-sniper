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
    # New fields for buy activity monitoring
    buy_count_since_entry: int = 0  # Number of buys since we entered
    last_buy_timestamp: int = 0  # Timestamp of last buy detected
    buyers_since_entry: set = None  # Set of buyer addresses since our entry
    
    def __post_init__(self):
        if self.buyers_since_entry is None:
            self.buyers_since_entry = set()

class SniperBot:
    """Main sniper bot class"""
    
    def __init__(self):
        self.keypair = None
        self.monitor = PumpPortalMonitor()
        self.trader = PumpPortalTrader()  # Initialize without keypair initially
        self.positions = {}
        self.monitoring_task = None
        self.position_monitoring_task = None
        self.buy_activity_monitoring_task = None  # New task for monitoring buy activity
        self.ui_callback = None
        
        # Set up monitor callbacks
        self.monitor.set_new_token_callback(self._handle_new_token)
        self.monitor.set_trade_callback(self._handle_trade_activity)  # New callback for trade monitoring
        
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
            
            # Set the trader's wallet
            self.trader.set_wallet(decoded_key)
            
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
                'min_liquidity': config_manager.config.bot_settings.min_liquidity,
                'min_holders': config_manager.config.bot_settings.min_holders,
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
            
            # Start buy activity monitoring
            self.buy_activity_monitoring_task = asyncio.create_task(self._monitor_buy_activity())
            
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
            
            try:
                if self.buy_activity_monitoring_task and not self.buy_activity_monitoring_task.done():
                    self.buy_activity_monitoring_task.cancel()
            except Exception as e:
                logger.warning(f"⚠️ Error canceling buy activity monitoring task: {e}")
            
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
            
            # Check liquidity filter
            if token.liquidity < settings.min_liquidity:
                logger.info(f"⏭️ Token {token.symbol} filtered out by liquidity: {token.liquidity:.4f} SOL (min: {settings.min_liquidity} SOL)")
                return
            
            # Check holders filter
            if token.holders < settings.min_holders:
                logger.info(f"⏭️ Token {token.symbol} filtered out by holders: {token.holders} (min: {settings.min_holders})")
                return
            
            # Emit to UI for manual buying
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
                    'liquidity': token.liquidity,
                    'holders': token.holders,
                    'created_timestamp': token.created_timestamp
                })
            
            logger.info(f"📊 Token {token.symbol} displayed for manual buying")
            
            # Auto-buy logic
            if settings.auto_buy:
                await self._auto_buy_token(token)
            
        except Exception as e:
            logger.error(f"❌ Error handling new token: {e}")
    
    async def _auto_buy_token(self, token: TokenInfo):
        """Automatically buy a token when auto_buy is enabled"""
        try:
            settings = config_manager.config.bot_settings
            
            # Check if we already have a position for this token
            if token.mint in self.positions and self.positions[token.mint].is_active:
                logger.info(f"⏭️ Skipping auto-buy for {token.symbol} - already have position")
                return
            
            # Check max positions limit
            active_positions = len([p for p in self.positions.values() if p.is_active])
            if active_positions >= settings.max_positions:
                logger.info(f"⏭️ Skipping auto-buy for {token.symbol} - max positions reached ({active_positions}/{settings.max_positions})")
                return
            
            # Check wallet balance
            current_balance = self.get_wallet_balance_sync()
            if current_balance < settings.sol_per_snipe:
                error_msg = f"Insufficient balance for auto-buy: {current_balance:.4f} SOL available, {settings.sol_per_snipe} SOL needed"
                logger.warning(f"⚠️ {error_msg}")
                
                # Notify frontend about the error
                if self.ui_callback:
                    self.ui_callback('auto_buy_error', {
                        'token_symbol': token.symbol,
                        'token_mint': token.mint,
                        'error': 'insufficient_balance',
                        'message': error_msg,
                        'required_amount': settings.sol_per_snipe,
                        'available_balance': current_balance
                    })
                return
            
            logger.info(f"🎯 Auto-buying {token.symbol} with {settings.sol_per_snipe} SOL...")
            
            # Execute the buy
            success = await self.buy_token(token.mint, settings.sol_per_snipe)
            
            if success:
                logger.info(f"✅ Auto-buy successful for {token.symbol}")
                
                # Notify frontend about successful auto-buy
                if self.ui_callback:
                    self.ui_callback('auto_buy_success', {
                        'token_symbol': token.symbol,
                        'token_mint': token.mint,
                        'sol_amount': settings.sol_per_snipe,
                        'timestamp': int(datetime.now().timestamp())
                    })
            else:
                error_msg = f"Auto-buy failed for {token.symbol}"
                logger.error(f"❌ {error_msg}")
                
                # Notify frontend about the error
                if self.ui_callback:
                    self.ui_callback('auto_buy_error', {
                        'token_symbol': token.symbol,
                        'token_mint': token.mint,
                        'error': 'buy_failed',
                        'message': error_msg
                    })
                
        except Exception as e:
            error_msg = f"Error during auto-buy for {token.symbol}: {e}"
            logger.error(f"❌ {error_msg}")
            
            # Notify frontend about the error
            if self.ui_callback:
                self.ui_callback('auto_buy_error', {
                    'token_symbol': token.symbol,
                    'token_mint': token.mint,
                    'error': 'exception',
                    'message': error_msg
                })
    
    async def buy_token(self, mint: str, sol_amount: float) -> bool:
        """Buy a token manually"""
        try:
            if not self.keypair:
                logger.error("❌ No wallet connected")
                return False
            
            # Check if we already have a position for this token
            if mint in self.positions and self.positions[mint].is_active:
                logger.warning(f"⚠️ Already have an active position for {mint}")
                return False
            
            # Check max positions limit
            active_positions = len([p for p in self.positions.values() if p.is_active])
            settings = config_manager.config.bot_settings
            if active_positions >= settings.max_positions:
                logger.warning(f"⚠️ Max positions reached ({active_positions}/{settings.max_positions})")
                return False
            
            logger.info(f"💰 Buying {sol_amount} SOL worth of {mint}")
            
            # Use trader to execute buy
            success, signature, token_amount = await self.trader.buy_token(mint, sol_amount)
            
            if success:
                logger.info(f"✅ Buy successful for {mint}")
                
                # Create position record
                position = Position(
                    token_mint=mint,
                    token_symbol="",  # Will be updated when we get token info
                    token_name="",    # Will be updated when we get token info
                    entry_price=0.0,  # Will be updated when we get current price
                    entry_timestamp=int(datetime.now().timestamp()),
                    sol_amount=sol_amount,
                    token_amount=token_amount,  # Use the actual token amount received
                    buy_count_since_entry=0,
                    last_buy_timestamp=int(datetime.now().timestamp()),
                    buyers_since_entry=set()
                )
                
                self.positions[mint] = position
                
                # Subscribe to trade monitoring for this token
                await self.monitor.subscribe_token_trades([mint])
                
                # Update balance
                await self._update_wallet_balance()
                
                # Emit position update to UI
                if self.ui_callback:
                    self.ui_callback('position_update', {
                        'mint': mint,
                        'action': 'buy',
                        'sol_amount': sol_amount,
                        'timestamp': position.entry_timestamp
                    })
                
                logger.info(f"📊 Position created and monitoring started for {mint}")
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
            
            if mint not in self.positions or not self.positions[mint].is_active:
                logger.warning(f"⚠️ No active position found for {mint}")
                return False
            
            position = self.positions[mint]
            logger.info(f"💸 Selling position for {position.token_symbol or mint}")
            
            # Use trader to execute sell
            success, signature, sol_received = await self.trader.sell_token(mint, position.token_amount)
            
            if success:
                logger.info(f"✅ Sell successful for {position.token_symbol or mint}")
                
                # Calculate P&L based on SOL received vs SOL invested
                if sol_received > 0:
                    pnl_sol = sol_received - position.sol_amount
                    pnl_percent = (pnl_sol / position.sol_amount) * 100
                    
                    position.current_pnl = pnl_sol
                    position.current_pnl_percent = pnl_percent
                    
                    logger.info(f"💰 P&L: {pnl_percent:.2f}% ({pnl_sol:.4f} SOL)")
                
                # Close position
                position.is_active = False
                
                # Update total P&L
                total_pnl = config_manager.config.bot_state.total_pnl + position.current_pnl
                config_manager.update_bot_state(total_pnl=total_pnl)
                
                # Update balance
                await self._update_wallet_balance()
                
                # Emit position update to UI
                if self.ui_callback:
                    self.ui_callback('position_update', {
                        'mint': mint,
                        'action': 'sell',
                        'pnl': position.current_pnl,
                        'pnl_percent': position.current_pnl_percent,
                        'buy_count': position.buy_count_since_entry,
                        'timestamp': int(datetime.now().timestamp())
                    })
                
                return True
            else:
                logger.error(f"❌ Sell failed for {position.token_symbol or mint}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error selling token: {e}")
            return False
    
    async def _monitor_positions(self):
        """Monitor active positions for profit/loss targets"""
        try:
            settings = config_manager.config.bot_settings
            
            while config_manager.config.bot_state.is_running:
                for mint, position in self.positions.items():
                    if not position.is_active:
                        continue
                    
                    # Calculate current P&L if we have price data
                    if position.current_price > 0 and position.entry_price > 0:
                        pnl_percent = ((position.current_price - position.entry_price) / position.entry_price) * 100
                        position.current_pnl_percent = pnl_percent
                        
                        # Check auto-sell conditions (profit target or stop loss)
                        if settings.auto_sell:
                            if pnl_percent >= settings.profit_target_percent:
                                logger.info(f"🎯 Profit target reached for {position.token_symbol or mint}: {pnl_percent:.1f}%")
                                await self.sell_token(mint)
                            elif pnl_percent <= -settings.stop_loss_percent:
                                logger.info(f"🛑 Stop loss triggered for {position.token_symbol or mint}: {pnl_percent:.1f}%")
                                await self.sell_token(mint)
                    
                    # Check buy count condition (3 additional buyers)
                    if position.buy_count_since_entry >= 3:
                        logger.info(f"🎯 3 additional buyers reached for {position.token_symbol or mint} - Selling!")
                        await self.sell_token(mint)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except asyncio.CancelledError:
            logger.info("📊 Position monitoring stopped")
        except Exception as e:
            logger.error(f"❌ Error monitoring positions: {e}")

    async def _handle_trade_activity(self, trade_info):
        """Handle trade activity for monitoring buy counts"""
        try:
            mint = trade_info.mint
            
            # Check if we have an active position for this token
            if mint not in self.positions or not self.positions[mint].is_active:
                return
            
            position = self.positions[mint]
            
            # Only process buy transactions
            if not trade_info.is_buy:
                return
            
            # Skip our own buys
            if trade_info.trader == str(self.keypair.pubkey()):
                return
            
            # Check if this is a new buyer (not seen before)
            if trade_info.trader not in position.buyers_since_entry:
                position.buyers_since_entry.add(trade_info.trader)
                position.buy_count_since_entry += 1
                position.last_buy_timestamp = trade_info.timestamp
                
                logger.info(f"🆕 New buyer detected for {position.token_symbol or mint}: {trade_info.trader}")
                logger.info(f"📊 Buy count since entry: {position.buy_count_since_entry}")
                
                # Check if we should sell (3 additional buyers)
                if position.buy_count_since_entry >= 3:
                    logger.info(f"🎯 3 additional buyers detected for {position.token_symbol or mint} - Selling!")
                    await self.sell_token(mint)
                    return
            
            # Update position with current price
            position.current_price = trade_info.price
            
            # Emit position update to UI
            if self.ui_callback:
                self.ui_callback('position_update', {
                    'mint': mint,
                    'buy_count': position.buy_count_since_entry,
                    'current_price': trade_info.price,
                    'timestamp': trade_info.timestamp
                })
                
        except Exception as e:
            logger.error(f"❌ Error handling trade activity: {e}")

    async def _monitor_buy_activity(self):
        """Monitor buy activity for active positions"""
        try:
            logger.info("📊 Starting buy activity monitoring...")
            
            while config_manager.config.bot_state.is_running:
                # Check each active position
                for mint, position in self.positions.items():
                    if not position.is_active:
                        continue
                    
                    # Log current buy count for debugging
                    if position.buy_count_since_entry > 0:
                        logger.debug(f"📊 {position.token_symbol or mint}: {position.buy_count_since_entry}/3 buyers")
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
        except asyncio.CancelledError:
            logger.info("📊 Buy activity monitoring stopped")
        except Exception as e:
            logger.error(f"❌ Error monitoring buy activity: {e}")

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