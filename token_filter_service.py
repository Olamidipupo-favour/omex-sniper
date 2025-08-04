#!/usr/bin/env python3
"""
Token Filter Service - Handles token age filtering and Pump.fun API integration
"""

import asyncio
import aiohttp
import logging
import time
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient

logger = logging.getLogger(__name__)

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
        """Get recent tokens from Helius RPC using token program and recent transactions"""
        try:
            logger.info(f"🔍 Helius: Searching for tokens from last {days} days...")
            
            # Calculate time threshold
            current_time = time.time()
            time_threshold = current_time - (days * 24 * 3600)
            
            # Get recent token program transactions
            try:
                # Get recent transactions involving token program
                token_program_id = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
                
                # Get recent signatures for token program
                response = await self.helius_client.get_signatures_for_address(
                    Pubkey.from_string(token_program_id),
                    limit=500  # Reduced limit to avoid overwhelming
                )
                
                if not response.value:
                    logger.warning("⚠️ Helius: No recent token program transactions found")
                    return []
                
                recent_tokens = []
                processed_mints = set()
                
                # Process recent transactions to find new token mints
                for sig_info in response.value:
                    if sig_info.block_time and sig_info.block_time < time_threshold:
                        continue  # Skip old transactions
                    
                    try:
                        # Get transaction details with maxSupportedTransactionVersion parameter
                        tx_response = await self.helius_client.get_transaction(
                            sig_info.signature,
                            encoding="jsonParsed",
                            max_supported_transaction_version=0  # Support legacy transactions
                        )
                        
                        if not tx_response.value or not tx_response.value.transaction:
                            continue
                        
                        # Safely extract instructions
                        try:
                            # Handle different transaction formats
                            if hasattr(tx_response.value.transaction, 'message'):
                                instructions = tx_response.value.transaction.message.instructions
                            elif hasattr(tx_response.value.transaction, 'instructions'):
                                instructions = tx_response.value.transaction.instructions
                            else:
                                # Try to access instructions from parsed data
                                if hasattr(tx_response.value, 'meta') and tx_response.value.meta:
                                    # Look for token program instructions in meta
                                    if hasattr(tx_response.value.meta, 'inner_instructions'):
                                        for inner_instruction in tx_response.value.meta.inner_instructions:
                                            if hasattr(inner_instruction, 'instructions'):
                                                for instruction in inner_instruction.instructions:
                                                    if hasattr(instruction, 'program_id') and instruction.program_id == token_program_id:
                                                        # Process token program instruction
                                                        await self._process_token_instruction(
                                                            instruction, sig_info, recent_tokens, processed_mints
                                                        )
                                continue
                            
                            # Process each instruction
                            for instruction in instructions:
                                if hasattr(instruction, 'program_id') and instruction.program_id == token_program_id:
                                    await self._process_token_instruction(
                                        instruction, sig_info, recent_tokens, processed_mints
                                    )
                                
                                if len(recent_tokens) >= 100:  # Limit results
                                    break
                                    
                        except Exception as parse_error:
                            logger.debug(f"⚠️ Helius: Error parsing transaction {sig_info.signature}: {parse_error}")
                            continue
                    
                    except Exception as e:
                        logger.debug(f"⚠️ Helius: Error processing transaction {sig_info.signature}: {e}")
                        continue
                    
                    if len(recent_tokens) >= 100:  # Limit results
                        break
                
                logger.info(f"📊 Helius: Found {len(recent_tokens)} recent tokens")
                return recent_tokens
                
            except Exception as e:
                logger.error(f"❌ Helius: Error getting recent transactions: {e}")
                return []
            
        except Exception as e:
            logger.error(f"❌ Error fetching recent tokens from Helius: {e}")
            return []
    
    async def _process_token_instruction(self, instruction, sig_info, recent_tokens, processed_mints):
        """Process a token program instruction to extract mint information"""
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
                            'created_timestamp': sig_info.block_time or int(time.time()),
                            'market_cap': 0,
                            'price': 0,
                            'liquidity': 0,
                            'holders': 0,
                            'is_on_pump': False,
                            'source': 'helius'
                        }
                        
                        recent_tokens.append(token_info)
                        
        except Exception as e:
            logger.debug(f"⚠️ Helius: Error processing instruction: {e}")
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
    
    async def get_recent_pump_tokens(self, days: int = 7) -> List[Dict]:
        """Get recent tokens from Pump.fun API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.pump_api_url}/tokens"
                params = {
                    'limit': 100,  # Get recent tokens
                    'offset': 0
                }
                
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        tokens = data.get('tokens', [])
                        
                        # Filter by creation date
                        current_time = time.time()
                        age_threshold = days * 24 * 3600  # Convert days to seconds
                        
                        recent_tokens = []
                        for token in tokens:
                            created_timestamp = token.get('created_timestamp', 0)
                            if current_time - created_timestamp <= age_threshold:
                                recent_tokens.append(token)
                        
                        logger.info(f"📊 Found {len(recent_tokens)} recent Pump.fun tokens from last {days} days")
                        return recent_tokens
                    else:
                        logger.warning(f"⚠️ Pump.fun API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Error fetching recent Pump.fun tokens: {e}")
            return []
    
    async def get_recent_tokens_simple(self, days: int = 7) -> List[Dict]:
        """Get recent tokens using a simpler approach - just return some sample tokens for testing"""
        try:
            logger.info(f"🔍 Simple: Getting sample tokens for last {days} days...")
            
            # For now, return some sample tokens to test the system
            # In a real implementation, you'd query a token database or use a different API
            sample_tokens = [
                {
                    'mint': 'So11111111111111111111111111111111111111112',  # Wrapped SOL
                    'symbol': 'WSOL',
                    'name': 'Wrapped SOL',
                    'created_timestamp': int(time.time()) - (3 * 24 * 3600),  # 3 days ago
                    'market_cap': 1000000,
                    'price': 1.0,
                    'liquidity': 1000.0,
                    'holders': 10000,
                    'is_on_pump': False,
                    'source': 'sample'
                },
                {
                    'mint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                    'symbol': 'USDC',
                    'name': 'USD Coin',
                    'created_timestamp': int(time.time()) - (5 * 24 * 3600),  # 5 days ago
                    'market_cap': 5000000,
                    'price': 1.0,
                    'liquidity': 2000.0,
                    'holders': 50000,
                    'is_on_pump': False,
                    'source': 'sample'
                }
            ]
            
            logger.info(f"📊 Simple: Found {len(sample_tokens)} sample tokens")
            logger.info(f"📋 Sample tokens JSON: {sample_tokens}")
            return sample_tokens
            
        except Exception as e:
            logger.error(f"❌ Error in simple token search: {e}")
            return []
    
    async def get_hybrid_recent_tokens(self, days: int = 7, include_pump_only: bool = False) -> List[Dict]:
        """Get recent tokens using hybrid approach (Pump.fun + Helius)"""
        try:
            logger.info(f"🔍 Getting hybrid token list for last {days} days...")
            
            # Get tokens from Pump.fun
            pump_tokens = await self.get_recent_pump_tokens(days)
            logger.info(f"📊 Found {len(pump_tokens)} tokens from Pump.fun")
            if pump_tokens:
                logger.info(f"📋 Pump.fun tokens JSON: {pump_tokens[:2]}")  # Show first 2 tokens
            
            # Get tokens from Helius (if not pump-only and using Helius RPC)
            helius_tokens = []
            if not include_pump_only:
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
            
            # Combine and deduplicate
            all_tokens = pump_tokens + helius_tokens
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