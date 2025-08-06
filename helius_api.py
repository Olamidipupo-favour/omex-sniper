#!/usr/bin/env python3
"""
Helius API Integration - Fetch wallet positions and transaction history
"""

import aiohttp
import logging
import asyncio
from typing import List, Dict, Any, Optional
from config import HELIUS_API_KEY
import json
import time

logger = logging.getLogger(__name__)

class HeliusAPI:
    """Helius API client for wallet data"""
    
    def __init__(self, api_key: str = HELIUS_API_KEY):
        self.api_key = api_key
        self.base_url = "https://api.helius.xyz/v0"
        
    async def get_wallet_token_balances(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Get all token balances for a wallet using Helius DAS API"""
        try:
            url = f"https://mainnet.helius-rpc.com/?api-key={self.api_key}"
            
            items = []
            cursor = None
            limit = 100

            while True:
                payload = {
                    "jsonrpc": "2.0",
                    "id": "searchAssets",
                    "method": "searchAssets",
                    "params": {
                        "ownerAddress": wallet_address,
                        "tokenType": "fungible",
                        "limit": limit,
                        **({"cursor": cursor} if cursor else {})
                    }
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload) as response:
                        if response.status == 200:
                            result = (await response.json())["result"]
                        else:
                            logger.error(f"❌ Failed to fetch token balances: {response.status}")
                            return []
                
                assets = result.get("items", [])
                items.extend(assets)
                cursor = result.get("cursor")
                
                if not cursor or len(assets) < limit:
                    break

            logger.info(f"✅ Fetched {len(items)} token balances for wallet {wallet_address}")
            logger.info(f"Items: {items}")
            return items
                        
        except Exception as e:
            logger.error(f"❌ Error fetching token balances: {e}")
            return []
    
    async def get_wallet_transactions(self, wallet_address: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transaction history for a wallet"""
        try:
            url = f"{self.base_url}/addresses/{wallet_address}/transactions?api-key={self.api_key}&limit={limit}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Fetched {len(data)} transactions for wallet {wallet_address}")
                        return data
                    else:
                        logger.error(f"❌ Failed to fetch transactions: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Error fetching transactions: {e}")
            return []
    
    async def get_token_metadata(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """Get token metadata including price and market data"""
        try:
            url = f"{self.base_url}/token-metadata?api-key={self.api_key}"
            
            payload = {
                "mintAccounts": [mint_address],
                "includeOffChain": True,
                "disableCache": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            logger.info(f"✅ Fetched metadata for token {mint_address}")
                            return data[0]
                    else:
                        logger.error(f"❌ Failed to fetch token metadata: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error fetching token metadata: {e}")
            return None
    
    async def get_token_price(self, mint_address: str) -> Optional[float]:
        """Get current token price in USD using SolanaTracker API"""
        try:
            # SolanaTracker API endpoint for price data
            url = f"https://data.solanatracker.io/price?token={mint_address}"
            headers = {
                "x-api-key": "f4e9aeb4-c5c3-4378-84f6-1ab2bf10c649"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'price' in data:
                            price = data['price']
                            logger.info(f"✅ Fetched price from SolanaTracker: ${price}")
                            return float(price)
                        else:
                            logger.warning(f"⚠️ No price data in response for {mint_address}")
                            return None
                    else:
                        logger.error(f"❌ Failed to fetch price from SolanaTracker: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error fetching price from SolanaTracker: {e}")
            return None
    
    async def get_token_price_from_jupiter(self, mint_address: str) -> Optional[float]:
        """Get token price from Jupiter API (alternative method)"""
        try:
            # Jupiter API endpoint for price data
            url = f"https://price.jup.ag/v4/price?ids={mint_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'data' in data and mint_address in data['data']:
                            price = data['data'][mint_address].get('price', 0)
                            logger.info(f"✅ Fetched price from Jupiter: ${price}")
                            return float(price)
                    else:
                        logger.error(f"❌ Failed to fetch price from Jupiter: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error fetching price from Jupiter: {e}")
            return None
    
    async def get_token_price_websocket(self, mint_address: str) -> Optional[float]:
        """Get current token price using WebSocket for real-time updates"""
        try:
            # For now, we'll use the existing get_token_price method
            # In the future, you could implement a WebSocket connection to a price feed
            return await self.get_token_price(mint_address)
        except Exception as e:
            logger.error(f"❌ Error fetching token price via WebSocket: {e}")
            return None
    
    async def monitor_token_price(self, mint_address: str, callback=None, interval: int = 5):
        """Monitor token price continuously for P&L tracking (default 5 seconds)"""
        import asyncio
        
        while True:
            try:
                price = await self.get_token_price(mint_address)
                if price is not None:
                    logger.info(f"💰 Price for {mint_address}: ${price}")
                    if callback:
                        await callback(mint_address, price)
                else:
                    logger.warning(f"⚠️ Could not fetch price for {mint_address}")
                
                await asyncio.sleep(interval)  # Check every 5 seconds by default
                
            except Exception as e:
                logger.error(f"❌ Error monitoring price for {mint_address}: {e}")
                await asyncio.sleep(interval)
    
    async def calculate_pnl(self, entry_price: float, current_price: float, token_amount: float) -> Dict[str, float]:
        """Calculate P&L for a position"""
        try:
            current_value = current_price * token_amount
            entry_value = entry_price * token_amount
            pnl_absolute = current_value - entry_value
            pnl_percentage = (pnl_absolute / entry_value) * 100 if entry_value > 0 else 0
            
            return {
                'entry_price': entry_price,
                'current_price': current_price,
                'token_amount': token_amount,
                'entry_value': entry_value,
                'current_value': current_value,
                'pnl_absolute': pnl_absolute,
                'pnl_percentage': pnl_percentage
            }
        except Exception as e:
            logger.error(f"❌ Error calculating P&L: {e}")
            return {}
    
    async def get_token_account_balance(self, token_account_address: str) -> Optional[Dict[str, Any]]:
        """Get balance for a specific token account using RPC"""
        try:
            url = f"https://mainnet.helius-rpc.com/?api-key={self.api_key}"
            
            payload = {
                "jsonrpc": "2.0",
                "id": "getTokenAccountBalance",
                "method": "getTokenAccountBalance",
                "params": [token_account_address]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Fetched token account balance for {token_account_address}")
                        return data.get("result", {})
                    else:
                        logger.error(f"❌ Failed to fetch token account balance: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error fetching token account balance: {e}")
            return None
    
    async def get_token_accounts_by_owner(self, owner_address: str, program_id: str = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA") -> List[Dict[str, Any]]:
        """List all token accounts owned by a wallet"""
        try:
            url = f"https://mainnet.helius-rpc.com/?api-key={self.api_key}"
            
            payload = {
                "jsonrpc": "2.0",
                "id": "getTokenAccountsByOwner",
                "method": "getTokenAccountsByOwner",
                "params": [
                    owner_address,
                    {
                        "programId": program_id
                    },
                    {
                        "encoding": "jsonParsed"
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = data.get("result", {})
                        accounts = result.get("value", [])
                        logger.info(f"✅ Fetched {len(accounts)} token accounts for owner {owner_address}")
                        return accounts
                    else:
                        logger.error(f"❌ Failed to fetch token accounts by owner: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Error fetching token accounts by owner: {e}")
            return []
    
    async def get_token_accounts_by_mint(self, mint_address: str, owner_address: str) -> List[Dict[str, Any]]:
        """List all accounts holding a specific token for a given owner"""
        try:
            url = f"https://mainnet.helius-rpc.com/?api-key={self.api_key}"
            
            payload = {
                "jsonrpc": "2.0",
                "id": "getTokenAccountsByMint",
                "method": "getTokenAccountsByOwner",
                "params": [
                    owner_address,
                    {
                        "mint": mint_address
                    },
                    {
                        "encoding": "jsonParsed"
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = data.get("result", {})
                        accounts = result.get("value", [])
                        logger.info(f"✅ Fetched {len(accounts)} token accounts for mint {mint_address}")
                        return accounts
                    else:
                        logger.error(f"❌ Failed to fetch token accounts by mint: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Error fetching token accounts by mint: {e}")
            return []
    
    async def get_token_supply(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """Check the total supply of a token"""
        try:
            url = f"https://mainnet.helius-rpc.com/?api-key={self.api_key}"
            
            payload = {
                "jsonrpc": "2.0",
                "id": "getTokenSupply",
                "method": "getTokenSupply",
                "params": [mint_address]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Fetched token supply for {mint_address}")
                        return data.get("result", {})
                    else:
                        logger.error(f"❌ Failed to fetch token supply: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error fetching token supply: {e}")
            return None
    
    async def get_token_largest_accounts(self, mint_address: str) -> List[Dict[str, Any]]:
        """Identify the largest accounts holding a token"""
        try:
            url = f"https://mainnet.helius-rpc.com/?api-key={self.api_key}"
            
            payload = {
                "jsonrpc": "2.0",
                "id": "getTokenLargestAccounts",
                "method": "getTokenLargestAccounts",
                "params": [mint_address]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = data.get("result", {})
                        accounts = result.get("value", [])
                        logger.info(f"✅ Fetched {len(accounts)} largest accounts for mint {mint_address}")
                        return accounts
                    else:
                        logger.error(f"❌ Failed to fetch token largest accounts: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Error fetching token largest accounts: {e}")
            return []
    
    async def get_asset(self, asset_id: str, show_fungible: bool = True) -> Optional[Dict[str, Any]]:
        """Get comprehensive asset information including metadata using DAS API"""
        try:
            url = f"https://mainnet.helius-rpc.com/?api-key={self.api_key}"
            
            payload = {
                "jsonrpc": "2.0",
                "id": "getAsset",
                "method": "getAsset",
                "params": {
                    "id": asset_id,
                    "options": {
                        "showFungible": show_fungible
                    }
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Fetched asset information for {asset_id}")
                        return data.get("result", {})
                    else:
                        logger.error(f"❌ Failed to fetch asset: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error fetching asset: {e}")
            return None
    
    def parse_transaction_for_bot(self, tx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse transaction for bot display"""
        try:
            # Extract relevant transaction data
            signature = tx.get('signature', '')
            timestamp = tx.get('timestamp', 0)
            fee = tx.get('fee', 0)
            
            # Look for token transfers
            token_transfers = tx.get('tokenTransfers', [])
            native_transfers = tx.get('nativeTransfers', [])
            
            # Determine transaction type
            tx_type = 'unknown'
            amount = 0
            token_mint = ''
            token_symbol = ''
            
            if token_transfers:
                tx_type = 'token_transfer'
                for transfer in token_transfers:
                    amount = transfer.get('amount', 0)
                    token_mint = transfer.get('mint', '')
                    token_symbol = transfer.get('tokenName', '')
                    break
            elif native_transfers:
                tx_type = 'sol_transfer'
                for transfer in native_transfers:
                    amount = transfer.get('amount', 0) / 1e9  # Convert lamports to SOL
                    break
            
            return {
                'signature': signature,
                'timestamp': timestamp,
                'type': tx_type,
                'amount': amount,
                'token_mint': token_mint,
                'token_symbol': token_symbol,
                'fee': fee / 1e9,  # Convert lamports to SOL
                'raw_data': tx
            }
            
        except Exception as e:
            logger.error(f"❌ Error parsing transaction: {e}")
            return None
    
    def parse_token_balance_for_position(self, balance: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse token balance for position display from DAS API response"""
        try:
            # Extract data from DAS API response structure
            mint = balance.get('id', '')  # Mint address is in 'id' field
            content = balance.get('content', {})
            metadata = content.get('metadata', {})
            token_info = balance.get('token_info', {})
            
            # Get balance and decimals from token_info
            raw_amount = token_info.get('balance', 0)
            decimals = token_info.get('decimals', 0)
            
            # Calculate UI amount (human-readable)
            token_amount = raw_amount / (10 ** decimals) if decimals > 0 else raw_amount
            
            # Get additional metadata from content.metadata
            symbol = metadata.get('symbol', 'Unknown')
            name = metadata.get('name', 'Unknown')
            
            # For now, we'll set price to 0 as it's not directly available in this response
            # You might need to fetch price separately using get_token_price method
            price = 0
            
            return {
                'mint': mint,
                'token_amount': token_amount,
                'decimals': decimals,
                'raw_amount': raw_amount,
                'symbol': symbol,
                'name': name,
                'price': price
            }
            
        except Exception as e:
            logger.error(f"❌ Error parsing token balance: {e}")
            return None 

    async def get_token_holders(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """Get token holder information from SolanaTracker API"""
        try:
            # SolanaTracker API endpoint for holder data
            url = f"https://data.solanatracker.io/tokens/{mint_address}/holders?token={mint_address}"
            headers = {
                "x-api-key": "f4e9aeb4-c5c3-4378-84f6-1ab2bf10c649"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Fetched holder data for {mint_address}")
                        return data
                    else:
                        logger.error(f"❌ Failed to fetch holder data: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error fetching holder data: {e}")
            return None
    
    async def get_token_holder_count(self, mint_address: str) -> Optional[int]:
        """Get the number of holders for a token"""
        try:
            holder_data = await self.get_token_holders(mint_address)
            if holder_data and 'total' in holder_data:
                count = holder_data['total']
                logger.info(f"📊 Token {mint_address} has {count} holders")
                return int(count)
            elif holder_data and 'holders' in holder_data:
                # If total not available, count the holders array
                count = len(holder_data['holders'])
                logger.info(f"📊 Token {mint_address} has {count} holders (from array)")
                return count
            else:
                logger.warning(f"⚠️ No holder count available for {mint_address}")
                return None
        except Exception as e:
            logger.error(f"❌ Error getting holder count: {e}")
            return None

    def should_sell_based_on_buy_count(self, mint: str, trade_history: List[Dict[str, Any]], required_buys: int = 3) -> bool:
        """Check if we should sell based on number of buys seen for a token"""
        try:
            buy_count = self.get_buy_count_for_token(mint, trade_history)
            return buy_count >= required_buys
        except Exception as e:
            logger.error(f"❌ Error checking buy count for {mint}: {e}")
            return False 

    def get_trade_count_for_token(self, mint: str, trade_history: List[Dict[str, Any]]) -> int:
        """Count the number of trades for a specific token"""
        return len([trade for trade in trade_history if trade.get('mint') == mint])
    
    def get_buy_count_for_token(self, mint: str, trade_history: List[Dict[str, Any]]) -> int:
        """Count the number of buy trades for a specific token"""
        return len([trade for trade in trade_history 
                   if trade.get('mint') == mint and trade.get('txType') == 'buy'])
    
    def get_sell_count_for_token(self, mint: str, trade_history: List[Dict[str, Any]]) -> int:
        """Count the number of sell trades for a specific token"""
        return len([trade for trade in trade_history 
                   if trade.get('mint') == mint and trade.get('txType') == 'sell']) 

    async def get_active_positions_from_trades(self, wallet_address: str, trade_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get active positions by analyzing trade history from PumpPortal WebSocket"""
        try:
            positions = {}
            
            # Process all trades for this wallet
            for trade in trade_history:
                if trade.get('traderPublicKey') != wallet_address:
                    continue
                
                mint = trade.get('mint')
                tx_type = trade.get('txType')
                token_amount = trade.get('tokenAmount', 0)
                
                if not mint or not tx_type:
                    continue
                
                # Initialize position if not exists
                if mint not in positions:
                    positions[mint] = {
                        'mint': mint,
                        'total_bought': 0,
                        'total_sold': 0,
                        'current_balance': 0,
                        'last_trade_time': 0,
                        'entry_price': 0,
                        'last_trade_price': 0
                    }
                
                position = positions[mint]
                
                if tx_type == 'buy':
                    position['total_bought'] += token_amount
                    position['current_balance'] += token_amount
                    position['entry_price'] = trade.get('marketCapSol', 0)  # Use market cap as price proxy
                elif tx_type == 'sell':
                    position['total_sold'] += token_amount
                    position['current_balance'] -= token_amount
                    position['last_trade_price'] = trade.get('marketCapSol', 0)
                
                position['last_trade_time'] = trade.get('timestamp', 0)
            
            # Filter to only active positions (positive balance)
            active_positions = []
            for mint, position in positions.items():
                if position['current_balance'] > 0:
                    # Get token metadata
                    metadata = await self.get_token_metadata(mint)
                    if metadata:
                        content = metadata.get('content', {})
                        token_metadata = content.get('metadata', {})
                        
                        active_positions.append({
                            'mint': mint,
                            'token_amount': position['current_balance'],
                            'token_name': token_metadata.get('name', 'Unknown'),
                            'token_symbol': token_metadata.get('symbol', 'Unknown'),
                            'entry_price': position['entry_price'],
                            'last_trade_price': position['last_trade_price'],
                            'total_bought': position['total_bought'],
                            'total_sold': position['total_sold'],
                            'last_trade_time': position['last_trade_time'],
                            'timestamp': int(time.time())
                        })
            
            logger.info(f"✅ Found {len(active_positions)} active positions from trade history")
            return active_positions
            
        except Exception as e:
            logger.error(f"❌ Error getting active positions from trades: {e}")
            return [] 