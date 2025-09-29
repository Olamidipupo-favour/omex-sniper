#!/usr/bin/env python3
"""
Omex Coin Sniper Microservice API
A well-documented API for coin sniping operations on Solana blockchain
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

# Import our services
from services.sniper_service import SniperService
from services.monitoring_service import MonitoringService
from services.trading_service import TradingService
from services.config_service import ConfigService
from services.database_service import db_service
from services.auth_service import auth_service, require_auth, require_admin, get_current_user
from models.schemas import (
    TokenInfo, Position, TradeRequest, TradeResponse, 
    SniperConfig, HealthStatus, ErrorResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize API with Swagger documentation
api = Api(
    app,
    version='1.0.0',
    title='Omex Coin Sniper API',
    description='A comprehensive API for coin sniping operations on Solana blockchain',
    doc='/docs/',
    prefix='/api/v1'
)

# Create namespaces for different API sections
sniper_ns = Namespace('sniper', description='Sniper operations')
monitoring_ns = Namespace('monitoring', description='Token monitoring')
trading_ns = Namespace('trading', description='Trading operations')
config_ns = Namespace('config', description='Configuration management')
health_ns = Namespace('health', description='Health and status')
auth_ns = Namespace('auth', description='User authentication')
user_ns = Namespace('user', description='User management')
wallet_ns = Namespace('wallet', description='Wallet management')

# Add namespaces to API
api.add_namespace(sniper_ns, path='/sniper')
api.add_namespace(monitoring_ns, path='/monitoring')
api.add_namespace(trading_ns, path='/trading')
api.add_namespace(config_ns, path='/config')
api.add_namespace(health_ns, path='/health')
api.add_namespace(auth_ns, path='/auth')
api.add_namespace(user_ns, path='/user')
api.add_namespace(wallet_ns, path='/wallet')

# Initialize services
sniper_service = SniperService()
monitoring_service = MonitoringService()
trading_service = TradingService()
config_service = ConfigService()

# Define API models for documentation
token_info_model = api.model('TokenInfo', {
    'mint': fields.String(required=True, description='Token mint address'),
    'symbol': fields.String(required=True, description='Token symbol'),
    'name': fields.String(required=True, description='Token name'),
    'price': fields.Float(required=True, description='Current price in USD'),
    'market_cap': fields.Float(required=True, description='Market cap in USD'),
    'liquidity': fields.Float(required=True, description='Liquidity in SOL'),
    'holders': fields.Integer(required=True, description='Number of holders'),
    'created_timestamp': fields.Integer(required=True, description='Creation timestamp'),
    'is_on_pump': fields.Boolean(required=True, description='Is token on Pump.fun'),
    'source': fields.String(required=True, description='Data source')
})

position_model = api.model('Position', {
    'mint': fields.String(required=True, description='Token mint address'),
    'symbol': fields.String(required=True, description='Token symbol'),
    'entry_price': fields.Float(required=True, description='Entry price in USD'),
    'current_price': fields.Float(required=True, description='Current price in USD'),
    'sol_amount': fields.Float(required=True, description='SOL amount invested'),
    'token_amount': fields.Float(required=True, description='Token amount held'),
    'pnl': fields.Float(required=True, description='Profit/Loss in SOL'),
    'pnl_percent': fields.Float(required=True, description='Profit/Loss percentage'),
    'entry_time': fields.DateTime(required=True, description='Entry timestamp'),
    'is_active': fields.Boolean(required=True, description='Is position active')
})

trade_request_model = api.model('TradeRequest', {
    'mint': fields.String(required=True, description='Token mint address'),
    'amount': fields.Float(required=True, description='Amount to trade'),
    'action': fields.String(required=True, enum=['buy', 'sell'], description='Trade action'),
    'slippage': fields.Float(required=False, default=5.0, description='Slippage tolerance (%)'),
    'priority_fee': fields.Float(required=False, default=0.0001, description='Priority fee in SOL')
})

trade_response_model = api.model('TradeResponse', {
    'success': fields.Boolean(required=True, description='Trade success status'),
    'signature': fields.String(description='Transaction signature'),
    'amount': fields.Float(description='Amount traded'),
    'price': fields.Float(description='Execution price'),
    'message': fields.String(description='Response message')
})

sniper_config_model = api.model('SniperConfig', {
    'sol_per_snipe': fields.Float(required=True, description='SOL amount per snipe'),
    'max_positions': fields.Integer(required=True, description='Maximum concurrent positions'),
    'profit_target_percent': fields.Float(required=True, description='Profit target percentage'),
    'stop_loss_percent': fields.Float(required=True, description='Stop loss percentage'),
    'min_market_cap': fields.Float(required=True, description='Minimum market cap filter'),
    'max_market_cap': fields.Float(required=True, description='Maximum market cap filter'),
    'min_liquidity': fields.Float(required=True, description='Minimum liquidity filter'),
    'min_holders': fields.Integer(required=True, description='Minimum holders filter'),
    'auto_buy': fields.Boolean(required=True, description='Enable auto buy'),
    'auto_sell': fields.Boolean(required=True, description='Enable auto sell')
})

health_status_model = api.model('HealthStatus', {
    'status': fields.String(required=True, description='Service status'),
    'timestamp': fields.DateTime(required=True, description='Status timestamp'),
    'version': fields.String(required=True, description='Service version'),
    'uptime': fields.Float(required=True, description='Service uptime in seconds'),
    'wallet_connected': fields.Boolean(required=True, description='Wallet connection status'),
    'monitoring_active': fields.Boolean(required=True, description='Monitoring status'),
    'active_positions': fields.Integer(required=True, description='Number of active positions')
})

error_response_model = api.model('ErrorResponse', {
    'error': fields.String(required=True, description='Error message'),
    'code': fields.String(description='Error code'),
    'details': fields.String(description='Error details')
})

# Health Check Endpoints
@health_ns.route('/status')
class HealthStatus(Resource):
    @api.marshal_with(health_status_model)
    def get(self):
        """Get service health status"""
        try:
            status = sniper_service.get_health_status()
            return status, 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {'error': str(e)}, 500

@health_ns.route('/ping')
class Ping(Resource):
    def get(self):
        """Simple ping endpoint"""
        return {'message': 'pong', 'timestamp': datetime.utcnow().isoformat()}, 200

# Sniper Configuration Endpoints
@config_ns.route('/sniper')
class SniperConfigResource(Resource):
    @api.marshal_with(sniper_config_model)
    def get(self):
        """Get current sniper configuration"""
        try:
            config = config_service.get_sniper_config()
            return config, 200
        except Exception as e:
            logger.error(f"Failed to get sniper config: {e}")
            return {'error': str(e)}, 500

    @api.expect(sniper_config_model)
    @api.marshal_with(sniper_config_model)
    def put(self):
        """Update sniper configuration"""
        try:
            config_data = request.get_json()
            updated_config = config_service.update_sniper_config(config_data)
            return updated_config, 200
        except Exception as e:
            logger.error(f"Failed to update sniper config: {e}")
            return {'error': str(e)}, 500

# Monitoring Endpoints
@monitoring_ns.route('/tokens')
class TokenMonitoring(Resource):
    @api.marshal_list_with(token_info_model)
    def get(self):
        """Get currently monitored tokens"""
        try:
            tokens = monitoring_service.get_monitored_tokens()
            return tokens, 200
        except Exception as e:
            logger.error(f"Failed to get monitored tokens: {e}")
            return {'error': str(e)}, 500

@monitoring_ns.route('/start')
class StartMonitoring(Resource):
    def post(self):
        """Start token monitoring"""
        try:
            result = monitoring_service.start_monitoring()
            return {'success': result, 'message': 'Monitoring started' if result else 'Failed to start monitoring'}, 200
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            return {'error': str(e)}, 500

@monitoring_ns.route('/stop')
class StopMonitoring(Resource):
    def post(self):
        """Stop token monitoring"""
        try:
            result = monitoring_service.stop_monitoring()
            return {'success': result, 'message': 'Monitoring stopped' if result else 'Failed to stop monitoring'}, 200
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}")
            return {'error': str(e)}, 500

# Trading Endpoints
@trading_ns.route('/positions')
class Positions(Resource):
    @api.marshal_list_with(position_model)
    def get(self):
        """Get current trading positions"""
        try:
            positions = trading_service.get_positions()
            return positions, 200
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return {'error': str(e)}, 500

@trading_ns.route('/trade')
class Trade(Resource):
    @api.expect(trade_request_model)
    @api.marshal_with(trade_response_model)
    def post(self):
        """Execute a trade (buy/sell)"""
        try:
            trade_data = request.get_json()
            result = trading_service.execute_trade(trade_data)
            return result, 200
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return {'error': str(e)}, 500

@trading_ns.route('/positions/<string:mint>')
class PositionManagement(Resource):
    def delete(self, mint):
        """Close a specific position"""
        try:
            result = trading_service.close_position(mint)
            return {'success': result, 'message': 'Position closed' if result else 'Failed to close position'}, 200
        except Exception as e:
            logger.error(f"Failed to close position {mint}: {e}")
            return {'error': str(e)}, 500

# Sniper Operations Endpoints
@sniper_ns.route('/start')
class StartSniper(Resource):
    def post(self):
        """Start the sniper bot"""
        try:
            result = sniper_service.start_sniper()
            return {'success': result, 'message': 'Sniper started' if result else 'Failed to start sniper'}, 200
        except Exception as e:
            logger.error(f"Failed to start sniper: {e}")
            return {'error': str(e)}, 500

@sniper_ns.route('/stop')
class StopSniper(Resource):
    def post(self):
        """Stop the sniper bot"""
        try:
            result = sniper_service.stop_sniper()
            return {'success': result, 'message': 'Sniper stopped' if result else 'Failed to stop sniper'}, 200
        except Exception as e:
            logger.error(f"Failed to stop sniper: {e}")
            return {'error': str(e)}, 500

@sniper_ns.route('/status')
class SniperStatus(Resource):
    def get(self):
        """Get sniper status"""
        try:
            status = sniper_service.get_status()
            return status, 200
        except Exception as e:
            logger.error(f"Failed to get sniper status: {e}")
            return {'error': str(e)}, 500

# Wallet Management
@config_ns.route('/wallet/connect')
class ConnectWallet(Resource):
    def post(self):
        """Connect wallet with private key"""
        try:
            data = request.get_json()
            private_key = data.get('private_key')
            if not private_key:
                return {'error': 'Private key is required'}, 400
            
            result = config_service.connect_wallet(private_key)
            return {'success': result, 'message': 'Wallet connected' if result else 'Failed to connect wallet'}, 200
        except Exception as e:
            logger.error(f"Failed to connect wallet: {e}")
            return {'error': str(e)}, 500

@config_ns.route('/wallet/disconnect')
class DisconnectWallet(Resource):
    def post(self):
        """Disconnect wallet"""
        try:
            result = config_service.disconnect_wallet()
            return {'success': result, 'message': 'Wallet disconnected' if result else 'Failed to disconnect wallet'}, 200
        except Exception as e:
            logger.error(f"Failed to disconnect wallet: {e}")
            return {'error': str(e)}, 500

@config_ns.route('/wallet/balance')
class WalletBalance(Resource):
    def get(self):
        """Get wallet SOL balance"""
        try:
            balance = config_service.get_wallet_balance()
            return {'balance': balance}, 200
        except Exception as e:
            logger.error(f"Failed to get wallet balance: {e}")
            return {'error': str(e)}, 500

# Authentication Endpoints
@auth_ns.route('/register')
class Register(Resource):
    def post(self):
        """Register new user"""
        try:
            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            
            if not all([username, email, password]):
                return {'error': 'Username, email, and password are required'}, 400
            
            result = auth_service.register_user(username, email, password)
            return result, 201 if result['success'] else 400
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return {'error': str(e)}, 500

@auth_ns.route('/login')
class Login(Resource):
    def post(self):
        """Login user"""
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            if not all([username, password]):
                return {'error': 'Username and password are required'}, 400
            
            result = auth_service.login_user(username, password)
            return result, 200 if result['success'] else 401
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return {'error': str(e)}, 500

@auth_ns.route('/logout')
class Logout(Resource):
    @require_auth
    def post(self):
        """Logout user"""
        try:
            auth_header = request.headers.get('Authorization')
            token = auth_header.split(' ')[1] if auth_header else None
            
            if not token:
                return {'error': 'No token provided'}, 400
            
            result = auth_service.logout_user(token)
            return result, 200 if result['success'] else 400
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return {'error': str(e)}, 500

# User Management Endpoints
@user_ns.route('/profile')
class UserProfile(Resource):
    @require_auth
    def get(self):
        """Get user profile"""
        try:
            user = g.current_user
            result = auth_service.get_user_profile(user.id)
            return result, 200 if result['success'] else 404
            
        except Exception as e:
            logger.error(f"Profile error: {e}")
            return {'error': str(e)}, 500

# Wallet Management Endpoints
@wallet_ns.route('/')
class WalletList(Resource):
    @require_auth
    def get(self):
        """Get user wallets"""
        try:
            user = g.current_user
            wallets = db_service.get_user_wallets(user.id)
            return {'wallets': wallets}, 200
            
        except Exception as e:
            logger.error(f"Get wallets error: {e}")
            return {'error': str(e)}, 500

@wallet_ns.route('/')
class CreateWallet(Resource):
    @require_auth
    def post(self):
        """Create new wallet"""
        try:
            user = g.current_user
            data = request.get_json()
            
            wallet_name = data.get('wallet_name')
            private_key = data.get('private_key')
            
            if not all([wallet_name, private_key]):
                return {'error': 'Wallet name and private key are required'}, 400
            
            from models.user import WalletCreate
            wallet_data = WalletCreate(
                wallet_name=wallet_name,
                private_key=private_key
            )
            
            wallet = db_service.create_wallet(user.id, wallet_data)
            
            if wallet:
                return {'success': True, 'wallet': wallet}, 201
            else:
                return {'error': 'Failed to create wallet'}, 400
                
        except Exception as e:
            logger.error(f"Create wallet error: {e}")
            return {'error': str(e)}, 500

@wallet_ns.route('/<int:wallet_id>/connect')
class ConnectWallet(Resource):
    @require_auth
    def post(self, wallet_id):
        """Connect to specific wallet"""
        try:
            user = g.current_user
            private_key = db_service.get_wallet_private_key(user.id, wallet_id)
            
            if not private_key:
                return {'error': 'Wallet not found or access denied'}, 404
            
            # Use existing config service to connect wallet
            success = config_service.connect_wallet(private_key)
            
            if success:
                return {'success': True, 'message': 'Wallet connected'}, 200
            else:
                return {'error': 'Failed to connect wallet'}, 400
                
        except Exception as e:
            logger.error(f"Connect wallet error: {e}")
            return {'error': str(e)}, 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return {'error': 'Endpoint not found'}, 404

@app.errorhandler(500)
def internal_error(error):
    return {'error': 'Internal server error'}, 500

if __name__ == '__main__':
    # Get configuration from environment
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Omex Coin Sniper API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
