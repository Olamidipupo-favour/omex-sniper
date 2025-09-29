"""
Sniper Service - Core sniper bot functionality
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from models.schemas import HealthStatus, SniperConfig
from services.monitoring_service import MonitoringService
from services.trading_service import TradingService
from services.config_service import ConfigService

logger = logging.getLogger(__name__)

class SniperService:
    """Core sniper service that coordinates monitoring and trading"""
    
    def __init__(self):
        self.monitoring_service = MonitoringService()
        self.trading_service = TradingService()
        self.config_service = ConfigService()
        self.is_running = False
        self.start_time = None
        
    def get_health_status(self) -> HealthStatus:
        """Get comprehensive health status"""
        try:
            uptime = 0
            if self.start_time:
                uptime = (datetime.utcnow() - self.start_time).total_seconds()
            
            wallet_connected = self.config_service.is_wallet_connected()
            monitoring_active = self.monitoring_service.is_monitoring_active()
            active_positions = len(self.trading_service.get_positions())
            
            return HealthStatus(
                status="healthy" if self.is_running else "stopped",
                timestamp=datetime.utcnow(),
                version="1.0.0",
                uptime=uptime,
                wallet_connected=wallet_connected,
                monitoring_active=monitoring_active,
                active_positions=active_positions
            )
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return HealthStatus(
                status="error",
                timestamp=datetime.utcnow(),
                version="1.0.0",
                uptime=0,
                wallet_connected=False,
                monitoring_active=False,
                active_positions=0
            )
    
    def start_sniper(self) -> bool:
        """Start the sniper bot"""
        try:
            if self.is_running:
                logger.warning("Sniper is already running")
                return False
            
            # Check if wallet is connected
            if not self.config_service.is_wallet_connected():
                logger.error("Cannot start sniper: wallet not connected")
                return False
            
            # Start monitoring
            if not self.monitoring_service.start_monitoring():
                logger.error("Failed to start monitoring")
                return False
            
            self.is_running = True
            self.start_time = datetime.utcnow()
            logger.info("Sniper started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start sniper: {e}")
            return False
    
    def stop_sniper(self) -> bool:
        """Stop the sniper bot"""
        try:
            if not self.is_running:
                logger.warning("Sniper is not running")
                return False
            
            # Stop monitoring
            self.monitoring_service.stop_monitoring()
            
            self.is_running = False
            self.start_time = None
            logger.info("Sniper stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop sniper: {e}")
            return False
    
    def get_status(self) -> Dict:
        """Get current sniper status"""
        try:
            return {
                'is_running': self.is_running,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0,
                'monitoring_active': self.monitoring_service.is_monitoring_active(),
                'active_positions': len(self.trading_service.get_positions()),
                'wallet_connected': self.config_service.is_wallet_connected()
            }
        except Exception as e:
            logger.error(f"Failed to get sniper status: {e}")
            return {'error': str(e)}
