#!/usr/bin/env python3
"""
Pump.Fun Sniper Bot - Main implementation
Integrates PumpPortal monitoring with Helius RPC trading
"""

import asyncio
import logging
import json
import ssl
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from decimal import Decimal

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from config import Config
from pump_fun_monitor import PumpPortalMonitor, TokenInfo, TradeInfo
from pumpportal_trader import PumpPortalTrader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class BotSettings:
    """Bot configuration settings"""
    sol_amount_per_snipe: float = Config.DEFAULT_SOL_AMOUNT
    max_concurrent_positions: int = Config.DEFAULT_MAX_TOKENS
    profit_target_percent: float = Config.DEFAULT_PROFIT_PERCENT
    stop_loss_percent: float = Config.DEFAULT_STOP_LOSS_PERCENT
    slippage: float = Config.DEFAULT_SLIPPAGE
    
    # Filtering criteria
    min_market_cap: float = 0
    max_market_cap: float = 1000000  # $1M
    min_liquidity: float = 1000  # $1k
    auto_buy_enabled: bool = False
    auto_sell_enabled: bool = True

@dataclass
class Position:
    """Represents an active token position"""
    token_mint: str
    token_symbol: str
    token_name: str
    entry_price: float
    current_price: float
    sol_amount: float
    token_amount: float
    current_pnl: float
    current_pnl_percent: float
    is_active: bool
    entry_time: datetime
    transaction_hash: str
    target_profit_percent: float = Config.DEFAULT_PROFIT_PERCENT
    stop_loss_percent: float = Config.DEFAULT_STOP_LOSS_PERCENT

class SniperBot:
    """Main sniper bot class"""
    
    def __init__(self):
        self.settings = BotSettings()
        self.monitor = PumpPortalMonitor()
        self.trader: Optional[PumpPortalTrader] = None
        self.wallet_keypair: Optional[Keypair] = None
        self.wallet_address: Optional[str] = None
        
        # State management
        self.is_running = False
        self.positions: List[Position] = []  # List of positions
        self.total_invested = 0.0
        self.total_profit_loss = 0.0
        
        # Callbacks for UI updates
        self.callbacks: Dict[str, List[Callable]] = {
            'new_token': [],
            'position_update': [],
            'transaction': [],
            'error': []
        }
        
        # Setup monitor callbacks
        self.monitor.set_new_token_callback(self._handle_new_token)
        self.monitor.set_trade_callback(self._handle_trade_event)
    
    def add_callback(self, event_type: str, callback: Callable):
        """Add callback for events"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    def _emit_callback(self, event_type: str, data: Any):
        """Emit callback to all registered handlers"""
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in callback {event_type}: {e}")
    
    def get_wallet_address(self) -> str:
        """Get wallet address"""
        return self.wallet_address if self.wallet_address else ""
    
    def get_sol_balance(self) -> float:
        """Get SOL balance"""
        if self.trader:
            return self.trader.get_wallet_balance()
        return 0.0
    
    def set_wallet(self, private_key: str) -> bool:
        """Set wallet using private key"""
        try:
            success, address, balance = self.connect_wallet(private_key)
            return success
        except Exception as e:
            logger.error(f"Error setting wallet: {e}")
            return False
    
    def get_total_pnl(self) -> Dict[str, Any]:
        """Get total P&L data"""
        total_pnl = 0.0
        total_invested = 0.0
        active_positions = 0
        
        for position in self.positions:
            if position.is_active:
                active_positions += 1
                total_invested += position.sol_amount
                total_pnl += position.current_pnl
        
        total_pnl_percent = 0.0
        if total_invested > 0:
            total_pnl_percent = (total_pnl / total_invested) * 100
        
        return {
            'total_pnl': total_pnl,
            'total_pnl_percent': total_pnl_percent,
            'total_invested': total_invested,
            'active_positions': active_positions
        }
        
    def connect_wallet(self, private_key: str) -> tuple[bool, str, float]:
        """Connect wallet using private key"""
        try:
            # Parse private key (handle both base58 and byte array formats)
            if isinstance(private_key, str):
                if private_key.startswith('[') and private_key.endswith(']'):
                    # JSON array format
                    key_bytes = bytes(json.loads(private_key))
                else:
                    # Base58 format - decode directly without length checks
                    import base58
                    key_bytes = base58.b58decode(private_key)
            else:
                key_bytes = private_key
            
            # Create keypair using solders
            self.wallet_keypair = Keypair.from_bytes(key_bytes)
            self.wallet_address = str(self.wallet_keypair.pubkey())
            
            # Initialize trader
            self.trader = PumpPortalTrader(
                private_key=key_bytes,
                rpc_url=Config.HELIUS_RPC_URL
            )
            
            # Get wallet balance
            balance = self.trader.get_wallet_balance()
            
            logger.info(f"Wallet connected: {self.wallet_address}")
            logger.info(f"SOL Balance: {balance:.4f}")
            
            return True, self.wallet_address, balance
            
        except Exception as e:
            logger.error(f"Failed to connect wallet: {e}")
            self._emit_callback('error', f"Wallet connection failed: {e}")
            return False, "", 0.0
    
    def update_settings(self, **kwargs):
        """Update bot settings"""
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
                logger.info(f"Updated setting {key} = {value}")
    
    async def start_monitoring(self):
        """Start the monitoring process"""
        if not self.wallet_keypair or not self.trader:
            raise ValueError("Wallet not connected")
        
        logger.info("Starting Pump.Fun sniper bot...")
        self.is_running = True
        
        try:
            # Start monitoring new tokens
            await self.monitor.start_monitoring()
            
            # Start position monitoring loop
            asyncio.create_task(self._monitor_positions())
            
            logger.info("Bot started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self._emit_callback('error', f"Failed to start monitoring: {e}")
            raise
    
    def stop_monitoring(self):
        """Stop the monitoring process"""
        logger.info("Stopping bot...")
        self.is_running = False
        if hasattr(self.monitor, 'stop_monitoring'):
            asyncio.create_task(self.monitor.stop_monitoring())
        logger.info("Bot stopped")
    
    async def _handle_new_token(self, token: TokenInfo):
        """Handle new token detection"""
        try:
            logger.info(f"new token detected: {token}")
            logger.info(f"New token detected: {token.symbol} ({token.name})")
            logger.info(f"  Market Cap: ${token.market_cap:,.0f}")
            logger.info(f"  Price: ${token.price:.8f}")
            
            # Emit to UI
            self._emit_callback('new_token', token)
            
            # Check if we should auto-buy
            if self.settings.auto_buy_enabled and self._should_buy_token(token):
                logger.info(f"Auto-buying {token.symbol}...")
                await self._execute_buy(token)
                
        except Exception as e:
            logger.error(f"Error handling new token: {e}")
    
    async def _handle_trade_event(self, trade: TradeInfo):
        """Handle trade events for price updates"""
        try:
            # Update position if we own this token
            position = None
            for pos in self.positions:
                if pos.token_mint == trade.mint and pos.is_active:
                    position = pos
                    break
            
            if position:
                old_price = position.current_price
                position.current_price = trade.price
                
                # Calculate P&L
                position.current_pnl = (position.current_price - position.entry_price) * position.token_amount
                if position.entry_price > 0:
                    position.current_pnl_percent = ((position.current_price - position.entry_price) / position.entry_price) * 100
                
                # Log significant price changes
                if old_price > 0:
                    price_change = ((trade.price - old_price) / old_price) * 100
                    if abs(price_change) > 5:  # Log 5%+ changes
                        logger.info(f"{position.token_symbol} price update: ${trade.price:.6f} ({price_change:+.1f}%)")
                
                # Check auto-sell conditions
                if self.settings.auto_sell_enabled:
                    if self._should_sell_position(position):
                        logger.info(f"Auto-selling {position.token_symbol}...")
                        await self._execute_sell(position)
                
                # Notify UI
                self._emit_callback('position_update', position)
                    
        except Exception as e:
            logger.error(f"Error handling trade event: {e}")
    
    def _should_buy_token(self, token: TokenInfo) -> bool:
        """Determine if token meets buying criteria"""
        try:
            # Check if we have enough positions
            active_positions = sum(1 for pos in self.positions if pos.is_active)
            if active_positions >= self.settings.max_concurrent_positions:
                logger.debug(f"Max tokens reached ({self.settings.max_concurrent_positions})")
                return False
            
            # Check market cap range
            if not (self.settings.min_market_cap <= token.market_cap <= self.settings.max_market_cap):
                logger.debug(f"Market cap {token.market_cap} outside range")
                return False
            
            # Add more criteria here as needed
            return True
            
        except Exception as e:
            logger.error(f"Error evaluating token criteria: {e}")
            return False
    
    def _should_sell_position(self, position: Position) -> bool:
        """Determine if position should be sold"""
        try:
            # Check profit target
            if position.current_pnl_percent >= position.target_profit_percent:
                logger.info(f"Profit target reached for {position.token_symbol}: {position.current_pnl_percent:.1f}%")
                return True
            
            # Check stop loss
            if position.current_pnl_percent <= -position.stop_loss_percent:
                logger.info(f"Stop loss triggered for {position.token_symbol}: {position.current_pnl_percent:.1f}%")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating sell criteria: {e}")
            return False
    
    async def buy_token(self, token_info: TokenInfo) -> bool:
        """Buy a token (public method for web_server)"""
        try:
            await self._execute_buy(token_info)
            return True
        except Exception as e:
            logger.error(f"Error buying token: {e}")
            return False
    
    async def sell_token(self, position: Position, reason: str = "manual") -> bool:
        """Sell a token position (public method for web_server)"""
        try:
            await self._execute_sell(position, reason)
            return True
        except Exception as e:
            logger.error(f"Error selling token: {e}")
            return False
    
    async def _execute_buy(self, token: TokenInfo):
        """Execute buy order for token"""
        try:
            if not self.trader:
                raise ValueError("Trader not initialized")
            
            logger.info(f"Executing buy for {token.symbol}...")
            
            # Execute buy
            success, signature, amount_tokens = await self.trader.buy_token(
                mint_address=token.mint,
                sol_amount=self.settings.sol_amount_per_snipe,
                slippage=self.settings.slippage
            )
            
            if success and signature:
                # Create position
                position = Position(
                    token_mint=token.mint,
                    token_symbol=token.symbol,
                    token_name=token.name,
                    entry_price=token.price or 0.0,
                    current_price=token.price or 0.0,
                    sol_amount=self.settings.sol_amount_per_snipe,
                    token_amount=amount_tokens,
                    current_pnl=0.0,
                    current_pnl_percent=0.0,
                    is_active=True,
                    entry_time=datetime.now(),
                    transaction_hash=signature,
                    target_profit_percent=self.settings.profit_target_percent,
                    stop_loss_percent=self.settings.stop_loss_percent
                )
                
                self.positions.append(position)
                self.total_invested += self.settings.sol_amount_per_snipe
                
                logger.info(f"✅ Buy successful: {token.symbol}")
                logger.info(f"   Amount: {amount_tokens:,.0f} tokens")
                logger.info(f"   SOL spent: {self.settings.sol_amount_per_snipe}")
                logger.info(f"   Signature: {signature}")
                
                # Notify UI
                self._emit_callback('transaction', {
                    'type': 'buy',
                    'symbol': token.symbol,
                    'mint': token.mint,
                    'amount_sol': self.settings.sol_amount_per_snipe,
                    'amount_tokens': amount_tokens,
                    'signature': signature,
                    'timestamp': datetime.now()
                })
                
                self._emit_callback('position_update', position)
            else:
                logger.error(f"❌ Buy failed for {token.symbol}")
                
        except Exception as e:
            logger.error(f"Error executing buy: {e}")
            self._emit_callback('error', f"Buy failed: {e}")
    
    async def _execute_sell(self, position: Position, reason: str = "auto"):
        """Execute sell order for position"""
        try:
            if not self.trader:
                raise ValueError("Trader not initialized")
            
            logger.info(f"Executing sell for {position.token_symbol}...")
            
            # Execute sell
            success, signature, sol_received = await self.trader.sell_token(
                mint_address=position.token_mint,
                token_amount=position.token_amount,
                slippage=self.settings.slippage
            )
            
            if success and signature:
                # Calculate final P&L
                final_profit = sol_received - position.sol_amount
                final_profit_percent = (final_profit / position.sol_amount) * 100
                
                # Update position
                position.is_active = False
                position.current_pnl = final_profit
                position.current_pnl_percent = final_profit_percent
                position.transaction_hash = signature
                
                self.total_profit_loss += final_profit
                
                logger.info(f"✅ Sell successful: {position.token_symbol}")
                logger.info(f"   SOL received: {sol_received:.4f}")
                logger.info(f"   Profit/Loss: {final_profit:+.4f} SOL ({final_profit_percent:+.1f}%)")
                logger.info(f"   Signature: {signature}")
                
                # Notify UI
                self._emit_callback('transaction', {
                    'type': 'sell',
                    'symbol': position.token_symbol,
                    'mint': position.token_mint,
                    'amount_sol': sol_received,
                    'amount_tokens': position.token_amount,
                    'profit_loss': final_profit,
                    'profit_loss_percent': final_profit_percent,
                    'signature': signature,
                    'reason': reason,
                    'timestamp': datetime.now()
                })
                
                self._emit_callback('position_update', position)
                
            else:
                logger.error(f"❌ Sell failed for {position.token_symbol}")
                
        except Exception as e:
            logger.error(f"Error executing sell: {e}")
            self._emit_callback('error', f"Sell failed: {e}")
    
    async def manual_buy(self, mint_address: str, amount_sol: float = None) -> bool:
        """Manually buy a token"""
        try:
            if not self.trader:
                raise ValueError("Trader not initialized")
            
            amount = amount_sol or self.settings.sol_amount_per_snipe
            
            success, signature, amount_tokens = await self.trader.buy_token(
                mint_address=mint_address,
                sol_amount=amount,
                slippage=self.settings.slippage
            )
            
            if success:
                logger.info(f"Manual buy successful: {signature}")
                # Would need to get token info to create position
                
            return success
            
        except Exception as e:
            logger.error(f"Manual buy failed: {e}")
            return False
    
    async def manual_sell(self, mint_address: str) -> bool:
        """Manually sell a position"""
        try:
            position = None
            for pos in self.positions:
                if pos.token_mint == mint_address and pos.is_active:
                    position = pos
                    break
            
            if not position:
                logger.error("Position not found")
                return False
            
            await self._execute_sell(position, "manual")
            return True
            
        except Exception as e:
            logger.error(f"Manual sell failed: {e}")
            return False
    
    async def _monitor_positions(self):
        """Monitor positions for updates"""
        while self.is_running:
            try:
                # Update total P&L
                current_total = sum(pos.current_pnl for pos in self.positions if pos.is_active)
                
                if abs(current_total - self.total_profit_loss) > 0.001:  # Significant change
                    logger.debug(f"Total P&L: {current_total:+.4f} SOL")
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring positions: {e}")
                await asyncio.sleep(10)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status"""
        return {
            'is_running': self.is_running,
            'wallet_address': self.wallet_address,
            'wallet_balance': self.trader.get_wallet_balance() if self.trader else 0.0,
            'total_positions': len([pos for pos in self.positions if pos.is_active]),
            'total_invested': self.total_invested,
            'total_profit_loss': sum(pos.current_pnl for pos in self.positions if pos.is_active),
            'positions': [
                {
                    'mint': pos.token_mint,
                    'symbol': pos.token_symbol,
                    'name': pos.token_name,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'sol_amount': pos.sol_amount,
                    'token_amount': pos.token_amount,
                    'current_pnl': pos.current_pnl,
                    'current_pnl_percent': pos.current_pnl_percent,
                    'is_active': pos.is_active,
                    'entry_time': pos.entry_time.isoformat(),
                    'transaction_hash': pos.transaction_hash
                }
                for pos in self.positions
            ],
            'settings': {
                'sol_amount_per_snipe': self.settings.sol_amount_per_snipe,
                'max_concurrent_positions': self.settings.max_concurrent_positions,
                'profit_target_percent': self.settings.profit_target_percent,
                'stop_loss_percent': self.settings.stop_loss_percent,
                'slippage': self.settings.slippage,
                'auto_buy_enabled': self.settings.auto_buy_enabled,
                'auto_sell_enabled': self.settings.auto_sell_enabled,
                'min_market_cap': self.settings.min_market_cap,
                'max_market_cap': self.settings.max_market_cap
            }
        }

# Global bot instance for web server
bot_instance = None

def get_bot_instance() -> SniperBot:
    """Get or create bot instance"""
    global bot_instance
    if bot_instance is None:
        bot_instance = SniperBot()
    return bot_instance 