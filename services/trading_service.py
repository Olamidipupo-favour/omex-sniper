"""
Trading Service - Handles buy/sell operations
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from models.schemas import Position, TradeRequest, TradeResponse
from core.pump_trader import PumpPortalTrader
from services.config_service import ConfigService

logger = logging.getLogger(__name__)

class TradingService:
    """Service for executing trades and managing positions"""
    
    def __init__(self):
        self.trader = PumpPortalTrader()
        self.config_service = ConfigService()
        self.positions = {}
        
    def get_positions(self) -> List[Position]:
        """Get all current positions"""
        return list(self.positions.values())
    
    def get_position(self, mint: str) -> Optional[Position]:
        """Get a specific position by mint address"""
        return self.positions.get(mint)
    
    def execute_trade(self, trade_request: TradeRequest) -> TradeResponse:
        """Execute a trade (buy or sell)"""
        try:
            if not self.config_service.is_wallet_connected():
                return TradeResponse(
                    success=False,
                    message="Wallet not connected"
                )
            
            if trade_request.action == 'buy':
                return self._execute_buy(trade_request)
            elif trade_request.action == 'sell':
                return self._execute_sell(trade_request)
            else:
                return TradeResponse(
                    success=False,
                    message="Invalid trade action"
                )
                
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return TradeResponse(
                success=False,
                message=f"Trade failed: {str(e)}"
            )
    
    def _execute_buy(self, trade_request: TradeRequest) -> TradeResponse:
        """Execute a buy order"""
        try:
            # Check if we already have a position for this token
            if trade_request.mint in self.positions:
                return TradeResponse(
                    success=False,
                    message="Position already exists for this token"
                )
            
            # Execute the buy order
            success, signature, token_amount = asyncio.run(
                self.trader.buy_token(
                    trade_request.mint,
                    trade_request.amount,
                    trade_request.slippage or 5.0,
                    "local",
                    trade_request.priority_fee or 0.0001
                )
            )
            
            if success:
                # Create new position
                position = Position(
                    mint=trade_request.mint,
                    symbol="",  # Will be updated when we get token info
                    entry_price=0.0,  # Will be calculated
                    current_price=0.0,
                    sol_amount=trade_request.amount,
                    token_amount=token_amount,
                    pnl=0.0,
                    pnl_percent=0.0,
                    entry_time=datetime.utcnow(),
                    is_active=True
                )
                
                self.positions[trade_request.mint] = position
                
                return TradeResponse(
                    success=True,
                    signature=signature,
                    amount=token_amount,
                    price=0.0,  # Will be updated
                    message="Buy order executed successfully"
                )
            else:
                return TradeResponse(
                    success=False,
                    message="Buy order failed"
                )
                
        except Exception as e:
            logger.error(f"Buy execution failed: {e}")
            return TradeResponse(
                success=False,
                message=f"Buy failed: {str(e)}"
            )
    
    def _execute_sell(self, trade_request: TradeRequest) -> TradeResponse:
        """Execute a sell order"""
        try:
            # Check if we have a position for this token
            if trade_request.mint not in self.positions:
                return TradeResponse(
                    success=False,
                    message="No position found for this token"
                )
            
            position = self.positions[trade_request.mint]
            
            # Execute the sell order
            success, signature, sol_received = asyncio.run(
                self.trader.sell_token(
                    trade_request.mint,
                    trade_request.amount,
                    trade_request.slippage or 5.0,
                    "local",
                    trade_request.priority_fee or 0.0001
                )
            )
            
            if success:
                # Update position
                position.is_active = False
                position.pnl = sol_received - position.sol_amount
                position.pnl_percent = (position.pnl / position.sol_amount) * 100
                
                return TradeResponse(
                    success=True,
                    signature=signature,
                    amount=sol_received,
                    price=0.0,  # Will be calculated
                    message="Sell order executed successfully"
                )
            else:
                return TradeResponse(
                    success=False,
                    message="Sell order failed"
                )
                
        except Exception as e:
            logger.error(f"Sell execution failed: {e}")
            return TradeResponse(
                success=False,
                message=f"Sell failed: {str(e)}"
            )
    
    def close_position(self, mint: str) -> bool:
        """Close a specific position"""
        try:
            if mint not in self.positions:
                logger.warning(f"No position found for token {mint}")
                return False
            
            position = self.positions[mint]
            
            # Execute sell for the full token amount
            trade_request = TradeRequest(
                mint=mint,
                amount=position.token_amount,
                action='sell'
            )
            
            result = self.execute_trade(trade_request)
            return result.success
            
        except Exception as e:
            logger.error(f"Failed to close position {mint}: {e}")
            return False
    
    def update_position_prices(self, mint: str, current_price: float):
        """Update position with current price"""
        try:
            if mint in self.positions:
                position = self.positions[mint]
                position.current_price = current_price
                
                # Calculate P&L
                if position.entry_price > 0:
                    position.pnl = (current_price - position.entry_price) * position.token_amount
                    position.pnl_percent = ((current_price - position.entry_price) / position.entry_price) * 100
                
        except Exception as e:
            logger.error(f"Failed to update position prices for {mint}: {e}")
    
    def get_total_pnl(self) -> Dict:
        """Get total P&L across all positions"""
        try:
            total_pnl = 0.0
            total_invested = 0.0
            active_positions = 0
            
            for position in self.positions.values():
                if position.is_active:
                    total_pnl += position.pnl
                    total_invested += position.sol_amount
                    active_positions += 1
            
            total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0
            
            return {
                'total_pnl': total_pnl,
                'total_pnl_percent': total_pnl_percent,
                'total_invested': total_invested,
                'active_positions': active_positions
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate total P&L: {e}")
            return {
                'total_pnl': 0.0,
                'total_pnl_percent': 0.0,
                'total_invested': 0.0,
                'active_positions': 0
            }
