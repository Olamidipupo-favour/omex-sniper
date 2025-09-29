"""
Data models and schemas for the Omex Coin Sniper API
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

class TradeAction(str, Enum):
    BUY = "buy"
    SELL = "sell"

class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class TokenInfo:
    """Token information model"""
    mint: str
    symbol: str
    name: str
    price: float
    market_cap: float
    liquidity: float
    holders: int
    created_timestamp: int
    is_on_pump: bool
    source: str
    description: Optional[str] = None
    image_uri: Optional[str] = None
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    website: Optional[str] = None

@dataclass
class Position:
    """Trading position model"""
    mint: str
    symbol: str
    entry_price: float
    current_price: float
    sol_amount: float
    token_amount: float
    pnl: float
    pnl_percent: float
    entry_time: datetime
    is_active: bool

@dataclass
class TradeRequest:
    """Trade request model"""
    mint: str
    amount: float
    action: str  # 'buy' or 'sell'
    slippage: Optional[float] = 5.0
    priority_fee: Optional[float] = 0.0001

@dataclass
class TradeResponse:
    """Trade response model"""
    success: bool
    signature: Optional[str] = None
    amount: Optional[float] = None
    price: Optional[float] = None
    message: Optional[str] = None

@dataclass
class SniperConfig:
    """Sniper configuration model"""
    sol_per_snipe: float
    max_positions: int
    profit_target_percent: float
    stop_loss_percent: float
    min_market_cap: float
    max_market_cap: float
    min_liquidity: float
    min_holders: int
    auto_buy: bool
    auto_sell: bool

@dataclass
class HealthStatus:
    """Health status model"""
    status: str
    timestamp: datetime
    version: str
    uptime: float
    wallet_connected: bool
    monitoring_active: bool
    active_positions: int

@dataclass
class ErrorResponse:
    """Error response model"""
    error: str
    code: Optional[str] = None
    details: Optional[str] = None

@dataclass
class MonitoringConfig:
    """Monitoring configuration model"""
    enabled: bool
    min_market_cap: float
    max_market_cap: float
    min_liquidity: float
    min_holders: int
    auto_buy: bool
    auto_sell: bool
    profit_target: float
    stop_loss: float

@dataclass
class WalletInfo:
    """Wallet information model"""
    address: str
    balance: float
    connected: bool
    last_updated: datetime

@dataclass
class TradeHistory:
    """Trade history model"""
    signature: str
    mint: str
    action: str
    amount: float
    price: float
    timestamp: datetime
    success: bool
    message: Optional[str] = None

@dataclass
class MarketData:
    """Market data model"""
    token: TokenInfo
    volume_24h: float
    price_change_24h: float
    price_change_percent_24h: float
    last_updated: datetime

@dataclass
class SniperStats:
    """Sniper statistics model"""
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_pnl: float
    total_pnl_percent: float
    active_positions: int
    closed_positions: int
    best_trade_pnl: float
    worst_trade_pnl: float
    average_hold_time: float  # in hours
