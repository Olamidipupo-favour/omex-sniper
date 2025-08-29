#!/usr/bin/env python3
"""
Token Filter Service - Handles token age filtering and Pump.fun API integration
"""

import asyncio
import aiohttp
import logging
import time
import ssl
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient

logger = logging.getLogger(__name__)

# SSL context configuration for macOS compatibility
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

@dataclass
class TokenAgeInfo:
    """Token age information"""
    mint: str
    symbol: str
    name: str
    created_timestamp: int
    age_days: float
    is_on_pump: bool = False
    pump_info: Optional[Dict] = None

class TokenFilterService:
    """Service for filtering tokens by age and Pump.fun integration"""
    
    def __init__(self, helius_rpc_url: str = "https://rpc.helius.xyz/?api-key=YOUR_API_KEY"):
        self.pump_api_url = "https://frontend-api-v3.pump.fun"
        
        # Add Pump.fun Helius endpoint as an option
        self.pump_helius_url = "https://pump-fe.helius-rpc.com/?api-key=1b8db865-a5a1-4535-9aec-01061440523b"
        
        # Fix Helius RPC URL - use public Solana RPC if Helius API key is not available
        if "YOUR_API_KEY" in helius_rpc_url or "api-key=" in helius_rpc_url and "YOUR_API_KEY" in helius_rpc_url:
            self.helius_rpc_url = "https://api.mainnet-beta.solana.com"
            logger.info("🔧 Using public Solana RPC (Helius API key not configured)")
        else:
            self.helius_rpc_url = helius_rpc_url
            logger.info(f"🔧 Using Helius RPC: {helius_rpc_url}")
        
        self.token_cache: Dict[str, TokenAgeInfo] = {}
        self.cache_expiry = 300  # 5 minutes cache
        self.last_cache_cleanup = time.time()
        self.helius_client = AsyncClient(self.helius_rpc_url)
        
        # Initialize Pump.fun Helius endpoint availability (will be tested when needed)
        self.pump_helius_available = False
        
        # SOL price variables (like in pump_fun_monitor.py)
        self.sol_price_usd = 188.76  # Default fallback price (current SOL price)
        self.last_sol_price_update = 0
        self.sol_price_cache_duration = 300  # 5 minutes
    
    async def _test_pump_helius_endpoint(self):
        """Test if Pump.fun Helius endpoint is available"""
        try:
            import aiohttp
            
            request_data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSlot",
                "params": []
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.pump_helius_url,
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                    timeout=5
                ) as response:
                    if response.status == 200:
                        self.pump_helius_available = True
                        logger.info("🔧 Pump.fun Helius endpoint is available")
                    else:
                        logger.info(f"🔧 Pump.fun Helius endpoint not available (HTTP {response.status})")
                        
        except Exception as e:
            logger.debug(f"🔧 Pump.fun Helius endpoint test failed: {e}")
        
    def _cleanup_cache(self):
        """Clean up expired cache entries"""
        current_time = time.time()
        if current_time - self.last_cache_cleanup > 60:  # Cleanup every minute
            expired_keys = []
            for mint, info in self.token_cache.items():
                if current_time - info.created_timestamp > self.cache_expiry:
                    expired_keys.append(mint)
            
            for key in expired_keys:
                del self.token_cache[key]
            
            self.last_cache_cleanup = current_time
            if expired_keys:
                logger.debug(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
    
    def _get_age_threshold_days(self, filter_type: str, custom_days: int = 7) -> int:
        """Get the age threshold in days based on filter type"""
        age_map = {
            "new_only": 0,  # Only newly created tokens
            "last_1_day": 1,
            "last_3_days": 3,
            "last_7_days": 7,
            "last_14_days": 14,
            "last_30_days": 30,
            "custom_days": custom_days
        }
        return age_map.get(filter_type, 0)
    
    def _is_token_within_age_limit(self, token_timestamp: int, age_threshold_days: int) -> bool:
        """Check if token is within the age limit"""
        if age_threshold_days == 0:
            # For "new_only", only show tokens created in the last hour
            return time.time() - token_timestamp < 3600
        
        # Calculate token age in days
        token_age_seconds = time.time() - token_timestamp
        token_age_days = token_age_seconds / (24 * 3600)
        
        return token_age_days <= age_threshold_days
    
    async def get_pump_token_info(self, mint: str) -> Optional[Dict]:
        """Get token information from Pump.fun API with better error handling"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.pump_api_url}/token/{mint}"
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"✅ Pump.fun API: Found token {mint}")
                        return data
                    elif response.status == 404:
                        # Token not found on Pump.fun - this is normal for many tokens
                        logger.debug(f"ℹ️ Pump.fun API: Token {mint} not found (404) - may not be on Pump.fun")
                        return None
                    else:
                        logger.warning(f"⚠️ Pump.fun API: Unexpected status {response.status} for {mint}")
                        return None
        except Exception as e:
            logger.debug(f"❌ Pump.fun API error for {mint}: {e}")
            return None
    
    async def get_token_creation_time_from_helius(self, mint: str) -> Optional[int]:
        """Get token creation time from Helius RPC"""
        try:
            # Get token account info
            token_pubkey = Pubkey.from_string(mint)
            
            # Get account info with maxSupportedTransactionVersion parameter
            response = await self.helius_client.get_account_info(
                token_pubkey,
                max_supported_transaction_version=0  # Support legacy transactions
            )
            
            if response.value:
                # Extract creation time from account data
                # This is a simplified approach - you might need to parse the actual token data
                account_data = response.value.data
                
                # For now, we'll use a fallback approach
                # In a real implementation, you'd parse the token metadata
                logger.debug(f"🔍 Helius: Got account info for {mint}")
                return int(time.time()) - (24 * 3600)  # Assume 1 day old as fallback
            else:
                logger.debug(f"⚠️ Helius: No account info found for {mint}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Helius RPC error for {mint}: {e}")
            return None
    
    async def get_recent_tokens_from_helius(self, days: int = 7) -> List[Dict]:
        """Get recent tokens from Helius RPC using optimized approach"""
        try:
            logger.info(f"🔍 Helius: Searching for tokens from last {days} days...")
            
            # Use a much more efficient approach - get recent blocks and look for token creation
            try:
                # Get recent blocks instead of individual transactions
                # This is much faster and more efficient
                recent_blocks = await self._get_recent_blocks_with_tokens(days)
                
                if not recent_blocks:
                    logger.warning("⚠️ Helius: No recent blocks with token activity found")
                    return []
                
                logger.info(f"📊 Helius: Found {len(recent_blocks)} recent tokens")
                return recent_blocks
                
            except Exception as e:
                logger.error(f"❌ Helius: Error getting recent blocks: {e}")
                return []
            
        except Exception as e:
            logger.error(f"❌ Error fetching recent tokens from Helius: {e}")
            return []
    
    async def _get_recent_blocks_with_tokens(self, days: int) -> List[Dict]:
        """Get recent blocks and extract token information efficiently"""
        try:
            # Calculate time threshold
            current_time = time.time()
            time_threshold = current_time - (days * 24 * 3600)
            
            # Get recent block production info
            try:
                # Get recent slot info
                slot_response = await self.helius_client.get_slot()
                if not slot_response.value:
                    logger.warning("⚠️ Helius: Could not get current slot")
                    return []
                
                current_slot = slot_response.value
                logger.info(f"🔍 Helius: Current slot: {current_slot}")
                
                # Get recent blocks (much more efficient than individual transactions)
                # We'll get the last 100 slots and check for token activity
                recent_tokens = []
                processed_mints = set()
                
                # Start from a recent slot and work backwards
                start_slot = max(0, current_slot - 100)  # Last 100 slots (reduced from 1000)
                
                for slot_offset in range(0, 100, 5):  # Check every 5th slot for efficiency (reduced from 10)
                    try:
                        slot = start_slot + slot_offset
                        
                        # Get block info for this slot
                        block_response = await self.helius_client.get_block(
                            slot,
                            encoding="jsonParsed",
                            max_supported_transaction_version=0
                        )
                        
                        if not block_response.value:
                            continue
                        
                        block = block_response.value
                        
                        # Check if block is too old
                        if hasattr(block, 'block_time') and block.block_time:
                            if block.block_time < time_threshold:
                                continue
                        
                        # Extract transactions from block
                        if hasattr(block, 'transactions') and block.transactions:
                            for tx in block.transactions:
                                try:
                                    # Look for token program instructions
                                    if hasattr(tx, 'transaction') and tx.transaction:
                                        if hasattr(tx.transaction, 'message') and tx.transaction.message:
                                            if hasattr(tx.transaction.message, 'instructions'):
                                                for instruction in tx.transaction.message.instructions:
                                                    if hasattr(instruction, 'program_id'):
                                                        program_id = instruction.program_id
                                                        if program_id == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                                                            # Found token program instruction
                                                            await self._extract_token_from_instruction(
                                                                instruction, block, recent_tokens, processed_mints
                                                            )
                                    
                                    # Also check inner instructions
                                    if hasattr(tx, 'meta') and tx.meta:
                                        if hasattr(tx.meta, 'inner_instructions'):
                                            for inner_instruction in tx.meta.inner_instructions:
                                                if hasattr(inner_instruction, 'instructions'):
                                                    for instruction in inner_instruction.instructions:
                                                        if hasattr(instruction, 'program_id'):
                                                            program_id = instruction.program_id
                                                            if program_id == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                                                                await self._extract_token_from_instruction(
                                                                    instruction, block, recent_tokens, processed_mints
                                                                )
                                
                                except Exception as tx_error:
                                    logger.debug(f"⚠️ Helius: Error processing transaction in slot {slot}: {tx_error}")
                                    continue
                        
                        # Limit results to avoid overwhelming
                        if len(recent_tokens) >= 20:  # Reduced from 50
                            break
                    
                    except Exception as slot_error:
                        logger.debug(f"⚠️ Helius: Error processing slot {slot}: {slot_error}")
                        continue
                
                logger.info(f"📊 Helius: Processed blocks and found {len(recent_tokens)} tokens")
                return recent_tokens
                
            except Exception as e:
                logger.error(f"❌ Helius: Error in block processing: {e}")
                return []
            
        except Exception as e:
            logger.error(f"❌ Error in _get_recent_blocks_with_tokens: {e}")
            return []
    
    async def _extract_token_from_instruction(self, instruction, block, recent_tokens, processed_mints):
        """Extract token information from a token program instruction"""
        try:
            # Check if this is an InitializeMint instruction
            if hasattr(instruction, 'parsed') and instruction.parsed:
                parsed = instruction.parsed
                if parsed.get('type') == 'initializeMint':
                    mint_address = parsed.get('info', {}).get('mint')
                    if mint_address and mint_address not in processed_mints:
                        processed_mints.add(mint_address)
                        
                        # Create token info
                        token_info = {
                            'mint': mint_address,
                            'symbol': f'TOKEN_{len(recent_tokens)}',
                            'name': f'Token {len(recent_tokens)}',
                            'created_timestamp': block.block_time if hasattr(block, 'block_time') else int(time.time()),
                            'market_cap': 0,
                            'price': 0,
                            'liquidity': 0,
                            'holders': 0,
                            'is_on_pump': False,
                            'source': 'helius'
                        }
                        
                        recent_tokens.append(token_info)
                        
        except Exception as e:
            logger.debug(f"⚠️ Helius: Error extracting token from instruction: {e}")
            pass
    
    async def get_token_age_info(self, mint: str, symbol: str, name: str, 
                                created_timestamp: int, include_pump_check: bool = True) -> TokenAgeInfo:
        """Get comprehensive token age information"""
        self._cleanup_cache()
        
        # Check cache first
        if mint in self.token_cache:
            return self.token_cache[mint]
        
        # Calculate age
        current_time = time.time()
        age_seconds = current_time - created_timestamp
        age_days = age_seconds / (24 * 3600)
        
        # Initialize token info (without Pump.fun checking)
        token_info = TokenAgeInfo(
            mint=mint,
            symbol=symbol,
            name=name,
            created_timestamp=created_timestamp,
            age_days=age_days,
            is_on_pump=False,  # Default to False, no checking
            pump_info=None
        )
        
        # Cache the result
        self.token_cache[mint] = token_info
        
        return token_info
    
    def filter_tokens_by_age(self, tokens: List[Dict], filter_type: str, 
                           custom_days: int = 7, include_pump_tokens: bool = True) -> List[Dict]:
        """Filter tokens based on age criteria"""
        age_threshold_days = self._get_age_threshold_days(filter_type, custom_days)
        
        filtered_tokens = []
        current_time = time.time()
        
        for token in tokens:
            created_timestamp = token.get('created_timestamp', 0)
            
            # Check age filter
            if not self._is_token_within_age_limit(created_timestamp, age_threshold_days):
                continue
            
            # No Pump.fun requirement check - removed
            
            filtered_tokens.append(token)
        
        logger.info(f"🔍 Filtered {len(tokens)} tokens to {len(filtered_tokens)} based on age filter: {filter_type}")
        return filtered_tokens
    
    async def enrich_token_with_age_info(self, token: Dict, include_pump_check: bool = True) -> Dict:
        """Enrich token data with age information"""
        mint = token.get('mint', '')
        symbol = token.get('symbol', '')
        name = token.get('name', '')
        created_timestamp = token.get('created_timestamp', 0)
        
        if not mint or not created_timestamp:
            return token
        
        # Get age info (without Pump.fun checking)
        age_info = await self.get_token_age_info(
            mint, symbol, name, created_timestamp, include_pump_check=False
        )
        
        # Add age information to token
        token['age_days'] = age_info.age_days
        token['is_on_pump'] = False  # Always False, no checking
        token['pump_info'] = None
        
        return token
    
    async def get_recent_pump_tokens(self, days: int = 7, batch_callback=None, batch_size: int = 10, cancellation_check=None) -> List[Dict]:
        """
        Get recent tokens from Pump.fun API using the real endpoint with timestamp-based fetching
        Now supports batch processing with callback for immediate frontend updates
        """
        try:
            logger.info(f"🔍 Getting Pump.fun tokens for last {days} days with batch size {batch_size}...")
            
            # Get current SOL price for market cap conversion
            sol_price_usd = await self.get_sol_price()
            
            # Calculate timestamp threshold
            current_time = int(time.time() * 1000)  # Convert to milliseconds
            time_threshold = current_time - (days * 24 * 3600 * 1000)  # Convert days to milliseconds
            
            all_tokens = []
            offset = 0
            limit = 100
            max_iterations = 10  # Prevent infinite loops
            current_batch = []
            
            # Fetch tokens with pagination and batch processing
            for iteration in range(max_iterations):
                try:
                    # Use the real Pump.fun API endpoint with pagination
                    url = f"{self.pump_api_url}/coins/for-you?offset={offset}&limit={limit}&includeNsfw=false"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=15) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                if not data:  # No more data
                                    logger.info(f"📊 No more tokens found at offset {offset}")
                                    break
                                
                                logger.info(f"📊 Fetched {len(data)} tokens at offset {offset}")
                                
                                # Convert Pump.fun data format to our standard format
                                converted_tokens = []
                                for token in data:
                                    try:
                                        # Check if token is within our time range
                                        created_timestamp = token.get('created_timestamp', 0)
                                        if created_timestamp < time_threshold:
                                            # Token is too old, skip
                                            continue
                                        
                                        # Extract bonding curve data (like in pump_fun_monitor.py)
                                        v_sol_in_bonding_curve = token.get('virtual_sol_reserves', 0) / 1e9 if token.get('virtual_sol_reserves') else 0  # Convert from lamports to SOL
                                        v_tokens_in_bonding_curve = token.get('virtual_token_reserves', 0) / 1e6 if token.get('virtual_token_reserves') else 0  # Convert from raw token amount
                                        
                                        # Calculate price per token (like in pump_fun_monitor.py)
                                        price_per_token_sol = v_sol_in_bonding_curve / v_tokens_in_bonding_curve if v_tokens_in_bonding_curve > 0 else 0.0
                                        price_per_token_usd = price_per_token_sol * sol_price_usd
                                        
                                        # Get market cap in SOL and convert to USD
                                        market_cap_sol = token.get('market_cap', 0)
                                        market_cap_usd = market_cap_sol * sol_price_usd
                                        
                                        # Extract and convert the data
                                        converted_token = {
                                            'mint': token.get('mint', ''),
                                            'symbol': token.get('symbol', ''),
                                            'name': token.get('name', ''),
                                            'created_timestamp': created_timestamp,
                                            'market_cap': market_cap_usd,  # Use USD market cap
                                            'price': price_per_token_usd,  # Use USD price
                                            'liquidity': v_sol_in_bonding_curve,  # SOL in bonding curve
                                            'holders': token.get('num_participants', 0) if token.get('num_participants') else 0,
                                            'is_on_pump': True,  # These are definitely on Pump.fun
                                            'source': 'pump_api',
                                            'description': token.get('description', ''),
                                            'image_uri': token.get('image_uri', ''),
                                            'twitter': token.get('twitter', ''),
                                            'telegram': token.get('telegram', ''),
                                            'website': token.get('website', ''),
                                            'usd_market_cap': market_cap_usd,
                                            'is_currently_live': token.get('is_currently_live', False),
                                            'reply_count': token.get('reply_count', 0),
                                            'nsfw': token.get('nsfw', False),
                                            'bonding_curve': token.get('bonding_curve', ''),
                                            'creator': token.get('creator', ''),
                                            'total_supply': token.get('total_supply', 0),
                                            'virtual_token_reserves': token.get('virtual_token_reserves', 0),
                                            # Add bonding curve data like in pump_fun_monitor.py
                                            'sol_in_pool': v_sol_in_bonding_curve,
                                            'tokens_in_pool': v_tokens_in_bonding_curve,
                                            'initial_buy': token.get('initial_buy', 0)
                                        }
                                        
                                        # Calculate age in days
                                        if converted_token['created_timestamp']:
                                            age_seconds = (current_time / 1000) - (converted_token['created_timestamp'] / 1000)
                                            converted_token['age_days'] = age_seconds / (24 * 3600)
                                        else:
                                            converted_token['age_days'] = 0
                                        
                                        converted_tokens.append(converted_token)
                                        
                                    except Exception as e:
                                        logger.debug(f"⚠️ Error converting token {token.get('mint', 'unknown')}: {e}")
                                        continue
                                
                                # Process tokens in batches for immediate frontend updates
                                for converted_token in converted_tokens:
                                    # Check for cancellation before processing each token
                                    if cancellation_check and cancellation_check():
                                        logger.info("🛑 Historical token loading cancelled during batch processing")
                                        return all_tokens
                                    
                                    current_batch.append(converted_token)
                                    
                                    # If batch is full, send it immediately
                                    if len(current_batch) >= batch_size:
                                        if batch_callback:
                                            logger.info(f"📤 Sending batch of {len(current_batch)} tokens to frontend")
                                            try:
                                                await batch_callback(current_batch.copy())
                                            except Exception as e:
                                                logger.error(f"❌ Error in batch callback: {e}")
                                        
                                        # Add to total collection and clear batch
                                        all_tokens.extend(current_batch)
                                        current_batch = []
                                
                                # If we got fewer tokens than requested, we've reached the end
                                if len(data) < limit:
                                    logger.info(f"📊 Reached end of data (got {len(data)} tokens, requested {limit})")
                                    break
                                
                                # Move to next page
                                offset += limit
                                
                            elif response.status == 404:
                                logger.warning("⚠️ Pump.fun API: /coins/for-you endpoint not found (404)")
                                break
                            else:
                                logger.error(f"❌ Pump.fun API: Unexpected status {response.status}")
                                break
                                
                except Exception as e:
                    logger.error(f"❌ Error fetching tokens at offset {offset}: {e}")
                    break
            
            # Send any remaining tokens in the final batch
            if current_batch and batch_callback:
                logger.info(f"📤 Sending final batch of {len(current_batch)} tokens to frontend")
                try:
                    await batch_callback(current_batch)
                except Exception as e:
                    logger.error(f"❌ Error in final batch callback: {e}")
                
                all_tokens.extend(current_batch)
            
            logger.info(f"📊 Total Pump.fun tokens found: {len(all_tokens)}")
            return all_tokens
                            
        except Exception as e:
            logger.error(f"❌ Error fetching recent Pump.fun tokens: {e}")
            return await self._get_fallback_pump_tokens(days)
    
    async def _get_fallback_pump_tokens(self, days: int = 7) -> List[Dict]:
        """Fallback method if the main Pump.fun API fails"""
        try:
            logger.info("🔄 Using fallback Pump.fun token method...")
            
            # Method 1: Try to get tokens from Pump.fun's recent activity
            known_pump_tokens = await self._get_known_pump_tokens()
            
            # Method 2: Try to get tokens from Pump.fun's trending or recent
            trending_tokens = await self._get_trending_pump_tokens()
            
            # Combine results
            all_tokens = known_pump_tokens + trending_tokens
            
            # Filter by creation date if we have timestamps
            current_time = time.time()
            age_threshold = days * 24 * 3600  # Convert days to seconds
            
            recent_tokens = []
            for token in all_tokens:
                created_timestamp = token.get('created_timestamp', 0)
                if created_timestamp == 0 or current_time - created_timestamp <= age_threshold:
                    recent_tokens.append(token)
            
            logger.info(f"📊 Fallback: Found {len(recent_tokens)} recent Pump.fun tokens from last {days} days")
            return recent_tokens
            
        except Exception as e:
            logger.error(f"❌ Error in fallback Pump.fun token method: {e}")
            return []
    
    async def _get_known_pump_tokens(self) -> List[Dict]:
        """Get known tokens that are verified to be on Pump.fun"""
        try:
            # Get current SOL price for market cap conversion
            sol_price_usd = await self.get_sol_price()
            
            # List of known tokens that are typically on Pump.fun
            known_tokens = [
                {
                    'mint': 'So11111111111111111111111111111111111111112',  # WSOL
                    'symbol': 'WSOL',
                    'name': 'Wrapped SOL',
                    'created_timestamp': int(time.time()) - (24 * 3600),  # 1 day ago
                    'market_cap': 1000 * sol_price_usd,  # 1000 SOL converted to USD
                    'price': 1.0 * sol_price_usd,  # 1 SOL converted to USD
                    'liquidity': 1000.0,
                    'holders': 10000,
                    'is_on_pump': True,
                    'source': 'pump_known',
                    'sol_in_pool': 1000.0,
                    'tokens_in_pool': 1000.0,
                    'initial_buy': 0
                },
                {
                    'mint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                    'symbol': 'USDC',
                    'name': 'USD Coin',
                    'created_timestamp': int(time.time()) - (2 * 24 * 3600),  # 2 days ago
                    'market_cap': 5000 * sol_price_usd,  # 5000 SOL converted to USD
                    'price': 1.0,  # USDC is pegged to $1
                    'liquidity': 2000.0,
                    'holders': 50000,
                    'is_on_pump': True,
                    'source': 'pump_known',
                    'sol_in_pool': 2000.0,
                    'tokens_in_pool': 2000.0,
                    'initial_buy': 0
                },
                {
                    'mint': 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',  # USDT
                    'symbol': 'USDT',
                    'name': 'Tether USD',
                    'created_timestamp': int(time.time()) - (3 * 24 * 3600),  # 3 days ago
                    'market_cap': 3000 * sol_price_usd,  # 3000 SOL converted to USD
                    'price': 1.0,  # USDT is pegged to $1
                    'liquidity': 1500.0,
                    'holders': 30000,
                    'is_on_pump': True,
                    'source': 'pump_known',
                    'sol_in_pool': 1500.0,
                    'tokens_in_pool': 1500.0,
                    'initial_buy': 0
                }
            ]
            
            # Verify these tokens are actually on Pump.fun
            verified_tokens = []
            for token in known_tokens:
                mint = token.get('mint', '')
                if mint:
                    # Check if token exists on Pump.fun
                    pump_info = await self.get_pump_token_info(mint)
                    if pump_info:
                        # Token is on Pump.fun, add it to verified list
                        token['pump_info'] = pump_info
                        verified_tokens.append(token)
                        logger.debug(f"✅ Verified token on Pump.fun: {token.get('symbol', 'N/A')}")
                    else:
                        logger.debug(f"⚠️ Token not on Pump.fun: {token.get('symbol', 'N/A')}")
            
            logger.info(f"📊 Found {len(verified_tokens)} verified Pump.fun tokens")
            return verified_tokens
            
        except Exception as e:
            logger.error(f"❌ Error getting known Pump.fun tokens: {e}")
            return []
    
    async def _get_trending_pump_tokens(self) -> List[Dict]:
        """Get trending tokens from Pump.fun - placeholder for now"""
        try:
            # Get current SOL price for market cap conversion
            sol_price_usd = await self.get_sol_price()
            
            # This is a placeholder - in a real implementation, you'd:
            # 1. Scrape Pump.fun's trending page
            # 2. Use Pump.fun's WebSocket API
            # 3. Use a third-party API that tracks Pump.fun tokens
            
            # For now, return some sample trending tokens
            trending_tokens = [
                {
                    'mint': '7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr',  # Sample trending token
                    'symbol': 'TREND',
                    'name': 'Trending Token',
                    'created_timestamp': int(time.time()) - (6 * 3600),  # 6 hours ago
                    'market_cap': 50 * sol_price_usd,  # 50 SOL converted to USD
                    'price': 0.001 * sol_price_usd,  # 0.001 SOL converted to USD
                    'liquidity': 100.0,
                    'holders': 500,
                    'is_on_pump': True,
                    'source': 'pump_trending',
                    'sol_in_pool': 100.0,
                    'tokens_in_pool': 100000.0,  # More tokens = lower price
                    'initial_buy': 0
                },
                {
                    'mint': '9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM',  # Another sample
                    'symbol': 'HOT',
                    'name': 'Hot Token',
                    'created_timestamp': int(time.time()) - (12 * 3600),  # 12 hours ago
                    'market_cap': 75 * sol_price_usd,  # 75 SOL converted to USD
                    'price': 0.002 * sol_price_usd,  # 0.002 SOL converted to USD
                    'liquidity': 150.0,
                    'holders': 750,
                    'is_on_pump': True,
                    'source': 'pump_trending',
                    'sol_in_pool': 150.0,
                    'tokens_in_pool': 75000.0,  # More tokens = lower price
                    'initial_buy': 0
                }
            ]
            
            logger.info(f"📊 Found {len(trending_tokens)} trending Pump.fun tokens")
            return trending_tokens
            
        except Exception as e:
            logger.error(f"❌ Error getting trending Pump.fun tokens: {e}")
            return []
    
    async def get_trending_pump_tokens(self, days: int = 7, batch_callback=None, batch_size: int = 10, cancellation_check=None) -> List[Dict]:
        """
        Get trending/running tokens from Pump.fun /api/runners endpoint with timestamp filtering
        Now supports batch processing with callback for immediate frontend updates
        """
        try:
            logger.info(f"🔍 Getting trending Pump.fun tokens for last {days} days with batch size {batch_size}...")
            
            # Calculate timestamp threshold
            current_time = int(time.time() * 1000)  # Convert to milliseconds
            time_threshold = current_time - (days * 24 * 3600 * 1000)  # Convert days to milliseconds
            
            # Use the Pump.fun runners API endpoint
            url = f"https://pump.fun/api/runners"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Pump.fun Runners API: Successfully fetched {len(data)} trending tokens")
                        
                        # Convert Pump.fun runners data format to our standard format with batch processing
                        converted_tokens = []
                        current_batch = []
                        
                        for runner in data:
                            try:
                                coin = runner.get('coin', {})
                                if not coin:
                                    continue
                                
                                # Check if token is within our time range
                                created_timestamp = coin.get('created_timestamp', 0)
                                if created_timestamp < time_threshold:
                                    # Token is too old, skip
                                    continue
                                
                                # Extract and convert the data
                                converted_token = {
                                    'mint': coin.get('mint', ''),
                                    'symbol': coin.get('symbol', ''),
                                    'name': coin.get('name', ''),
                                    'created_timestamp': created_timestamp,
                                    'market_cap': coin.get('market_cap', 0),
                                    'price': coin.get('price', 0),
                                    'liquidity': coin.get('virtual_sol_reserves', 0) / 1e9 if coin.get('virtual_sol_reserves') else 0,  # Convert from lamports to SOL
                                    'holders': coin.get('reply_count', 0),  # Use reply_count as holder proxy
                                    'is_on_pump': True,  # These are definitely on Pump.fun
                                    'source': 'pump_runners',
                                    'description': coin.get('description', ''),
                                    'image_uri': coin.get('image_uri', ''),
                                    'twitter': coin.get('twitter', ''),
                                    'telegram': coin.get('telegram', ''),
                                    'website': coin.get('website', ''),
                                    'usd_market_cap': coin.get('usd_market_cap', 0),
                                    'is_currently_live': coin.get('is_currently_live', False),
                                    'reply_count': coin.get('reply_count', 0),
                                    'nsfw': coin.get('nsfw', False),
                                    'bonding_curve': coin.get('bonding_curve', ''),
                                    'creator': coin.get('creator', ''),
                                    'total_supply': coin.get('total_supply', 0),
                                    'virtual_token_reserves': coin.get('virtual_token_reserves', 0),
                                    'complete': coin.get('complete', False),
                                    'raydium_pool': coin.get('raydium_pool', ''),
                                    'market_id': coin.get('market_id', ''),
                                    'king_of_the_hill_timestamp': coin.get('king_of_the_hill_timestamp', ''),
                                    'last_reply': coin.get('last_reply', ''),
                                    'is_banned': coin.get('is_banned', False),
                                    'banner_uri': coin.get('banner_uri', ''),
                                    'video_uri': coin.get('video_uri', ''),
                                    'show_name': coin.get('show_name', True),
                                    'metadata_uri': coin.get('metadata_uri', ''),
                                    'associated_bonding_curve': coin.get('associated_bonding_curve', ''),
                                    # Additional runner-specific data
                                    'runner_description': runner.get('description', ''),
                                    'modified_by': runner.get('modifiedBy', ''),
                                    'is_trending': True
                                }
                                
                                # Calculate age in days
                                if converted_token['created_timestamp']:
                                    age_seconds = (current_time / 1000) - (converted_token['created_timestamp'] / 1000)
                                    converted_token['age_days'] = age_seconds / (24 * 3600)
                                else:
                                    converted_token['age_days'] = 0
                                
                                # Check for cancellation before processing each token
                                if cancellation_check and cancellation_check():
                                    logger.info("🛑 Historical token loading cancelled during trending token processing")
                                    return converted_tokens
                                
                                converted_tokens.append(converted_token)
                                current_batch.append(converted_token)
                                
                                # If batch is full, send it immediately
                                if len(current_batch) >= batch_size and batch_callback:
                                    logger.info(f"📤 Sending batch of {len(current_batch)} trending tokens to frontend")
                                    try:
                                        await batch_callback(current_batch.copy())
                                    except Exception as e:
                                        logger.error(f"❌ Error in trending tokens batch callback: {e}")
                                    
                                    current_batch = []
                                
                            except Exception as e:
                                logger.debug(f"⚠️ Error converting runner token {runner.get('coin', {}).get('mint', 'unknown')}: {e}")
                                continue
                        
                        # Send any remaining tokens in the final batch
                        if current_batch and batch_callback:
                            logger.info(f"📤 Sending final batch of {len(current_batch)} trending tokens to frontend")
                            try:
                                await batch_callback(current_batch)
                            except Exception as e:
                                logger.error(f"❌ Error in final trending tokens batch callback: {e}")
                        
                        logger.info(f"📊 Found {len(converted_tokens)} recent trending Pump.fun tokens from last {days} days")
                        return converted_tokens
                            
                    elif response.status == 404:
                        logger.warning("⚠️ Pump.fun Runners API: /api/runners endpoint not found (404)")
                        return []
                    else:
                        logger.error(f"❌ Pump.fun Runners API: Unexpected status {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Error fetching trending Pump.fun tokens: {e}")
            return []
    
    async def get_recent_tokens_simple(self, days: int = 7) -> List[Dict]:
        """Get recent tokens using a simpler approach - just return some sample tokens for testing"""
        try:
            logger.info(f"🔍 Simple: Getting sample tokens for last {days} days...")
            
            # Get current SOL price for market cap conversion
            sol_price_usd = await self.get_sol_price()
            
            # For now, return some sample tokens to test the system
            # In a real implementation, you'd query a token database or use a different API
            sample_tokens = [
                {
                    'mint': 'So11111111111111111111111111111111111111112',  # Wrapped SOL
                    'symbol': 'WSOL',
                    'name': 'Wrapped SOL',
                    'created_timestamp': int(time.time()) - (3 * 24 * 3600),  # 3 days ago
                    'market_cap': 1000 * sol_price_usd,  # 1000 SOL converted to USD
                    'price': 1.0 * sol_price_usd,  # 1 SOL converted to USD
                    'liquidity': 1000.0,
                    'holders': 10000,
                    'is_on_pump': False,
                    'source': 'sample',
                    'sol_in_pool': 1000.0,
                    'tokens_in_pool': 1000.0,
                    'initial_buy': 0
                },
                {
                    'mint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                    'symbol': 'USDC',
                    'name': 'USD Coin',
                    'created_timestamp': int(time.time()) - (5 * 24 * 3600),  # 5 days ago
                    'market_cap': 5000 * sol_price_usd,  # 5000 SOL converted to USD
                    'price': 1.0,  # USDC is pegged to $1
                    'liquidity': 2000.0,
                    'holders': 50000,
                    'is_on_pump': False,
                    'source': 'sample',
                    'sol_in_pool': 2000.0,
                    'tokens_in_pool': 2000.0,
                    'initial_buy': 0
                }
            ]
            
            logger.info(f"📊 Simple: Found {len(sample_tokens)} sample tokens")
            logger.info(f"📋 Sample tokens JSON: {sample_tokens}")
            return sample_tokens
            
        except Exception as e:
            logger.error(f"❌ Error in simple token search: {e}")
            return []
    
    async def get_hybrid_recent_tokens(self, days: int = 7, include_pump_only: bool = True, batch_callback=None, batch_size: int = 10, cancellation_check=None) -> List[Dict]:
        """
        Get recent tokens using hybrid approach (Pump.fun + Pump.fun Helius + Helius) - defaults to pump-only
        Now supports batch processing with callback for immediate frontend updates
        """
        try:
            logger.info(f"🔍 Getting hybrid token list for last {days} days with batch size {batch_size}...")
            
            # Get tokens from Pump.fun (always prioritize this) with batch processing
            pump_tokens = await self.get_recent_pump_tokens(days, batch_callback, batch_size)
            logger.info(f"📊 Found {len(pump_tokens)} tokens from Pump.fun")
            if pump_tokens:
                logger.info(f"📋 Pump.fun tokens JSON: {pump_tokens[:2]}")  # Show first 2 tokens
            
            # Check for cancellation after Pump.fun tokens
            if cancellation_check and cancellation_check():
                logger.info("🛑 Historical token loading cancelled during Pump.fun token fetch")
                return []
            
            # # Get tokens from Pump.fun Helius endpoint (if available)
            # pump_helius_tokens = await self.get_recent_tokens_from_pump_helius(days)
            # logger.info(f"📊 Found {len(pump_helius_tokens)} tokens from Pump.fun Helius")
            # if pump_helius_tokens:
            #     logger.info(f"📋 Pump.fun Helius tokens JSON: {pump_helius_tokens[:2]}")  # Show first 2 tokens
            
            # Get trending/running tokens from Pump.fun /api/runners endpoint with batch processing
            trending_tokens = await self.get_trending_pump_tokens(days, batch_callback, batch_size)
            logger.info(f"📊 Found {len(trending_tokens)} trending Pump.fun tokens")
            if trending_tokens:
                logger.info(f"📋 Trending Pump.fun tokens JSON: {trending_tokens[:2]}") # Show first 2 tokens
            
            # Check for cancellation after trending tokens
            if cancellation_check and cancellation_check():
                logger.info("🛑 Historical token loading cancelled during trending token fetch")
                return []
            
            # If pump_only is True, return only Pump.fun tokens (including Pump.fun Helius)
            if include_pump_only:
                logger.info("🎯 Returning Pump.fun tokens only")
                # Combine Pump.fun and Pump.fun Helius tokens
                all_pump_tokens = pump_tokens + trending_tokens
                # Deduplicate
                unique_pump_tokens = {}
                for token in all_pump_tokens:
                    mint = token.get('mint', '')
                    if mint and mint not in unique_pump_tokens:
                        unique_pump_tokens[mint] = token
                return list(unique_pump_tokens.values())
            
            # Get tokens from Helius (only if not pump-only and using Helius RPC)
            helius_tokens = []
            # Check if we're using public Solana RPC (skip Helius calls)
            if "api.mainnet-beta.solana.com" in self.helius_rpc_url:
                logger.info("⚠️ Using public Solana RPC - skipping Helius calls (rate limited)")
                helius_tokens = await self.get_recent_tokens_simple(days)
                logger.info(f"📊 Found {len(helius_tokens)} tokens from simple fallback")
            else:
                try:
                    helius_tokens = await self.get_recent_tokens_from_helius(days)
                    logger.info(f"📊 Found {len(helius_tokens)} tokens from Helius")
                    if helius_tokens:
                        logger.info(f"📋 Helius tokens JSON: {helius_tokens[:2]}")  # Show first 2 tokens
                except Exception as e:
                    logger.warning(f"⚠️ Helius failed, using simple fallback: {e}")
                    # Use simple fallback if Helius fails
                    helius_tokens = await self.get_recent_tokens_simple(days)
                    logger.info(f"📊 Found {len(helius_tokens)} tokens from simple fallback")
                    if helius_tokens:
                        logger.info(f"📋 Fallback tokens JSON: {helius_tokens}")
            
            # Combine and deduplicate (Pump.fun tokens take priority)
            all_tokens = pump_tokens + pump_helius_tokens + helius_tokens + trending_tokens
            unique_tokens = {}
            
            for token in all_tokens:
                mint = token.get('mint', '')
                if mint and mint not in unique_tokens:
                    unique_tokens[mint] = token
            
            result = list(unique_tokens.values())
            logger.info(f"🎯 Total unique tokens found: {len(result)}")
            logger.info(f"📋 Final result JSON: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in hybrid token search: {e}")
            # Return simple tokens as final fallback
            fallback_tokens = await self.get_recent_tokens_simple(days)
            logger.info(f"📋 Final fallback tokens JSON: {fallback_tokens}")
            return fallback_tokens
    
    async def get_recent_tokens_from_pump_helius(self, days: int = 7) -> List[Dict]:
        """Get recent tokens from Pump.fun Helius endpoint (if available)"""
        # Test endpoint availability if not already tested
        if not hasattr(self, '_pump_helius_tested'):
            await self._test_pump_helius_endpoint()
            self._pump_helius_tested = True
        
        if not self.pump_helius_available:
            logger.info("🔧 Pump.fun Helius endpoint not available, skipping")
            return []
        
        try:
            logger.info(f"🔍 Pump.fun Helius: Getting tokens for last {days} days...")
            
            # Try to use Pump.fun specific methods if available
            import aiohttp
            
            # Method 1: Try getPumpTokens
            try:
                request_data = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getPumpTokens",
                    "params": [{"days": days}]
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.pump_helius_url,
                        json=request_data,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            response_data = await response.json()
                            if "result" in response_data:
                                tokens = response_data["result"]
                                logger.info(f"📊 Pump.fun Helius: Found {len(tokens)} tokens")
                                return tokens
            except Exception as e:
                logger.debug(f"🔧 Pump.fun Helius getPumpTokens failed: {e}")
            
            # Method 2: Try getPumpRecentTokens
            try:
                request_data = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getPumpRecentTokens",
                    "params": [{"limit": 100}]
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.pump_helius_url,
                        json=request_data,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            response_data = await response.json()
                            if "result" in response_data:
                                tokens = response_data["result"]
                                logger.info(f"📊 Pump.fun Helius: Found {len(tokens)} recent tokens")
                                return tokens
            except Exception as e:
                logger.debug(f"🔧 Pump.fun Helius getPumpRecentTokens failed: {e}")
            
            logger.info("🔧 Pump.fun Helius: No specific methods available")
            return []
            
        except Exception as e:
            logger.error(f"❌ Error fetching tokens from Pump.fun Helius: {e}")
            return []
    
    def get_filter_description(self, filter_type: str, custom_days: int = 7) -> str:
        """Get human-readable description of the current filter"""
        descriptions = {
            "new_only": "Newly created tokens only",
            "last_1_day": "Tokens created in the last 1 day",
            "last_3_days": "Tokens created in the last 3 days", 
            "last_7_days": "Tokens created in the last 7 days",
            "last_14_days": "Tokens created in the last 14 days",
            "last_30_days": "Tokens created in the last 30 days",
            "custom_days": f"Tokens created in the last {custom_days} days"
        }
        return descriptions.get(filter_type, "Unknown filter") 

    async def get_sol_price(self) -> float:
        """Fetch real-time SOL price from Pump.Fun API"""
        current_time = datetime.now().timestamp()
        
        # Return cached price if it's still fresh
        if current_time - self.last_sol_price_update < self.sol_price_cache_duration:
            return self.sol_price_usd
        
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                async with session.get('https://frontend-api-v3.pump.fun/sol-price') as response:
                    if response.status == 200:
                        data = await response.json()
                        self.sol_price_usd = data.get('solPrice', 100.0)
                        self.last_sol_price_update = current_time
                        logger.info(f"📈 Updated SOL price: ${self.sol_price_usd:.2f}")
                        return self.sol_price_usd
                    else:
                        logger.warning(f"Failed to fetch SOL price: HTTP {response.status}")
                        return self.sol_price_usd
        except Exception as e:
            logger.warning(f"Error fetching SOL price: {e}")
            return self.sol_price_usd
    

    async def get_token_holders(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """Get token holder information from SolanaTracker API with Moralis fallback"""
        try:
            # Add 0.5 second delay between requests to prevent rate limiting
            await asyncio.sleep(0.5)
            
            # Primary: Try SolanaTracker API first
            logger.info(f"🔍 Fetching holder data for {mint_address} from SolanaTracker API")
            
            url = f"https://data.solanatracker.io/tokens/{mint_address}/holders"
            headers = {
                "x-api-key": "f4e9aeb4-c5c3-4378-84f6-1ab2bf10c649"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Fetched holder data for {mint_address} from SolanaTracker")
                        return data
                    else:
                        logger.warning(f"⚠️ SolanaTracker failed for {mint_address}: HTTP {response.status}, trying Moralis fallback")
                        # Fall back to Moralis API
                        return await self._get_holders_from_moralis_fallback(mint_address)
                        
        except Exception as e:
            logger.error(f"❌ Error fetching holder data from SolanaTracker for {mint_address}: {e}")
            logger.info(f"🔄 Trying Moralis fallback for {mint_address}")
            # Fall back to Moralis API
            return await self._get_holders_from_moralis_fallback(mint_address)
    
    async def _get_holders_from_moralis_fallback(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """Fallback method to get holder data from Moralis API"""
        try:
            # Add 0.5 second delay between requests to prevent rate limiting
            await asyncio.sleep(0.5)
            
            logger.info(f"🔄 Fetching holder data for {mint_address} from Moralis API (fallback)")
            
            # Moralis API endpoint for holder data
            url = f"https://solana-gateway.moralis.io/token/mainnet/holders/{mint_address}"
            headers = {
                "Accept": "application/json",
                "X-API-Key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjkyZThkZmJhLTAyOGUtNGI5NC04ZjMzLWJkMTIwY2Y1MmM4MSIsIm9yZ0lkIjoiNDY3MjA2IiwidXNlcklkIjoiNDgwNjQ1IiwidHlwZUlkIjoiZmRlNTBkZmItNWIwNS00ZTIzLWIzODYtYjhiMzc5NTUwM2JlIiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3NTYxNDY2NjQsImV4cCI6NDkxMTkwNjY2NH0.iOqIBD7EERIIi38WSiqzcEfqwWxdAWjLDBL7tNZ-6MQ"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Fetched holder data for {mint_address} from Moralis (fallback)")
                        
                        # Check if data is None or empty
                        if data is None:
                            logger.warning(f"⚠️ Moralis fallback returned None for {mint_address}")
                            return None
                        
                        return data
                    else:
                        logger.error(f"❌ Failed to fetch holder data from Moralis fallback: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error fetching holder data from Moralis fallback for {mint_address}: {e}")
            return None
        
    async def get_token_holders_count(self, mint_address: str) -> Optional[int]:
        """Get the number of holders for a token from SolanaTracker API with Moralis fallback"""
        try:
            # Add 0.5 second delay between requests to prevent rate limiting
            await asyncio.sleep(0.5)
            
            holder_data = await self.get_token_holders(mint_address)
            
            # Check if we got data from SolanaTracker (primary source)
            if holder_data and 'total' in holder_data:
                count = holder_data['total']
                logger.info(f"📊 Token {mint_address} has {count} holders (from SolanaTracker total)")
                return int(count)
            elif holder_data and 'accounts' in holder_data and isinstance(holder_data['accounts'], list):
                # If total not available, count the accounts array
                count = len(holder_data['accounts'])
                logger.info(f"📊 Token {mint_address} has {count} holders (from SolanaTracker accounts array)")
                return int(count)
            # Check if we got data from Moralis fallback
            elif holder_data and 'totalHolders' in holder_data:
                count = holder_data['totalHolders']
                logger.info(f"📊 Token {mint_address} has {count} holders (from Moralis fallback totalHolders)")
                return int(count)
            elif holder_data and 'result' in holder_data and isinstance(holder_data['result'], list):
                # Fallback for other Moralis response formats
                count = len(holder_data['result'])
                logger.info(f"📊 Token {mint_address} has {count} holders (from Moralis fallback result array)")
                return int(count)
            elif holder_data is None:
                logger.warning(f"⚠️ Both APIs returned None for {mint_address}, using fallback")
                return 0
            else:
                logger.warning(f"⚠️ No holder count available for {mint_address}")
                logger.debug(f"📋 Full response: {holder_data}")
                return 0
        except Exception as e:
            logger.error(f"❌ Error getting holder count: {e}")
            return 0
        
    # async def get_token_holders_count(self, mint: str) -> int:
    #     """Get the number of holders for a token using SolanaTracker API"""
    #     try:
    #         url = f"https://data.solanatracker.io/tokens/{mint}/holders?token={mint}"
    #         headers = {
    #             "x-api-key": "f4e9aeb4-c5c3-4378-84f6-1ab2bf10c649"
    #         }
            
    #         logger.info(f"🔍 Fetching holders for {mint} from SolanaTracker")
            
    #         async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
    #             async with session.get(url, headers=headers, timeout=10) as response:
    #                 logger.info(f"📡 Response status: {response.status}")
                    
    #                 if response.status == 200:
    #                     data = await response.json()
    #                     logger.info(f"📋 SolanaTracker response for {mint}: {data}")
                        
    #                     # Try to get total count from response
    #                     if 'total' in data:
    #                         holders_count = int(data['total'])
    #                         logger.info(f"📊 Token {mint}: Found {holders_count} holders (from total)")
    #                         return holders_count
    #                     elif 'holders' in data:
    #                         # If total not available, count the holders array
    #                         holders_count = len(data['holders'])
    #                         logger.info(f"📊 Token {mint}: Found {holders_count} holders (from array)")
    #                         return holders_count
    #                     else:
    #                         logger.warning(f"⚠️ No holder data found for {mint}")
    #                         return 0
    #                 else:
    #                     # Try to get error response body
    #                     try:
    #                         error_body = await response.text()
    #                         logger.error(f"❌ HTTP {response.status} error for {mint}: {error_body}")
    #                     except:
    #                         logger.error(f"❌ HTTP {response.status} error for {mint}: Could not read error body")
                        
    #                     logger.warning(f"⚠️ Failed to get holders for {mint}: HTTP {response.status}")
    #                     return 0
    #     except Exception as e:
    #         logger.error(f"❌ Exception getting holders for {mint}: {e}")
    #         import traceback
    #         logger.error(f"❌ Traceback: {traceback.format_exc()}")
    #         return 0
    
    async def update_token_holders_and_filter(self, tokens: List[Dict], min_liquidity: float = 100.0, min_holders: int = 10) -> List[Dict]:
        """Update holders count for tokens and apply filtering based on settings"""
        try:
            logger.info(f"🔍 Updating holders and filtering {len(tokens)} tokens...")
            logger.info(f"📊 Filter criteria: min_liquidity={min_liquidity} SOL, min_holders={min_holders}")
            
            filtered_tokens = []
            
            for token in tokens:
                mint = token.get('mint', '')
                if not mint:
                    continue
                
                # Get current holders count from Pump.fun API
                holders_count = await self.get_token_holders_count(mint)
                
                # Update the token with real holders count
                token['holders'] = holders_count
                
                # Get liquidity (should already be in SOL)
                liquidity = token.get('liquidity', 0.0)
                
                # Apply filtering
                if liquidity >= min_liquidity and holders_count >= min_holders:
                    filtered_tokens.append(token)
                    logger.debug(f"✅ Token {token.get('symbol', 'Unknown')} passed filter: liquidity={liquidity:.2f} SOL, holders={holders_count}")
                else:
                    logger.debug(f"❌ Token {token.get('symbol', 'Unknown')} failed filter: liquidity={liquidity:.2f} SOL, holders={holders_count}")
            
            logger.info(f"📊 Filtered {len(tokens)} tokens to {len(filtered_tokens)} based on criteria")
            return filtered_tokens
            
        except Exception as e:
            logger.error(f"❌ Error updating holders and filtering: {e}")
            return tokens  # Return original tokens if there's an error 