#!/usr/bin/env python3
"""
Pump.Fun Sniper Bot - Main implementation
Integrates PumpPortal monitoring with Helius RPC trading
"""

import asyncio
import logging
import base58
from typing import Optional, Callable, Dict, List, Any
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from dataclasses import dataclass
from datetime import datetime
import time

from config import config_manager, HELIUS_RPC_URL
from pump_fun_monitor import PumpFunMonitor, TokenInfo
from pumpportal_trader import PumpPortalTrader
from token_filter_service import TokenFilterService
from helius_api import HeliusAPI

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
    # Current P&L snapshot (used by UI and total P&L calculations)
    current_pnl: float = 0.0
    current_pnl_percent: float = 0.0
    pnl_sol: float = 0.0
    pnl_percent: float = 0.0
    last_price_update: int = 0
    is_active: bool = True
    # New fields for buy activity monitoring
    buy_count_since_entry: int = 0  # Number of buys since we entered
    last_buy_timestamp: int = 0  # Timestamp of last buy detected
    buyers_since_entry: set = None  # Set of buyer addresses since our entry
    # Time-based sell tracking
    entry_time: int = 0  # Entry time in seconds since epoch
    
    def __post_init__(self):
        if self.buyers_since_entry is None:
            self.buyers_since_entry = set()

class SniperBot:
    """Main sniper bot class"""
    
    def __init__(self):
        """Initialize the sniper bot"""
        self.keypair = None
        self.trader = PumpPortalTrader()
        self.monitor = PumpFunMonitor()
        self.token_filter = TokenFilterService(helius_rpc_url=HELIUS_RPC_URL)
        self.positions: Dict[str, Position] = {}
        self.ui_callback: Optional[Callable] = None
        self.buy_activity_monitoring_task = None
        # Ensure trade history always exists before any later initialization may fail
        self.trade_history: List[Dict[str, Any]] = []
        # Serialize auto-buys to respect max_positions and avoid race conditions
        self._buy_lock: asyncio.Lock = asyncio.Lock()
        # New: track concurrent auto-buys and a queue when at capacity
        self._autobuy_state_lock: asyncio.Lock = asyncio.Lock()
        self._buys_in_progress: set[str] = set()
        self._autobuy_queue: List[TokenInfo] = []
        # New: track concurrent sells and a queue when at capacity
        self._sell_state_lock: asyncio.Lock = asyncio.Lock()
        self._sells_in_progress: set[str] = set()
        self._sell_queue: List[str] = []

        # Add cancellation flag for historical token loading
        self._historical_loading_cancelled = False
        self._historical_loading_task = None
        
        # Initialize Helius API
        self.helius_api = HeliusAPI()
        
        # Store trade history for analysis (initialized in __init__)
        
        # Check for existing wallet on startup
        self._check_wallet_on_startup()
        
        # Set up trade monitoring callback
        self.monitor.set_trade_callback(self._handle_pumpportal_trade)
        
        # Set up new token callback
        self.monitor.set_new_token_callback(self._handle_new_token)
        
        # Set up price update callback
        self.monitor.set_price_update_callback(self._handle_price_update)
        
        # Set up loading status callback for quick mode
        self.loading_status_callback = None

    async def _start_autobuy_task(self, token: TokenInfo):
        """Run a single auto-buy and ensure slot release + queue draining."""
        settings = config_manager.config.bot_settings
        try:
            await self.buy_token(token.mint, settings.sol_per_snipe, token.symbol, token.name)
        except Exception as e:
            logger.error(f"❌ Auto-buy task failed for {getattr(token, 'symbol', token.mint)}: {e}")
        finally:
            async with self._autobuy_state_lock:
                self._buys_in_progress.discard(token.mint)
                # Drain queue if capacity available
                active_positions = len([p for p in self.positions.values() if p.is_active])
                concurrent_buys = len(self._buys_in_progress)
                capacity = max(0, settings.max_positions - active_positions - concurrent_buys)
                if capacity > 0 and self._autobuy_queue:
                    next_token = self._autobuy_queue.pop(0)
                    self._buys_in_progress.add(next_token.mint)
                    asyncio.create_task(self._start_autobuy_task(next_token))
    
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
            
            # Note: Account monitoring will be set up when monitoring starts
            # (Cannot await here as this is not an async function)
            logger.info(f"📡 Account monitoring will be set up when bot starts: {wallet_address}")
            
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
    
    def set_loading_status_callback(self, callback: Callable):
        """Set callback for loading status updates (quick mode)"""
        self.loading_status_callback = callback
    
    def get_bot_status(self) -> dict:
        """Get current bot status"""
        return {
            'is_running': config_manager.config.bot_state.is_running,
            'has_private_key': config_manager.has_private_key(),
            'wallet_connected': config_manager.config.bot_state.wallet_connected,
            'wallet_address': config_manager.config.bot_state.wallet_address,
            'sol_balance': config_manager.config.bot_state.sol_balance,
            'total_pnl': config_manager.config.bot_state.total_pnl,
            # Iterate over position objects, not dict keys
            'active_positions': sum(1 for p in self.positions.values() if p.is_active),
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
                'sell_strategy': config_manager.config.bot_settings.sell_strategy,
                'sell_after_buys': config_manager.config.bot_settings.sell_after_buys,
                'sell_after_seconds': getattr(config_manager.config.bot_settings, 'sell_after_seconds', 18000),
                'token_age_filter': config_manager.config.bot_settings.token_age_filter,
                'custom_days': config_manager.config.bot_settings.custom_days,
                'include_pump_tokens': config_manager.config.bot_settings.include_pump_tokens,
                'transaction_type': config_manager.config.bot_settings.transaction_type,
                'priority_fee': config_manager.config.bot_settings.priority_fee,
                'historical_batch_size': config_manager.config.bot_settings.historical_batch_size,
                'quick_mode': config_manager.config.bot_settings.quick_mode,
                'quick_mode_batch_size': config_manager.config.bot_settings.quick_mode_batch_size,
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

    def delete_position(self, mint: str) -> bool:
        """Remove a position from memory/state without selling on-chain."""
        try:
            if not mint:
                return False
            pos = self.positions.pop(mint, None)
            if pos is None:
                # try alternative key field
                to_delete = None
                for k, v in self.positions.items():
                    if getattr(v, 'token_mint', None) == mint:
                        to_delete = k
                        break
                if to_delete:
                    pos = self.positions.pop(to_delete, None)
            if pos:
                logger.info(f"🗑️ Deleted position for {pos.token_symbol or mint}")
                # Notify UI
                if self.ui_callback:
                    self.ui_callback('position_update', {
                        'action': 'deleted',
                        'mint': mint
                    })
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Error deleting position {mint}: {e}")
            return False

    def get_positions_snapshot(self) -> List[Dict[str, Any]]:
        """Return a serializable snapshot of current in-memory positions."""
        try:
            snapshot: List[Dict[str, Any]] = []
            for mint, pos in self.positions.items():
                # Only include active positions
                if not getattr(pos, 'is_active', True):
                    continue
                snapshot.append({
                    'mint': mint,
                    'token_mint': getattr(pos, 'token_mint', mint),
                    'token_symbol': getattr(pos, 'token_symbol', 'Unknown'),
                    'token_name': getattr(pos, 'token_name', 'Unknown'),
                    'entry_price': getattr(pos, 'entry_price', 0.0),
                    'current_price': getattr(pos, 'current_price', 0.0),
                    'token_amount': getattr(pos, 'token_amount', 0.0),
                    'sol_amount': getattr(pos, 'sol_amount', 0.0),
                    'current_pnl': getattr(pos, 'current_pnl', getattr(pos, 'pnl_sol', 0.0) or 0.0),
                    'current_pnl_percent': getattr(pos, 'current_pnl_percent', getattr(pos, 'pnl_percent', 0.0) or 0.0),
                    'is_active': getattr(pos, 'is_active', True),
                    'entry_timestamp': getattr(pos, 'entry_timestamp', getattr(pos, 'entry_time', 0) or 0),
                    'signature': getattr(pos, 'signature', None)
                })
            return snapshot
        except Exception as e:
            logger.error(f"❌ Error building positions snapshot: {e}")
            return []
    
    async def _load_historical_tokens(self):
        """Load historical tokens based on age filter settings"""
        try:
            settings = config_manager.config.bot_settings
            
            # Only load historical tokens if not using "new_only" filter
            if settings.token_age_filter == "new_only":
                return
            
            logger.info(f"📚 Loading historical tokens for filter: {settings.token_age_filter}")
            
            # Get age threshold
            age_threshold_days = self.token_filter._get_age_threshold_days(
                settings.token_age_filter, 
                settings.custom_days
            )
            
            logger.info(f"📅 Age threshold: {age_threshold_days} days")
            
            # Check if quick mode is enabled
            if settings.quick_mode:
                await self._load_historical_tokens_quick_mode(age_threshold_days)
            else:
                await self._load_historical_tokens_normal_mode(age_threshold_days)
            
        except Exception as e:
            logger.error(f"❌ Error loading historical tokens: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
    async def _load_historical_tokens_normal_mode(self, age_threshold_days: int):
        """Load historical tokens using normal mode (original logic)"""
        try:
            settings = config_manager.config.bot_settings
            
            # Get historical tokens using hybrid approach with batch processing
            # Create a batch callback to process tokens immediately as they're fetched
            async def process_token_batch(token_batch: List[Dict[str, Any]]):
                """Process a batch of tokens immediately for frontend updates"""
                # Check if historical loading has been cancelled
                if self._historical_loading_cancelled:
                    logger.info("🛑 Historical token loading cancelled, skipping batch processing")
                    return 0
                
                logger.info(f"📤 Processing batch of {len(token_batch)} tokens immediately")
                
                # Process each token in the batch concurrently
                batch_tasks = []
                for token_data in token_batch:
                    # Check cancellation before processing each token
                    if self._historical_loading_cancelled:
                        logger.info("🛑 Historical token loading cancelled, stopping batch processing")
                        return 0
                    
                    task = self._process_historical_token(token_data)
                    batch_tasks.append(task)
                
                # Wait for all tokens in the batch to complete processing
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Count successful processing
                batch_processed = sum(1 for result in batch_results if result is True)
                logger.info(f"✅ Batch processed: {batch_processed}/{len(token_batch)} tokens successfully")
                
                return batch_processed
            
            # Get historical tokens with batch processing
            historical_tokens = await self.token_filter.get_hybrid_recent_tokens(
                days=age_threshold_days,
                include_pump_only=True,  # Get all tokens, not just Pump.fun ones
                batch_callback=process_token_batch,
                batch_size=getattr(settings, 'historical_batch_size', 10),
                cancellation_check=lambda: self._historical_loading_cancelled
            )
            
            # Check if loading was cancelled during the process
            if self._historical_loading_cancelled:
                logger.info("🛑 Historical token loading cancelled, stopping processing")
                return
            
            logger.info(f"📊 Loaded {len(historical_tokens)} historical tokens")
            logger.info(f"📋 Historical tokens before processing: {historical_tokens}")
            
            # Tokens are now processed in batches as they're fetched via the callback
            # The historical_tokens list contains all tokens that were processed
            logger.info(f"✅ Historical token loading completed. Total tokens processed: {len(historical_tokens)}")
            
        except Exception as e:
            logger.error(f"❌ Error loading historical tokens in normal mode: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
    async def _load_historical_tokens_quick_mode(self, age_threshold_days: int):
        """Load historical tokens using quick mode (get all first, then filter)"""
        try:
            settings = config_manager.config.bot_settings
            
            # Notify UI that we're loading tokens
            if self.loading_status_callback:
                self.loading_status_callback('loading_status', {
                    'status': 'loading_tokens',
                    'message': 'Loading historical tokens...',
                    'timestamp': int(time.time())
                })
            
            logger.info("🚀 Quick mode: Loading all historical tokens first...")
            
            # Get all historical tokens without processing (just fetch them)
            all_tokens = await self.token_filter.get_hybrid_recent_tokens(
                days=age_threshold_days,
                include_pump_only=True,
                batch_callback=None,  # No batch processing in quick mode
                batch_size=getattr(settings, 'quick_mode_batch_size', 100),
                cancellation_check=lambda: self._historical_loading_cancelled
            )
            
            if self._historical_loading_cancelled:
                logger.info("🛑 Historical token loading cancelled in quick mode")
                return
            
            logger.info(f"📊 Quick mode: Loaded {len(all_tokens)} total tokens")
            
            # Notify UI that we're done loading, now filtering
            if self.loading_status_callback:
                self.loading_status_callback('loading_status', {
                    'status': 'filtering_tokens',
                    'message': f'Done loading {len(all_tokens)} tokens. Now filtering...',
                    'timestamp': int(time.time())
                })
            
            # Apply market cap and basic filters first (without holder checks)
            filtered_tokens = []
            for token_data in all_tokens:
                if self._historical_loading_cancelled:
                    break
                
                # Basic market cap filter
                market_cap = token_data.get('usd_market_cap', 0)
                if market_cap < settings.min_market_cap or market_cap > settings.max_market_cap:
                    continue
                
                # Basic liquidity filter (if available)
                liquidity = token_data.get('liquidity', 0)
                if liquidity < settings.min_liquidity:
                    continue
                
                filtered_tokens.append(token_data)
            
            logger.info(f"🔍 Quick mode: After basic filtering: {len(filtered_tokens)} tokens")
            
            # Notify UI that filtering is complete, now processing
            if self.loading_status_callback:
                self.loading_status_callback('loading_status', {
                    'status': 'processing_tokens',
                    'message': f'Filtered to {len(filtered_tokens)} tokens. Now processing...',
                    'timestamp': int(time.time())
                })
            
            # Now process the filtered tokens in large batches
            batch_size = getattr(settings, 'quick_mode_batch_size', 100)
            total_processed = 0
            
            for i in range(0, len(filtered_tokens), batch_size):
                if self._historical_loading_cancelled:
                    break
                
                batch = filtered_tokens[i:i + batch_size]
                logger.info(f"📤 Quick mode: Processing batch {i//batch_size + 1} ({len(batch)} tokens)")
                
                # Process batch concurrently
                batch_tasks = []
                for token_data in batch:
                    if self._historical_loading_cancelled:
                        break
                    
                    task = self._process_historical_token_quick_mode(token_data)
                    batch_tasks.append(task)
                
                if batch_tasks:
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    batch_processed = sum(1 for result in batch_results if result is True)
                    total_processed += batch_processed
                    
                    logger.info(f"✅ Quick mode: Batch {i//batch_size + 1} processed: {batch_processed}/{len(batch)} tokens")
                    
                    # Update UI progress
                    if self.loading_status_callback:
                        progress = min(100, (total_processed / len(filtered_tokens)) * 100)
                        self.loading_status_callback('loading_status', {
                            'status': 'processing_progress',
                            'message': f'Processed {total_processed}/{len(filtered_tokens)} tokens ({progress:.1f}%)',
                            'progress': progress,
                            'timestamp': int(time.time())
                        })
            
            # Final status update
            if self.loading_status_callback:
                self.loading_status_callback('loading_status', {
                    'status': 'completed',
                    'message': f'✅ Quick mode completed! Processed {total_processed} tokens',
                    'total_processed': total_processed,
                    'timestamp': int(time.time())
                })
            
            logger.info(f"🚀 Quick mode: Historical token loading completed. Total processed: {total_processed}")
            
        except Exception as e:
            logger.error(f"❌ Error loading historical tokens in quick mode: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            
            # Notify UI of error
            if self.loading_status_callback:
                self.loading_status_callback('loading_status', {
                    'status': 'error',
                    'message': f'Error in quick mode: {str(e)}',
                    'timestamp': int(time.time())
                })
    
    async def _process_historical_token_quick_mode(self, token_data: Dict[str, Any]) -> bool:
        """Process a single historical token in quick mode (with holder check)"""
        try:
            # Check if historical loading has been cancelled
            if self._historical_loading_cancelled:
                logger.info("🛑 Historical token loading cancelled, skipping token processing")
                return False
            
            # Convert to TokenInfo format
            token = TokenInfo(
                mint=token_data.get('mint', ''),
                symbol=token_data.get('symbol', ''),
                name=token_data.get('name', ''),
                description=token_data.get('description', ''),
                image=token_data.get('image_uri', ''),
                created_timestamp=token_data.get('created_timestamp', int(time.time())),
                usd_market_cap=token_data.get('usd_market_cap', 0),
                market_cap=token_data.get('market_cap', 0),
                price=token_data.get('price', 0),
                creator=token_data.get('creator', ''),
                twitter=token_data.get('twitter', ''),
                telegram=token_data.get('telegram', ''),
                website=token_data.get('website', ''),
                nsfw=token_data.get('nsfw', False),
                sol_in_pool=token_data.get('sol_in_pool', 0),
                tokens_in_pool=token_data.get('tokens_in_pool', 0),
                initial_buy=token_data.get('initial_buy', 0),
                sol_amount=token_data.get('sol_amount', 0),
                new_token_balance=token_data.get('new_token_balance', 0),
                trader_public_key=token_data.get('trader_public_key', ''),
                tx_type=token_data.get('tx_type', ''),
                signature=token_data.get('signature', ''),
                pool=token_data.get('pool', ''),
                liquidity=token_data.get('liquidity', 0),
                holders=token_data.get('holders', 0)
            )
            
            # Now check holders (this is the key difference in quick mode)
            settings = config_manager.config.bot_settings
            
            # Update holders count using Pump.fun API
            passes_filter = await self.monitor.update_token_holders_and_filter(
                token, 
                min_liquidity=settings.min_liquidity, 
                min_holders=settings.min_holders
            )
            
            if not passes_filter:
                logger.info(f"⏭️ Quick mode: Token {token.symbol} filtered out by liquidity/holders criteria")
                return False
            
            # Enrich token with age information
            token_dict = {
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
            }
            
            enriched_token = await self.token_filter.enrich_token_with_age_info(
                token_dict, 
                include_pump_check=False
            )
            
            # Emit to UI for manual buying
            if self.ui_callback:
                logger.info(f"📡 Quick mode: Emitting token to frontend: {token.symbol} ({token.mint})")
                self.ui_callback('new_token', enriched_token)
                logger.info(f"📡 Quick mode: Token emitted successfully: {enriched_token}")
            
            logger.info(f"📊 Quick mode: Token {token.symbol} processed and displayed for manual buying")
            
            # Auto-buy logic for quick mode
            if settings.auto_buy:
                logger.info(f"🤖 Quick mode: Auto-buy enabled for {token.symbol}, triggering auto-buy...")
                await self._auto_buy_token(token)
            else:
                logger.info(f"⏭️ Quick mode: Auto-buy disabled for {token.symbol}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing historical token in quick mode: {e}")
            return False
    
    async def _process_historical_token(self, token_data: Dict[str, Any]) -> bool:
        """Process a single historical token (extracted from batch processing)"""
        try:
            # Check if historical loading has been cancelled
            if self._historical_loading_cancelled:
                logger.info("🛑 Historical token loading cancelled, skipping token processing")
                return False
            
            # Convert to TokenInfo format
            token = TokenInfo(
                mint=token_data.get('mint', ''),
                symbol=token_data.get('symbol', ''),
                name=token_data.get('name', ''),
                description=token_data.get('description', ''),
                image=token_data.get('image_uri', ''),
                created_timestamp=token_data.get('created_timestamp', int(time.time())),
                usd_market_cap=token_data.get('usd_market_cap', 0),
                market_cap=token_data.get('market_cap', 0),
                price=token_data.get('price', 0),
                creator=token_data.get('creator', ''),
                twitter=token_data.get('twitter', ''),
                telegram=token_data.get('telegram', ''),
                website=token_data.get('website', ''),
                nsfw=token_data.get('nsfw', False),
                sol_in_pool=token_data.get('sol_in_pool', 0),
                tokens_in_pool=token_data.get('tokens_in_pool', 0),
                initial_buy=token_data.get('initial_buy', 0),
                sol_amount=token_data.get('sol_amount', 0),
                new_token_balance=token_data.get('new_token_balance', 0),
                trader_public_key=token_data.get('trader_public_key', ''),
                tx_type=token_data.get('tx_type', ''),
                signature=token_data.get('signature', ''),
                pool=token_data.get('pool', ''),
                liquidity=token_data.get('liquidity', 0),
                holders=token_data.get('holders', 0)
            )
            
            logger.info(f"🔄 Processing historical token: {token.symbol} ({token.mint})")
            
            # Process the token through normal flow (this includes holder updates)
            await self._handle_new_token(token)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing historical token {token_data.get('mint', 'unknown')}: {e}")
            return False
    
    async def start_monitoring(self) -> bool:
        """Start monitoring for new tokens and trading opportunities"""
        try:
            logger.info("🚀 Starting sniper bot monitoring...")
            
            # Update bot state
            config_manager.update_bot_state(is_running=True)
            
            # Get current bot settings
            settings = config_manager.config.bot_settings
            token_age_filter = settings.token_age_filter
            
            logger.info(f"🔍 Token age filter: {token_age_filter}")
            
            # Load historical tokens if using historical filter (in background)
            if token_age_filter != "new_only":
                logger.info(f"📚 Loading historical tokens for {token_age_filter} filter (background)...")
                # Immediately connect WebSocket and subscribe to account trades (historical mode)
                try:
                    initial_subscriptions = {}
                    if self.keypair:
                        wallet_address = str(self.keypair.pubkey())
                        initial_subscriptions['account_addresses'] = [wallet_address]
                        logger.info(f"📡 Historical mode: will subscribe to account trades for {wallet_address}")
                    # Start monitor in background to avoid blocking
                    if initial_subscriptions:
                        self._pumpportal_monitor_task = asyncio.create_task(self.monitor.start_monitoring(initial_subscriptions))
                        logger.info("🧵 Launched PumpPortal monitoring task (account trades only) for historical mode")
                except Exception as e:
                    logger.error(f"❌ Failed to start PumpPortal monitoring in historical branch: {e}")
                # Reset cancellation flag
                self._historical_loading_cancelled = False
                # Store the task for potential cancellation and DO NOT await
                self._historical_loading_task = asyncio.create_task(self._load_historical_tokens())
                # Wait for it to complete (but it can be cancelled)
                try:
                    await self._historical_loading_task
                    logger.info("✅ Historical tokens loaded")
                except asyncio.CancelledError:
                    logger.info("🛑 Historical token loading was cancelled")
                except Exception as e:
                    logger.error(f"❌ Error in historical token loading: {e}")
            
            # Start PumpPortal WebSocket monitoring
            await self._start_pumpportal_monitoring()
            
            # Start the main monitoring loop
            monitoring_task = asyncio.create_task(self._monitor_positions())
            
            # Start buy activity monitoring
            self.buy_activity_monitoring_task = asyncio.create_task(self._monitor_buy_activity())
            
            # Skip starting global background price monitoring
            logger.info("⏭️ Skipping global background price monitoring (prices update only on our trades)")
            
            logger.info("✅ Monitoring started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error starting monitoring: {e}")
            config_manager.update_bot_state(is_running=False)
            return False

    async def _start_pumpportal_monitoring(self):
        """Start PumpPortal WebSocket monitoring using existing pump_fun_monitor.py"""
        try:
            logger.info("🔌 Starting PumpPortal WebSocket monitoring...")
            
            # Get current bot settings
            settings = config_manager.config.bot_settings
            token_age_filter = settings.token_age_filter
            
            # Prepare initial subscriptions
            initial_subscriptions = {}
            
            # Only subscribe to new tokens if the filter allows it
            if token_age_filter == "new_only":
                initial_subscriptions['subscribe_new_tokens'] = True
                logger.info("📡 Will subscribe to newly created tokens (newly_created_only filter)")
            else:
                # For historical filters (last_3_days, last_7_days, custom_days), don't subscribe to new tokens
                logger.info(f"📡 Will NOT subscribe to new tokens (using {token_age_filter} filter)")
                logger.info("📡 Will use historical data instead of WebSocket for new tokens")
            
            # Always add account trades subscription if wallet is connected
            if self.keypair:
                wallet_address = str(self.keypair.pubkey())
                initial_subscriptions['account_addresses'] = [wallet_address]
                logger.info(f"📡 Will subscribe to account trades: {wallet_address}")
            
            # Start the existing PumpFunMonitor with initial subscriptions
            await self.monitor.start_monitoring(initial_subscriptions)
            
            logger.info("✅ PumpPortal monitoring started using existing pump_fun_monitor.py")
            logger.info(f"🔍 Token age filter: {token_age_filter}")
            logger.info(f"🔍 Subscriptions: {initial_subscriptions}")
            
        except Exception as e:
            logger.error(f"❌ Error starting PumpPortal monitoring: {e}")
    
    async def _unsubscribe_from_all_monitoring(self):
        """Unsubscribe from specific monitoring but keep account trades active"""
        try:
            # Unsubscribe from new token creation
            await self.monitor.unsubscribe_new_tokens()
            logger.info("📤 Unsubscribed from new token creation")
            
            # Unsubscribe from token trades for all active positions
            active_tokens = [mint for mint, pos in self.positions.items() if pos.is_active]
            if active_tokens:
                await self.monitor.unsubscribe_token_trades(active_tokens)
                logger.info(f"📤 Unsubscribed from token trades: {active_tokens}")
            
            # Keep account trades subscription active (don't unsubscribe)
            logger.info("📡 Keeping account trades subscription active")
                
        except Exception as e:
            logger.error(f"❌ Error unsubscribing from monitoring: {e}")
    
    def stop_monitoring(self) -> bool:
        """Stop the monitoring system but keep WebSocket connection alive"""
        try:
            logger.info("🛑 Stopping monitoring system (keeping WebSocket alive)...")
            config_manager.update_bot_state(is_running=False)
            
            # Cancel historical token loading
            try:
                if self._historical_loading_task and not self._historical_loading_task.done():
                    logger.info("🛑 Cancelling historical token loading task...")
                    self._historical_loading_task.cancel()
                    self._historical_loading_cancelled = True
                    logger.info("✅ Historical token loading task cancelled")
            except Exception as e:
                logger.warning(f"⚠️ Error cancelling historical token loading task: {e}")
            
            # Unsubscribe from specific tokens/accounts but don't close WebSocket
            try:
                # Use synchronous unsubscription method
                self.monitor.unsubscribe_from_monitoring_sync()
            except Exception as e:
                logger.warning(f"⚠️ Error unsubscribing from monitoring: {e}")
            
            # Stop monitor (but keep WebSocket alive)
            try:
                self.monitor.stop_monitoring()
            except Exception as e:
                logger.warning(f"⚠️ Error stopping monitor: {e}")
            
            # Cancel tasks with error handling
            try:
                if self.buy_activity_monitoring_task and not self.buy_activity_monitoring_task.done():
                    self.buy_activity_monitoring_task.cancel()
            except Exception as e:
                logger.warning(f"⚠️ Error canceling buy activity monitoring task: {e}")
            
            # Cancel all price monitoring tasks
            try:
                if hasattr(self, 'price_monitoring_tasks'):
                    for mint, task in self.price_monitoring_tasks.items():
                        if not task.done():
                            task.cancel()
                            logger.info(f"🛑 Cancelled price monitoring for {mint}")
                    self.price_monitoring_tasks.clear()
            except Exception as e:
                logger.warning(f"⚠️ Error canceling price monitoring tasks: {e}")
            
            logger.info("✅ Monitoring system stopped (WebSocket kept alive)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping monitoring: {e}")
            return False
    
    def shutdown(self) -> bool:
        """Completely shutdown the bot and close WebSocket connection"""
        try:
            logger.info("🔌 Shutting down bot completely...")
            
            # First stop monitoring
            self.stop_monitoring()
            
            # Then close WebSocket connection
            try:
                self.monitor.close_websocket_connection()
            except Exception as e:
                logger.warning(f"⚠️ Error closing WebSocket connection: {e}")
            
            logger.info("✅ Bot shutdown complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error shutting down bot: {e}")
            return False
    
    async def _handle_new_token(self, token: TokenInfo):
        """Handle new token detection"""
        try:
            # Check if monitoring is currently running
            if not config_manager.config.bot_state.is_running:
                logger.info(f"⏭️ Skipping token {token.symbol} - monitoring is stopped")
                return
            
            settings = config_manager.config.bot_settings
            
            # Update holders count and apply filtering using Pump.fun API
            passes_filter = await self.monitor.update_token_holders_and_filter(
                token, 
                min_liquidity=settings.min_liquidity, 
                min_holders=settings.min_holders
            )
            
            if not passes_filter:
                logger.info(f"⏭️ Token {token.symbol} filtered out by liquidity/holders criteria")
                return
            
            # Enrich token with age information (no Pump.fun checking)
            token_dict = {
                'mint': token.mint,
                'symbol': token.symbol,
                'name': token.name,
                'market_cap': token.market_cap,
                'price': token.price,
                'sol_in_pool': token.sol_in_pool,
                'tokens_in_pool': token.tokens_in_pool,
                'initial_buy': token.initial_buy,
                'liquidity': token.liquidity,
                'holders': token.holders,  # Now updated with real count from API
                'created_timestamp': token.created_timestamp
            }
            
            # Enrich with age info (no Pump.fun checking)
            enriched_token = await self.token_filter.enrich_token_with_age_info(
                token_dict, 
                include_pump_check=False
            )
            
            # Apply age filter
            if settings.token_age_filter != "new_only":
                # For non-newly created tokens, check if they meet the age criteria
                age_threshold_days = self.token_filter._get_age_threshold_days(
                    settings.token_age_filter, 
                    settings.custom_days
                )
                
                if not self.token_filter._is_token_within_age_limit(
                    token.created_timestamp, 
                    age_threshold_days
                ):
                    logger.info(f"⏭️ Token {token.symbol} filtered out by age: {enriched_token.get('age_days', 0):.1f} days old")
                    return
            else:
                # For newly created tokens, ensure they are actually new (0-1 day old)
                age_days = enriched_token.get('age_days', 0)
                if age_days > 1:
                    logger.info(f"⏭️ Token {token.symbol} filtered out - not newly created: {age_days:.1f} days old")
                    return
            
            # Check market cap filters
            if token.market_cap < settings.min_market_cap or token.market_cap > settings.max_market_cap:
                logger.info(f"⏭️ Token {token.symbol} filtered out by market cap: ${token.market_cap:,.0f}")
                return
            
            # Log filter description
            filter_desc = self.token_filter.get_filter_description(
                settings.token_age_filter, 
                settings.custom_days
            )
            logger.info(f"🔍 Token {token.symbol} passed filters: {filter_desc}")
            logger.info(f"📊 Token details: liquidity={token.liquidity:.2f} SOL, holders={token.holders}, market_cap=${token.market_cap:,.0f}")
            
            # Emit to UI for manual buying
            if self.ui_callback:
                logger.info(f"📡 Emitting token to frontend: {token.symbol} ({token.mint})")
                self.ui_callback('new_token', enriched_token)
                logger.info(f"📡 Token emitted successfully: {enriched_token}")
            else:
                logger.warning(f"⚠️ No UI callback set, cannot emit token: {token.symbol}")
            
            logger.info(f"📊 Token {token.symbol} displayed for manual buying (Age: {enriched_token.get('age_days', 0):.1f} days)")
            
            # Auto-buy logic
            if settings.auto_buy:
                await self._auto_buy_token(token)
            
        except Exception as e:
            logger.error(f"❌ Error handling new token: {e}")
    
    async def _auto_buy_token(self, token: TokenInfo):
        """Automatically buy a token when auto_buy is enabled"""
        try:
            settings = config_manager.config.bot_settings
            
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
            
            # Allow concurrent auto-buys up to max_positions
            async with self._autobuy_state_lock:
                # Already have a position? skip
                if token.mint in self.positions and self.positions[token.mint].is_active:
                    logger.info(f"⏭️ Skipping auto-buy for {token.symbol} - already have position")
                    return
                # Compute available slots
                active_positions = len([p for p in self.positions.values() if p.is_active])
                concurrent_buys = len(self._buys_in_progress)
                capacity = max(0, settings.max_positions - active_positions - concurrent_buys)
                if capacity <= 0:
                    # Queue only when at capacity
                    logger.info(f"⏸️ Queuing auto-buy for {token.symbol} - at capacity ({active_positions}+{concurrent_buys}/{settings.max_positions})")
                    self._autobuy_queue.append(token)
                    return
                # Reserve a slot for this buy
                self._buys_in_progress.add(token.mint)

            logger.info(f"🎯 Auto-buying {token.symbol} with {settings.sol_per_snipe} SOL...")
            # Run via helper that guarantees slot release and queue drain, even on error
            asyncio.create_task(self._start_autobuy_task(token))
            success = True
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
    
    async def buy_token(self, mint: str, sol_amount: float, token_symbol: str = "Unknown", token_name: str = "Unknown") -> bool:
        """Buy a specific token"""
        try:
            if not self.keypair:
                logger.error("❌ No wallet connected")
                return False
            
            # Check if trader has wallet set
            if not self.trader.keypair:
                logger.error("❌ Trader wallet not set")
                return False
            
            # Get priority fee from settings
            settings = config_manager.config.bot_settings
            priority_fee = settings.priority_fee
            
            logger.info(f"🛒 Attempting to buy {mint} ({token_symbol}) for {sol_amount} SOL")
            logger.info(f"🔑 Trader wallet: {str(self.trader.keypair.pubkey())}")
            logger.info(f"💰 Priority fee: {priority_fee} SOL")
            
            # Execute the buy
            result = await self.trader.buy_token(mint, sol_amount, priority_fee=priority_fee)
            logger.info(f"🔍 Trader buy_token result: {result} (type: {type(result)})")
            
            if result is None:
                logger.error(f"❌ Trader buy_token returned None for {mint}")
                return False
            
            success, signature, token_amount = result
            
            if success:
                logger.info(f"✅ Buy successful! Signature: {signature}")
                
                # Create position tracking with token metadata (only if not already present)
                created_new_position = False
                if mint in self.positions and self.positions[mint].is_active:
                    existing = self.positions[mint]
                    logger.info(f"🔄 Existing position before update: {existing}")
                    logger.info(f"token symbol before update: {token_symbol}")
                    logger.info(f"token name before update: {token_name}")
                    # Update only missing metadata; do NOT overwrite existing entry_price/token_amount
                    if (not existing.token_symbol) or existing.token_symbol == "Unknown":
                        existing.token_symbol = token_symbol
                    if (not existing.token_name) or existing.token_name == "Unknown":
                        existing.token_name = token_name
                    if existing.sol_amount <= 0:
                        existing.sol_amount = sol_amount
                    logger.info(f"token symbol after update: {token_symbol}")
                    logger.info(f"token name after update: {token_name}")
                    logger.info(f"🔄 Existing position after update: {existing}")
                    logger.info(f"↩️ Position for {mint} already exists; updated metadata without overwriting core fields")
                else:
                    position = Position(
                        token_mint=mint,
                        token_symbol=token_symbol,  # Use provided token metadata
                        token_name=token_name,      # Use provided token metadata
                        entry_price=0.0,            # Will be updated from our own trade data
                        entry_timestamp=int(time.time()),
                        sol_amount=sol_amount,
                        token_amount=0.0,           # Will be updated from our own trade data
                        entry_time=int(time.time()) # Entry time for time-based sell strategy
                    )
                    self.positions[mint] = position
                    created_new_position = True
                    logger.info(f"📊 Position created for {mint} ({token_symbol}) | SOL Amount: {sol_amount}")
                    logger.info(f"🔄 Waiting for WebSocket data to update entry price and token amount...")
                    # Use safe repr to avoid referencing undefined var when reusing existing
                    logger.info(f"📊 Position created: {position}")
                    logger.info(f"📊 Placeholder position created for {mint}; awaiting stream update")
                
                # Record the transaction (without token amount for now)
                await self._record_transaction("buy", mint, sol_amount, signature, 0.0)
                
                # Update PumpPortal monitoring to include this token
                await self._update_pumpportal_monitoring()
                
                # Do not start background price monitoring anymore
                logger.info(f"⏭️ Skipping background price monitoring for {mint} (price will update only on our buys/sells)")
                
                # Send initial position creation to UI immediately
                if created_new_position and self.ui_callback:
                    # Convert signature to string for UI
                    signature_str = str(signature) if signature else ""
                    
                    self.ui_callback('position_update', {
                        'action': 'buy',
                        'mint': mint,
                        'sol_amount': sol_amount,
                        'token_amount': 0.0,  # Will be updated from WebSocket
                        'signature': signature_str,
                        'entry_price': 0.0,  # Will be updated from WebSocket
                        'token_symbol': token_symbol,  # Use provided token metadata
                        'token_name': token_name       # Use provided token metadata
                    })
                    logger.info(f"📱 Sent initial position creation to UI for {mint} ({token_symbol})")
                else:
                    if not created_new_position:
                        logger.info(f"📱 Skipped initial 'buy' UI emission for {mint} (position already existed)")
                    else:
                        logger.warning(f"⚠️ No UI callback set for position update")
                
                return True
            else:
                logger.error(f"❌ Buy failed for {mint}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error buying token {mint}: {e}")
            return False

    async def _update_pumpportal_monitoring(self):
        """Update PumpPortal WebSocket monitoring when positions change"""
        try:
            # Get current tokens to monitor
            tokens_to_monitor = list(self.positions.keys())
            
            # Get our wallet address for account monitoring
            wallet_address = str(self.keypair.pubkey()) if self.keypair else None
            
            # Ensure WebSocket is connected; if not, start it with appropriate initial subscriptions
            token_age_filter = config_manager.config.bot_settings.token_age_filter
            if not self.monitor.is_websocket_connected():
                initial_subs = {
                    # Only subscribe to new tokens for 'new_only'; skip for historical filters
                    'subscribe_new_tokens': token_age_filter == "new_only",
                    'account_addresses': [wallet_address] if wallet_address else [],
                    'token_mints': tokens_to_monitor
                }
                logger.info("🔌 WebSocket not connected. Starting monitor with initial subscriptions for trades only...")
                await self.monitor.start_monitoring(initial_subs)
            else:
                # Subscribe to our own account trades (for entry price and metadata)
                # if wallet_address:
                #     await self.monitor.add_account_trades_subscription([wallet_address])
                #     logger.info(f"📡 Added account trades subscription: {wallet_address}")
                
                # Subscribe to token trades (for monitoring other trades and buy-count condition)
                if tokens_to_monitor:
                    await self.monitor.add_token_trades_subscription(tokens_to_monitor)
                    logger.info(f"📡 Added token trades subscription for {len(tokens_to_monitor)} tokens: {tokens_to_monitor}")
                
        except Exception as e:
            logger.error(f"❌ Error updating PumpPortal monitoring: {e}")

    async def _start_price_monitoring_for_token(self, mint: str):
        """Deprecated: background price monitoring is disabled."""
        logger.info(f"⏭️ _start_price_monitoring_for_token called for {mint}, but background price monitoring is disabled.")
        return
    
    async def _stop_price_monitoring_for_token(self, mint: str):
        """Stop price monitoring for a specific token"""
        try:
            if hasattr(self, 'price_monitoring_tasks') and mint in self.price_monitoring_tasks:
                task = self.price_monitoring_tasks[mint]
                if not task.done():
                    task.cancel()
                    logger.info(f"🛑 Stopped price monitoring for {mint}")
                del self.price_monitoring_tasks[mint]
        except Exception as e:
            logger.error(f"❌ Error stopping price monitoring for {mint}: {e}")
    
    async def sell_token(self, mint: str) -> bool:
        """Sell a token position with queue management for same mint operations"""
        try:
            logger.info(f"💸 sell_token called for {mint}")
            if not self.keypair:
                logger.error("❌ No wallet connected")
                return False
            
            if mint not in self.positions or not self.positions[mint].is_active:
                logger.warning(f"⚠️ No active position found for {mint}")
                return False
            
            async with self._sell_state_lock:
                # Check if there's already a sell in progress for this mint
                if mint in self._sells_in_progress:
                    logger.info(f"🔄 Sell already in progress for {mint}, adding to queue")
                    self._sell_queue.append(mint)
                    return True
                
                # No sells in progress for this mint, start this one
                self._sells_in_progress.add(mint)
                asyncio.create_task(self._start_sell_task(mint))
                logger.info(f"🚀 Starting sell task for {mint}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error in sell_token queue management: {e}")
            return False
    
    async def _monitor_positions(self):
        """Monitor active positions for profit/loss targets"""
        try:
            logger.info(f"🔍 _monitor_positions called")
            settings = config_manager.config.bot_settings
            
            # while config_manager.config.bot_state.is_running:
            while True:
                logger.info(f"🔍 _monitor_positions loop called")
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
                    
                    # Check sell conditions based on strategy
                    if settings.auto_sell:
                        should_sell = False
                        sell_reason = ""
                        
                        if settings.sell_strategy == "buy_count":
                            # Sell after specified number of buys
                            if position.buy_count_since_entry >= settings.sell_after_buys:
                                should_sell = True
                                sell_reason = f"{settings.sell_after_buys}-buy rule"
                        elif settings.sell_strategy == "time_based":
                            # Sell after specified number of seconds
                            current_time = int(time.time())
                            seconds_since_entry = current_time - position.entry_time
                            target_seconds = getattr(settings, 'sell_after_seconds', 18000)
                            if seconds_since_entry >= target_seconds:
                                should_sell = True
                                sell_reason = f"{target_seconds}-second rule"
                        
                        if should_sell:
                            logger.info(f"🎯 {sell_reason} reached for {position.token_symbol or mint} - Selling!")
                            await self.sell_token(mint)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except asyncio.CancelledError:
            logger.info("📊 Position monitoring stopped")
        except Exception as e:
            logger.error(f"❌ Error monitoring positions: {e}")

    async def _handle_trade_activity(self, trade_info):
        """Handle incoming trade activity for active positions"""
        try:
            mint = trade_info.get('mint', '')
            buyer = trade_info.get('buyer', '')
            tx_type = trade_info.get('txType', '')
            
            # Only process buy transactions for tokens we have positions in
            if mint in self.positions and self.positions[mint].is_active and tx_type == 'buy':
                position = self.positions[mint]
                
                # Skip if this is our own buy
                if buyer == str(self.keypair.pubkey()):
                    return
                
                # Track unique buyers since our entry
                if buyer not in position.buyers_since_entry:
                    position.buyers_since_entry.add(buyer)
                    position.buy_count_since_entry += 1
                    position.last_buy_timestamp = int(time.time())
                    
                    logger.info(f"📈 New buyer detected for {mint}: {buyer} (Total buyers since entry: {position.buy_count_since_entry})")
                    
                    # Check if we should sell based on strategy
                    settings = config_manager.config.bot_settings
                    if settings.auto_sell:
                        if settings.sell_strategy == "buy_count":
                            if position.buy_count_since_entry >= settings.sell_after_buys:
                                logger.info(f"🎯 {settings.sell_after_buys}-buy sell condition met for {mint}, executing sell...")
                                await self._execute_sell(mint, f"{settings.sell_after_buys}-buy rule")
                        elif settings.sell_strategy == "time_based":
                            seconds_since_entry = int(time.time()) - position.entry_time
                            target_seconds = getattr(settings, 'sell_after_seconds', 18000)
                            if seconds_since_entry >= target_seconds:
                                logger.info(f"⏰ {target_seconds}-second time-based sell condition met for {mint}, executing sell...")
                                await self._execute_sell(mint, f"{target_seconds}-second rule")

                        # Also enforce TP/SL immediately on trade activity
                        if position.entry_price > 0 and position.current_price > 0:
                            pnl_percent = ((position.current_price - position.entry_price) / position.entry_price) * 100
                            if pnl_percent >= settings.profit_target_percent:
                                logger.info(f"🎯 Profit target reached on trade activity for {mint}: {pnl_percent:.1f}%")
                                await self._execute_sell(mint, f"profit target {settings.profit_target_percent}%")
                            elif pnl_percent <= -settings.stop_loss_percent:
                                logger.info(f"🛑 Stop loss triggered on trade activity for {mint}: {pnl_percent:.1f}%")
                                await self._execute_sell(mint, f"stop loss {settings.stop_loss_percent}%")
                        
        except Exception as e:
            logger.error(f"❌ Error handling trade activity: {e}")
    
    def _handle_price_update(self, mint: str, price_sol: float, price_usd: float):
        """Handle price updates from websocket"""
        try:
            logger.info(f"💰 Price update received for {mint}: {price_sol:.12f} SOL (${price_usd:.8f})")
            
            # Check if we have a position for this token
            if mint in self.positions and self.positions[mint].is_active:
                position = self.positions[mint]
                
                # Update position with latest price
                position.current_price = price_sol
                position.last_price_update = int(time.time())
                
                # Calculate P&L if we have entry price
                if position.entry_price > 0:
                    pnl_sol = (price_sol - position.entry_price) * position.token_amount
                    pnl_percent = ((price_sol - position.entry_price) / position.entry_price) * 100 if position.entry_price > 0 else 0
                    
                    position.pnl_sol = pnl_sol
                    position.pnl_percent = pnl_percent
                    
                    logger.info(f"💰 P&L Update for {mint}:")
                    logger.info(f"   Entry: {position.entry_price:.12f} SOL, Current: {price_sol:.12f} SOL")
                    logger.info(f"   P&L: {pnl_sol:.6f} SOL ({pnl_percent:+.2f}%)")

                    # Enforce TP/SL immediately on price update
                    settings = config_manager.config.bot_settings
                    if settings.auto_sell:
                        if pnl_percent >= settings.profit_target_percent:
                            logger.info(f"🎯 Profit target reached on price update for {mint}: {pnl_percent:.1f}%")
                            try:
                                loop = asyncio.get_running_loop()
                                asyncio.create_task(self.sell_token(mint))
                            except RuntimeError:
                                asyncio.run(self.sell_token(mint))
                        elif pnl_percent <= -settings.stop_loss_percent:
                            logger.info(f"🛑 Stop loss triggered on price update for {mint}: {pnl_percent:.1f}%")
                            try:
                                loop = asyncio.get_running_loop()
                                asyncio.create_task(self.sell_token(mint))
                            except RuntimeError:
                                asyncio.run(self.sell_token(mint))
                    
                    # Update UI with price and P&L update (always include position metadata as backup)
                    if self.ui_callback:
                        self.ui_callback('position_update', {
                            'action': 'price_update',
                            'mint': mint,
                            'current_price': price_sol,
                            'current_price_usd': price_usd,
                            'pnl_sol': pnl_sol,
                            'pnl_percent': pnl_percent,
                            'timestamp': int(time.time()),
                            # BACKUP: Always include position metadata in case frontend missed metadata_update
                            'entry_price': position.entry_price,
                            'token_amount': position.token_amount,
                            'token_symbol': position.token_symbol,
                            'token_name': position.token_name,
                            'sol_amount': position.sol_amount
                        })
                        logger.info(f"📱 Sent price update to UI for {mint} (with backup metadata: entry_price={position.entry_price}, token_amount={position.token_amount})")
                else:
                    logger.info(f"💰 Price updated for {mint} but no entry price available yet")
            else:
                logger.info(f"💰 Price update for {mint} but no active position found")
                
        except Exception as e:
            logger.error(f"❌ Error handling price update: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")

    async def _handle_pumpportal_trade(self, trade_info):
        """Handle trade events from PumpPortal WebSocket"""
        try:
            logger.info(f"🔄 _handle_pumpportal_trade called with trade_info: {trade_info}")
            logger.info(f"📊 Trade mint: {trade_info.mint}")
            logger.info(f"📊 Trade trader: {trade_info.trader}")
            logger.info(f"📊 Trade is_buy: {trade_info.is_buy}")
            logger.info(f"📊 Trade amount: {trade_info.amount}")
            logger.info(f"📊 Trade token_amount: {trade_info.token_amount}")
            
            # Convert TradeInfo to dictionary for compatibility with existing code
            trade_data = {
                'mint': trade_info.mint,
                'txType': 'buy' if trade_info.is_buy else 'sell',
                'traderPublicKey': trade_info.trader,
                'solAmount': trade_info.amount,
                'tokenAmount': trade_info.token_amount,  # Use the actual token amount from TradeInfo
                'signature': trade_info.signature,
                'timestamp': trade_info.timestamp,
                'marketCapSol': trade_info.market_cap / 100.0,  # Convert USD to SOL (approximate)
                'price': trade_info.price
            }
            
            # Store trade in history (guard against missing attribute)
            if not hasattr(self, 'trade_history') or self.trade_history is None:
                self.trade_history = []
            self.trade_history.append(trade_data)
            
            # Keep only last 1000 trades to prevent memory issues
            if len(self.trade_history) > 1000:
                self.trade_history = self.trade_history[-1000:]
            
            mint = trade_data['mint']
            tx_type = trade_data['txType']
            trader = trade_data['traderPublicKey']
            
            logger.info(f"📊 PumpPortal trade: {tx_type} on {mint} by {trader}")
            logger.info(f"📋 Full trade data: {trade_data}")
            
            # Check if this is our own trade (from subscribeAccountTrade)
            wallet_pubkey = str(self.keypair.pubkey()) if self.keypair else None
            logger.info(f"🔍 Comparing trader '{trader}' with our wallet '{wallet_pubkey}'")
            
            if trader == wallet_pubkey:
                logger.info(f"🔄 Our own trade detected for {mint}, updating position...")
                
                # Check if we have a position for this token
                if mint in self.positions and self.positions[mint].is_active:
                    position = self.positions[mint]
                    
                    if tx_type == 'buy':
                        # Extract entry price from our buy trade
                        sol_amount = trade_data['solAmount']
                        token_amount = trade_data['tokenAmount']  # Use the actual token amount
                        
                        logger.info(f"💰 Trade data - SOL Amount: {sol_amount}, Token Amount: {token_amount}")
                        
                        if token_amount > 0:
                            entry_price = sol_amount / token_amount
                            position.entry_price = entry_price
                            position.token_amount = token_amount  # Update token amount from WebSocket data
                            # Ensure entry time is set for time-based sell strategy
                            logger.info(f"💰 Updated entry price for {mint}: ${entry_price:.6f}")
                            logger.info(f"💰 Updated token amount for {mint}: {token_amount:,.0f}")
                            
                            # Update transaction record with real token amount
                            await self._update_transaction_with_token_amount(mint, token_amount)
                        
                        # Use token metadata from the trade data (already available)
                        token_symbol = trade_info.token_symbol
                        token_name = trade_info.token_name
                        
                        if token_symbol and token_symbol != "Unknown":
                            position.token_symbol = token_symbol
                            position.token_name = token_name
                            logger.info(f"📝 Updated token metadata from trade data: {token_symbol} ({token_name})")
                        else:
                            logger.warning(f"⚠️ No token metadata available in trade data for {mint}")
                        
                        # Update UI with the real data
                        if self.ui_callback:
                            logger.info(f"📱 Sending metadata update to UI for {mint}")
                            logger.info(f"📊 Update data: entry_price={position.entry_price}, token_amount={position.token_amount}, symbol={position.token_symbol}")
                            
                            self.ui_callback('position_update', {
                                'action': 'metadata_update',
                                'mint': mint,
                                'entry_price': position.entry_price,
                                'token_amount': position.token_amount,
                                'token_symbol': position.token_symbol,
                                'token_name': position.token_name
                            })
                            logger.info(f"📱 Sent position update to UI for {mint}")
                        else:
                            logger.warning(f"⚠️ No UI callback available for position update")
                
                else:
                    # We don't have a position yet, create one from the trade data
                    logger.info(f"🆕 Creating new position from our own trade for {mint}")
                    
                    if tx_type == 'buy':
                        # Extract data from our buy trade
                        sol_amount = trade_data['solAmount']
                        token_amount = trade_data['tokenAmount']
                        
                        # Calculate entry price
                        entry_price = sol_amount / token_amount if token_amount > 0 else 0.0
                        
                        # Use token metadata from the trade data
                        token_symbol = trade_info.token_symbol
                        token_name = trade_info.token_name
                        
                        # Create position with real data from WebSocket
                        position = Position(
                            token_mint=mint,
                            token_symbol=token_symbol or "Unknown",
                            token_name=token_name or "Unknown",
                            entry_price=entry_price,
                            entry_timestamp=int(time.time()),
                            sol_amount=sol_amount,
                            token_amount=token_amount,
                            entry_time=int(time.time())
                        )
                        
                        self.positions[mint] = position
                        
                        logger.info(f"✅ Created position from WebSocket trade: {position}")
                        
                        # Send position creation to UI
                        if self.ui_callback:
                            logger.info(f"📱 Sending position creation to UI for {mint}")
                            
                            self.ui_callback('position_update', {
                                'action': 'buy',
                                'mint': mint,
                                'sol_amount': sol_amount,
                                'token_amount': token_amount,
                                'entry_price': entry_price,
                                'token_symbol': token_symbol or "Unknown",
                                'token_name': token_name or "Unknown"
                            })
                            logger.info(f"📱 Sent position creation to UI for {mint}")
                        else:
                            logger.warning(f"⚠️ No UI callback available for position creation")
                        
                        # Start price monitoring for this token
                        # await self._start_price_monitoring_for_token(mint)
                
                # If this was our own SELL, don't emit price updates to the UI; position update occurs elsewhere
                if tx_type == 'sell':
                    logger.info(f"🔕 Skipping price_update emission for our own sell on {mint}")
                    return
                return  # Don't process our own trades for buy counting
            
            # Check if this is a token we have a position in (from subscribeTokenTrade)
            if mint in self.positions and self.positions[mint].is_active:
                position = self.positions[mint]
                
                # Backfill missing token_amount from trade stream if we don't have it yet
                try:
                    if (position.token_amount is None or position.token_amount <= 0) and trade_info.token_amount and trade_info.token_amount > 0:
                        position.token_amount = trade_info.token_amount
                        logger.info(f"✅ Backfilled token_amount for {mint} from trade update: {position.token_amount:,.0f}")
                        # Also update the last transaction entry in the UI with real token amount
                        await self._update_transaction_with_token_amount(mint, position.token_amount)
                        # Notify UI of metadata update (no entry_price change)
                        if self.ui_callback:
                            self.ui_callback('position_update', {
                                'action': 'metadata_update',
                                'mint': mint,
                                'token_amount': position.token_amount
                            })
                except Exception as backfill_err:
                    logger.warning(f"⚠️ Could not backfill token_amount for {mint}: {backfill_err}")

                # Update position with latest price from websocket
                if trade_info.price > 0:
                    # Update current price for P&L calculations
                    position.current_price = trade_info.price
                    position.last_price_update = int(time.time())
                    
                    # Calculate P&L
                    if position.entry_price > 0:
                        pnl_sol = (trade_info.price - position.entry_price) * position.token_amount
                        pnl_percent = ((trade_info.price - position.entry_price) / position.entry_price) * 100 if position.entry_price > 0 else 0
                        
                        position.pnl_sol = pnl_sol
                        position.pnl_percent = pnl_percent
                        
                        logger.info(f"💰 Price update for {mint}: {trade_info.price:.12f} SOL")
                        logger.info(f"   Entry: {position.entry_price:.12f} SOL, Current: {trade_info.price:.12f} SOL")
                        logger.info(f"   P&L: {pnl_sol:.6f} SOL ({pnl_percent:+.2f}%)")
                        
                        # Update UI with price and P&L update
                        if self.ui_callback:
                            self.ui_callback('position_update', {
                                'action': 'price_update',
                                'mint': mint,
                                'current_price': trade_info.price,
                                'pnl_sol': pnl_sol,
                                'pnl_percent': pnl_percent,
                                'timestamp': int(time.time())
                            })
                            logger.info(f"📱 Sent price update to UI for {mint}")
                
                logger.info(f"📈 Token trade detected for our position: {mint}")
                logger.info(f"📊 Current position - Symbol: {position.token_symbol}, Entry Price: ${position.entry_price:.6f}, Token Amount: {position.token_amount:,.0f}")
                
                # For buy transactions, track buy activity and check buy-count rule
                if tx_type == 'buy':
                    # Track this buy in our position
                    position.buy_count_since_entry += 1
                    position.last_buy_timestamp = trade_data['timestamp']
                    position.buyers_since_entry.add(trader)
                    
                    logger.info(f"📈 Buy detected for {mint}: {position.buy_count_since_entry} buys since our entry")
                    logger.info(f"   Unique buyers: {len(position.buyers_since_entry)}")
                    logger.info(f"   Buyer: {trader}")
                    logger.info(f"   Trade SOL Amount: {trade_data['solAmount']}")
                    logger.info(f"   Trade Token Amount: {trade_data.get('tokenAmount', 0.0)}")
                    
                    # Use HeliusAPI's buy count method for buy-count rule
                    buy_count = self.helius_api.get_buy_count_for_token(mint, self.trade_history)
                    
                    logger.info(f"📈 PumpPortal: {buy_count} total buys detected for {mint}")
                    
                    # Check if we should sell based on configured strategy (buy-count or time-based)
                    settings = config_manager.config.bot_settings
                    if settings.auto_sell:
                        # Ensure entry_time is initialized for time-based checks
                        if not position.entry_time:
                            position.entry_time = position.entry_timestamp or int(time.time())
                        
                        # Check profit/loss targets first (highest priority)
                        should_sell = False
                        sell_reason = ""
                        
                        if position.current_price > 0 and position.entry_price > 0:
                            pnl_percent = ((position.current_price - position.entry_price) / position.entry_price) * 100
                            position.current_pnl_percent = pnl_percent
                            
                            # Check profit target
                            if pnl_percent >= settings.profit_target_percent:
                                should_sell = True
                                sell_reason = f"Profit target ({pnl_percent:.1f}%)"
                                logger.info(f"🎯 Profit target reached for {position.token_symbol or mint}: {pnl_percent:.1f}% >= {settings.profit_target_percent}%")
                            
                            # Check stop loss
                            elif pnl_percent <= -settings.stop_loss_percent:
                                should_sell = True
                                sell_reason = f"Stop loss ({pnl_percent:.1f}%)"
                                logger.info(f"🛑 Stop loss triggered for {position.token_symbol or mint}: {pnl_percent:.1f}% <= -{settings.stop_loss_percent}%")
                        
                        # Check other sell strategies only if profit/loss targets not met
                        if not should_sell:
                            if settings.sell_strategy == "buy_count":
                                if position.buy_count_since_entry >= settings.sell_after_buys:
                                    should_sell = True
                                    sell_reason = f"{settings.sell_after_buys}-buyer rule"
                                    logger.info(f"🎯 {settings.sell_after_buys}-buyer sell condition met for {mint}, executing sell...")
                            elif settings.sell_strategy == "time_based":
                                seconds_since_entry = int(time.time()) - position.entry_time
                                target_seconds = getattr(settings, 'sell_after_seconds', 18000)
                                if seconds_since_entry >= target_seconds:
                                    should_sell = True
                                    sell_reason = f"{target_seconds}-second rule"
                                    logger.info(f"⏰ {target_seconds}-second time-based sell condition met for {mint}, executing sell...")
                        
                        # Execute sell if any condition is met
                        if should_sell:
                            await self._execute_sell(mint, sell_reason)
            
            # Update UI if callback exists
            if self.ui_callback:
                self.ui_callback('trade_update', trade_data)
                        
        except Exception as e:
            logger.error(f"❌ Error handling PumpPortal trade: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")

    async def _handle_pumpportal_new_token(self, token_data: Dict[str, Any]):
        """Handle new token events from PumpPortal WebSocket"""
        try:
            logger.info(f"🆕 PumpPortal new token: {token_data}")
            
            # You can add logic here to automatically buy new tokens
            # or filter them based on your criteria
            
            # Update UI if callback exists
            if self.ui_callback:
                self.ui_callback('new_token', token_data)
                
        except Exception as e:
            logger.error(f"❌ Error handling PumpPortal new token: {e}")

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
                        logger.debug(f"📊 {position.token_symbol or mint}: {position.buy_count_since_entry}/{config_manager.config.bot_settings.sell_after_buys} buyers")
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
        except asyncio.CancelledError:
            logger.info("📊 Buy activity monitoring stopped")
        except Exception as e:
            logger.error(f"❌ Error monitoring buy activity: {e}")

    def get_wallet_balance_sync(self) -> float | None:
        """Get wallet balance synchronously (for startup/status checks)"""
        try:
            if not self.keypair:
                # Attempt auto-connect if a private key is configured
                if config_manager.has_private_key():
                    try:
                        private_key = config_manager.get_private_key()
                        success, _ = self.connect_wallet_from_key(private_key)
                        if not success:
                            logger.info(f"💰 Auto-connect failed; returning cached balance")
                            return config_manager.config.bot_state.sol_balance
                    except Exception as e:
                        logger.info(f"💰 No wallet keypair and auto-connect error: {e}; returning cached balance")
                        return config_manager.config.bot_state.sol_balance
                else:
                    logger.info(f"💰 No wallet connected, returning None for balance (sync)")
                    return None
            
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
            # If RPC didn't return a value, return cached balance
            return config_manager.config.bot_state.sol_balance
        except Exception as e:
            logger.error(f"❌ Error getting balance: {e}")
            if "401" in str(e) or "Unauthorized" in str(e):
                logger.error("💡 Check your HELIUS_API_KEY in the .env file")
            return config_manager.config.bot_state.sol_balance  # Return cached balance 

    async def get_wallet_balance(self) -> float | None:
        """Async helper to fetch current SOL balance via RPC and update state."""
        try:
            if not self.keypair:
                # Attempt auto-connect if a private key is configured
                if config_manager.has_private_key():
                    try:
                        private_key = config_manager.get_private_key()
                        success, _ = self.connect_wallet_from_key(private_key)
                        if not success:
                            logger.info(f"💰 Auto-connect failed; returning cached balance")
                            return config_manager.config.bot_state.sol_balance
                    except Exception as e:
                        logger.info(f"💰 No wallet keypair and auto-connect error: {e}; returning cached balance")
                        return config_manager.config.bot_state.sol_balance
                else:
                    logger.info(f"💰 No wallet connected, returning None for balance")
                    return None
            # Use async path only if there's a running loop; otherwise fall back to sync
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                return self.get_wallet_balance_sync()

            balance_response = await self.solana_client.get_balance(self.keypair.pubkey())
            if getattr(balance_response, 'value', None) is not None:
                balance_sol = balance_response.value / 10**9
                config_manager.update_bot_state(sol_balance=balance_sol)
                return balance_sol
            return config_manager.config.bot_state.sol_balance
        except Exception as e:
            logger.error(f"❌ Error fetching wallet balance: {e}")
            # Fallback to sync fetch if async path fails due to loop issues
            try:
                return self.get_wallet_balance_sync()
            except Exception:
                return config_manager.config.bot_state.sol_balance

    async def fetch_wallet_positions(self) -> List[Dict[str, Any]]:
        """Fetch current wallet positions using HeliusAPI method"""
        try:
            if not self.keypair:
                logger.warning("⚠️ No wallet connected, cannot fetch positions")
                return []
            
            wallet_address = str(self.keypair.pubkey())
            
            # Use HeliusAPI method to get positions from trade history
            positions = await self.helius_api.get_active_positions_from_trades(
                wallet_address, 
                self.trade_history
            )
            
            logger.info(f"✅ Fetched {len(positions)} wallet positions from trade data")
            return positions
            
        except Exception as e:
            logger.error(f"❌ Error fetching wallet positions: {e}")
            return []
    
    async def fetch_wallet_transactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch wallet transaction history using Helius API"""
        try:
            if not self.keypair:
                logger.warning("⚠️ No wallet connected, cannot fetch transactions")
                return []
            
            wallet_address = str(self.keypair.pubkey())
            raw_transactions = await self.helius_api.get_wallet_transactions(wallet_address, limit)
            
            # Parse each transaction using the Helius API parser
            processed_transactions = []
            for tx in raw_transactions:
                parsed_tx = self.helius_api.parse_transaction_for_bot(tx)
                if parsed_tx:
                    processed_transactions.append(parsed_tx)
            
            logger.info(f"✅ Fetched and processed {len(processed_transactions)} wallet transactions")
            return processed_transactions
            
        except Exception as e:
            logger.error(f"❌ Error fetching wallet transactions: {e}")
            return []
    
    async def update_position_prices(self):
        """Update prices for all active positions"""
        try:
            for mint, position in self.positions.items():
                if position.is_active:
                    # Get current price
                    current_price = await self.helius_api.get_token_price(mint)
                    if current_price:
                        position.current_price = current_price
                        
                        # Calculate P&L
                        if position.entry_price > 0:
                            pnl_percent = ((current_price - position.entry_price) / position.entry_price) * 100
                            position.current_pnl_percent = pnl_percent
                            
                            # Calculate SOL P&L
                            current_value = position.token_amount * current_price
                            entry_value = position.token_amount * position.entry_price
                            position.current_pnl = current_value - entry_value
                        
                        # Emit position update to UI
                        if self.ui_callback:
                            self.ui_callback('position_update', {
                                'mint': mint,
                                'current_price': current_price,
                                'pnl_percent': position.current_pnl_percent,
                                'pnl_sol': position.current_pnl,
                                'timestamp': int(time.time())
                            })
            
            logger.debug(f"✅ Updated prices for {len(self.positions)} positions")
            
        except Exception as e:
            logger.error(f"❌ Error updating position prices: {e}")
    
    async def start_price_monitoring(self):
        """Deprecated: global background price monitoring is disabled."""
        logger.info("⏭️ start_price_monitoring called but background monitoring is disabled.")
        return
    
    async def stop_price_monitoring(self):
        """Deprecated: background price monitoring is disabled."""
        logger.info("⏭️ stop_price_monitoring called but background monitoring is disabled.")
        return
    
    async def _record_transaction(self, action: str, mint: str, sol_amount: float, signature, token_amount: float = 0):
        """Record a transaction for history"""
        try:
            # Convert signature to string if it's a Signature object
            signature_str = str(signature) if signature else ""
            
            transaction_data = {
                'action': action,
                'mint': mint,
                'sol_amount': sol_amount,
                'token_amount': token_amount,
                'signature': signature_str,
                'timestamp': int(time.time())
            }
            
            # Emit transaction to UI
            if self.ui_callback:
                self.ui_callback('transaction', transaction_data)
            
            logger.info(f"📝 Recorded {action} transaction: {signature_str}")
            
        except Exception as e:
            logger.error(f"❌ Error recording transaction: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
    async def _update_transaction_with_token_amount(self, mint: str, token_amount: float):
        """Update a transaction record with the real token amount from WebSocket data"""
        try:
            # Convert token amount to string for UI
            token_amount_str = f"{token_amount:,.0f}" if token_amount > 0 else "0"
            
            # Emit updated transaction to UI
            if self.ui_callback:
                self.ui_callback('transaction_update', {
                    'mint': mint,
                    'token_amount': token_amount,
                    'token_amount_formatted': token_amount_str,
                    'timestamp': int(time.time())
                })
            
            logger.info(f"📝 Updated transaction for {mint} with token amount: {token_amount_str}")
            
        except Exception as e:
            logger.error(f"❌ Error updating transaction: {e}")
    
    async def _execute_sell(self, mint: str, reason: str):
        """Execute a sell order for a position"""
        try:
            if mint not in self.positions or not self.positions[mint].is_active:
                logger.warning(f"⚠️ No active position found for {mint}")
                return False
            
            position = self.positions[mint]
            logger.info(f"💸 Selling position for {position.token_symbol or mint} - Reason: {reason}")
            
            # Get transaction type from settings
            settings = config_manager.config.bot_settings
            priority_fee = settings.priority_fee
            
            logger.info(f"💰 Priority fee: {priority_fee} SOL")
            
            logger.info(f"💰 Token amount: {position.token_amount}")
            # Use trader to execute sell with transaction type from settings
            success, signature, sol_received = await self.trader.sell_token(
                mint, 
                position.token_amount, 
                transaction_type=settings.transaction_type,
                priority_fee=priority_fee
            )
            
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
                
                # Stop price monitoring for this token
                await self._stop_price_monitoring_for_token(mint)
                
                # Unsubscribe from monitoring
                self.monitor.remove_token_trade_subscription_sync(mint)
                
                # Record transaction
                await self._record_transaction('sell', mint, sol_received, signature, position.token_amount)
                
                # Update balance
                await self._update_wallet_balance()
                
                # Emit position update to UI
                if self.ui_callback:
                    # Convert signature to string for UI
                    signature_str = str(signature) if signature else ""
                    
                    self.ui_callback('position_update', {
                        'mint': mint,
                        'action': 'sell',
                        'sol_received': sol_received,
                        'pnl_percent': position.current_pnl_percent,
                        'pnl_sol': position.current_pnl,
                        'signature': signature_str,
                        'reason': reason,
                        'timestamp': int(time.time())
                    })
                
                logger.info(f"📊 Position closed for {mint}")
                return True
            else:
                logger.error(f"❌ Sell failed for {position.token_symbol or mint}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error executing sell: {e}")
            return False 

    async def _start_sell_task(self, mint: str):
        """Run a single sell operation and ensure slot release + queue draining."""
        try:
            success = await self._execute_sell_token(mint)
        except Exception as e:
            logger.error(f"❌ Sell task failed for {mint}: {e}")
            success = False
        finally:
            async with self._sell_state_lock:
                self._sells_in_progress.discard(mint)
                
                # Process queue based on sell result
                if self._sell_queue:
                    # Find all queued sells for this mint
                    same_mint_sells = [m for m in self._sell_queue if m == mint]
                    
                    if success:
                        # If sell was successful, remove all queued sells for this mint (position closed)
                        self._sell_queue = [m for m in self._sell_queue if m != mint]
                        if same_mint_sells:
                            logger.info(f"✅ Removed {len(same_mint_sells)} queued sells for {mint} (position closed)")
                    else:
                        # If sell failed, process the next queued sell for this mint
                        if same_mint_sells:
                            next_mint = same_mint_sells[0]
                            self._sell_queue.remove(next_mint)
                            self._sells_in_progress.add(next_mint)
                            asyncio.create_task(self._start_sell_task(next_mint))
                            logger.info(f"🔄 Processing next queued sell for {next_mint} (previous failed)")
                
                # Process any other mints in queue (different mints can run concurrently)
                remaining_queue = [m for m in self._sell_queue if m not in self._sells_in_progress]
                for next_mint in remaining_queue:
                    if next_mint not in self._sells_in_progress:
                        self._sell_queue.remove(next_mint)
                        self._sells_in_progress.add(next_mint)
                        asyncio.create_task(self._start_sell_task(next_mint))
                        logger.info(f"🚀 Starting concurrent sell task for {next_mint}")

    async def _execute_sell_token(self, mint: str) -> bool:
        """Execute the actual sell operation (moved from sell_token)"""
        try:
            logger.info(f"💸 _execute_sell_token called for {mint}")
            if not self.keypair:
                logger.error("❌ No wallet connected")
                return False
            
            if mint not in self.positions or not self.positions[mint].is_active:
                logger.warning(f"⚠️ No active position found for {mint}")
                return False
            
            position = self.positions[mint]
            logger.info(f"💸 Selling position for {position.token_symbol or mint}")
            logger.info(f"💸 Token amount: {position.token_amount}")

            # Safety: Ensure we have a non-zero token amount before attempting to sell
            if position.token_amount <= 0:
                try:
                    logger.warning(f"⚠️ token_amount is 0 for {mint}. Attempting to refresh from wallet balances before selling...")
                    wallet_address = str(self.keypair.pubkey())
                    balances = await self.helius_api.get_wallet_token_balances(wallet_address)
                    refreshed_amount = 0.0
                    for item in balances:
                        # Items are DAS assets; use helper to parse
                        parsed = self.helius_api.parse_token_balance_for_position(item)
                        if not parsed:
                            continue
                        if parsed.get('mint') == mint:
                            refreshed_amount = parsed.get('token_amount', 0.0)
                            break
                    if refreshed_amount > 0:
                        position.token_amount = refreshed_amount
                        logger.info(f"✅ Refreshed token_amount for {mint}: {refreshed_amount:,.0f}")
                    else:
                        logger.error(f"❌ Unable to determine token amount for {mint}. Aborting sell to prevent 0-amount transaction.")
                        return False
                except Exception as e:
                    logger.error(f"❌ Error refreshing token amount before sell for {mint}: {e}")
                    return False
            
            # Get transaction type from settings
            settings = config_manager.config.bot_settings
            priority_fee = settings.priority_fee
            
            logger.info(f"💰 Priority fee: {priority_fee} SOL")
            
            # Use trader to execute sell with transaction type from settings
            success, signature, sol_received = await self.trader.sell_token(
                mint, 
                position.token_amount, 
                transaction_type=settings.transaction_type,
                priority_fee=priority_fee
            )
            
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

                # Stop listening to this token's trades after it becomes inactive
                try:
                    self.monitor.remove_token_trade_subscription_sync(mint)
                except Exception as _:
                    pass
                
                return True
            else:
                logger.error(f"❌ Sell failed for {position.token_symbol or mint}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error selling token: {e}")
            return False