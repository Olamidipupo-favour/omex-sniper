from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import asyncio
import threading
import logging
from typing import Dict, Any

from config import config_manager
from sniper_bot import SniperBot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'pump-fun-sniper-secret-key'

# Initialize SocketIO with fallback for Python 3.13 compatibility
try:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
except Exception as e:
    logger.warning(f"Failed to initialize SocketIO with threading mode: {e}")
    try:
        socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')
    except Exception as e2:
        logger.warning(f"Failed to initialize SocketIO with gevent mode: {e2}")
        # Fallback to basic mode
        socketio = SocketIO(app, cors_allowed_origins="*")

# Global bot instance
bot = SniperBot()
bot_thread = None
loop = None

# Set up the trade callback for the bot's monitor
bot.monitor.set_trade_callback(bot._handle_pumpportal_trade)
logger.info("✅ Trade callback connected to bot monitor")
logger.info(f"📊 Trade callback function: {bot._handle_pumpportal_trade.__name__}")
logger.info(f"📊 Trade callback is async: {asyncio.iscoroutinefunction(bot._handle_pumpportal_trade)}")

class WebSocketHandler:
    """Handle WebSocket communications"""
    
    @staticmethod
    def emit_new_token(token_data: Dict[str, Any]):
        """Emit new token event to frontend"""
        logger.info(f"📡 WebSocket: Emitting token to frontend: {token_data.get('symbol', 'Unknown')}")
        logger.info(f"📋 WebSocket: Token data: {token_data}")
        
        socketio.emit('new_token', {
            'mint': token_data.get('mint'),
            'symbol': token_data.get('symbol'),
            'name': token_data.get('name'),
            'market_cap': token_data.get('market_cap'),
            'price': token_data.get('price'),
            'sol_in_pool': token_data.get('sol_in_pool'),
            'tokens_in_pool': token_data.get('tokens_in_pool'),
            'initial_buy': token_data.get('initial_buy'),
            'created_timestamp': token_data.get('created_timestamp'),
            'liquidity': token_data.get('liquidity'),
            'holders': token_data.get('holders'),
            'age_days': token_data.get('age_days'),
            'is_on_pump': token_data.get('is_on_pump'),
            'pump_info': token_data.get('pump_info'),
            'source': token_data.get('source', 'pumpportal')
        })
        
        logger.info(f"✅ WebSocket: Token emitted successfully")
    
    @staticmethod
    def emit_position_update(position_data: Dict[str, Any]):
        """Emit position update to frontend"""
        logger.info(f"📡 WebSocket: Emitting position update to frontend")
        logger.info(f"📋 WebSocket: Position data: {position_data}")
        socketio.emit('position_update', position_data)
        logger.info(f"✅ WebSocket: Position update emitted successfully")
    
    @staticmethod
    def emit_transaction(transaction_data: Dict[str, Any]):
        """Emit transaction event to frontend"""
        socketio.emit('transaction', transaction_data)
    
    @staticmethod
    def emit_error(error_message: str):
        """Emit error event to frontend"""
        socketio.emit('error', {'message': error_message})
    
    @staticmethod
    def emit_auto_buy_success(data: Dict[str, Any]):
        """Emit auto-buy success event to frontend"""
        socketio.emit('auto_buy_success', data)
    
    @staticmethod
    def emit_auto_buy_error(data: Dict[str, Any]):
        """Emit auto buy error event"""
        socketio.emit('auto_buy_error', data)
    
    @staticmethod
    def emit_transaction_update(data: Dict[str, Any]):
        """Emit transaction update event"""
        socketio.emit('transaction_update', data)
    
    @staticmethod
    def emit_price_update(data: Dict[str, Any]):
        """Emit price update event"""
        socketio.emit('price_update', data)
    
    @staticmethod
    def emit_trade_update(data: Dict[str, Any]):
        """Emit trade update event"""
        socketio.emit('trade_update', data)

async def handle_bot_event(event_type: str, data: Dict[str, Any]):
    """Handle bot events for WebSocket emission"""
    if event_type == 'new_token':
        WebSocketHandler.emit_new_token(data)
    elif event_type == 'position_update':
        WebSocketHandler.emit_position_update(data)
    elif event_type == 'transaction':
        WebSocketHandler.emit_transaction(data)
    elif event_type == 'transaction_update':
        WebSocketHandler.emit_transaction_update(data)
    elif event_type == 'price_update':
        WebSocketHandler.emit_price_update(data)
    elif event_type == 'trade_update':
        WebSocketHandler.emit_trade_update(data)
    elif event_type == 'error':
        WebSocketHandler.emit_error(data)
    elif event_type == 'auto_buy_success':
        WebSocketHandler.emit_auto_buy_success(data)
    elif event_type == 'auto_buy_error':
        WebSocketHandler.emit_auto_buy_error(data)
    else:
        logger.warning(f"⚠️ Unknown event type: {event_type}")

def handle_bot_event_sync(event_type: str, data: Dict[str, Any]):
    """Synchronous wrapper for bot event handling"""
    import asyncio
    try:
        # Get the current event loop or create a new one
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, create a task
            asyncio.create_task(handle_bot_event(event_type, data))
        except RuntimeError:
            # No running loop, run in new event loop
            asyncio.run(handle_bot_event(event_type, data))
    except Exception as e:
        logger.error(f"❌ Error handling bot event {event_type}: {e}")

bot.set_ui_callback(handle_bot_event_sync)

# Routes
@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current bot status"""
    try:
        status = bot.get_bot_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/wallet/connect', methods=['POST'])
def connect_wallet():
    """Connect wallet with private key"""
    try:
        data = request.get_json()
        private_key = data.get('private_key')
        
        if not private_key:
            return jsonify({
                'success': False,
                'error': 'Private key is required'
            }), 400
        
        success, message = bot.connect_wallet_from_key(private_key)
        
        if success:
            status = bot.get_bot_status()
            return jsonify({
                'success': True,
                'message': message,
                'wallet_address': status['wallet_address'],
                'sol_balance': status['sol_balance']
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error connecting wallet: {e}")
        return jsonify({
            'success': False,
            'error': f'Connection failed: {str(e)}'
        }), 500

@app.route('/api/wallet/disconnect', methods=['POST'])
def disconnect_wallet():
    """Disconnect wallet and clear private key"""
    try:
        # Stop monitoring if running
        if config_manager.config.bot_state.is_running:
            bot.stop_monitoring()
        
        # Clear wallet data
        config_manager.clear_private_key()
        
        return jsonify({
            'success': True,
            'message': 'Wallet disconnected successfully'
        })
        
    except Exception as e:
        logger.error(f"Error disconnecting wallet: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/settings/update', methods=['POST'])
def update_settings():
    """Update bot settings"""
    try:
        data = request.get_json()
        
        # Validate settings
        valid_settings = {
            'sol_per_snipe': float,
            'max_positions': int,
            'profit_target_percent': float,
            'stop_loss_percent': float,
            'min_market_cap': float,
            'max_market_cap': float,
            'min_liquidity': float,
            'min_holders': int,
            'auto_buy': bool,
            'auto_sell': bool,
            'sell_strategy': str,
            'sell_after_buys': int,
            'sell_after_seconds': int,
            'token_age_filter': str,
            'custom_days': int,
            'include_pump_tokens': bool,
            'transaction_type': str,
            'priority_fee': float
        }
        
        settings = {}
        for key, value in data.items():
            if key in valid_settings:
                settings[key] = valid_settings[key](value)

        # Back-compat: convert legacy hours to seconds if provided
        if 'sell_after_hours' in data and 'sell_after_seconds' not in settings:
            try:
                settings['sell_after_seconds'] = int(float(data['sell_after_hours']) * 3600)
            except Exception:
                pass
        
        success = bot.update_settings(settings)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Settings updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update settings'
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bot/start', methods=['POST'])
def start_monitoring():
    """Start bot monitoring"""
    global bot_thread, loop
    
    try:
        if config_manager.config.bot_state.is_running:
            return jsonify({
                'success': False,
                'error': 'Bot is already running'
            }), 400
        
        # Verify trade callback is set up
        logger.info("🔍 Verifying trade callback setup...")
        logger.info(f"📊 Monitor trade callback: {bot.monitor.trade_callback}")
        logger.info(f"📊 Monitor trade callback name: {bot.monitor.trade_callback.__name__ if bot.monitor.trade_callback else 'None'}")
        
        def run_bot():
            global loop
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot.start_monitoring())
            except Exception as e:
                logger.error(f"Error in bot thread: {e}")
            finally:
                if loop and not loop.is_closed():
                    loop.close()
        
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Bot monitoring started'
        })
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bot/stop', methods=['POST'])
def stop_monitoring():
    """Stop bot monitoring"""
    global bot_thread, loop
    
    try:
        success = bot.stop_monitoring()
        
        if bot_thread and bot_thread.is_alive():
            bot_thread.join(timeout=5)
        
        return jsonify({
            'success': success,
            'message': 'Bot monitoring stopped' if success else 'Failed to stop bot'
        })
        
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/trade/buy', methods=['POST'])
def manual_buy():
    """Execute manual buy"""
    try:
        data = request.get_json()
        mint = data.get('mint')
        amount = data.get('amount', config_manager.config.bot_settings.sol_per_snipe)
        symbol = data.get('symbol', 'Unknown')
        name = data.get('name', 'Unknown')
        
        # Debug logging
        logger.info(f"🔍 Manual buy request - mint: {mint}, amount: {amount}, symbol: {symbol}, name: {name}")
        logger.info(f"🔍 Full request data: {data}")
        
        if not mint:
            return jsonify({
                'success': False,
                'error': 'Mint address is required'
            }), 400
        
        # Execute buy in async context
        async def execute_buy():
            return await bot.buy_token(mint, amount, symbol, name)
        
        # Run in the bot's event loop if it exists
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(execute_buy(), loop)
            success = future.result(timeout=30)
        else:
            success = asyncio.run(execute_buy())
        
        return jsonify({
            'success': success,
            'message': 'Buy order executed' if success else 'Buy order failed'
        })
        
    except Exception as e:
        logger.error(f"Error executing buy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/trade/sell', methods=['POST'])
def manual_sell():
    """Execute manual sell"""
    try:
        data = request.get_json()
        mint = data.get('mint')
        
        if not mint:
            return jsonify({
                'success': False,
                'error': 'Mint address is required'
            }), 400
        
        # Execute sell in async context
        async def execute_sell():
            return await bot.sell_token(mint)
        
        # Run in the bot's event loop if it exists
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(execute_sell(), loop)
            success = future.result(timeout=30)
        else:
            success = asyncio.run(execute_sell())
        
        return jsonify({
            'success': success,
            'message': 'Sell order executed' if success else 'Sell order failed'
        })
        
    except Exception as e:
        logger.error(f"Error executing sell: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/positions', methods=['GET'])
def get_positions():
    """Get current in-memory positions (no wallet scan)"""
    try:
        positions = bot.get_positions_snapshot()
        return jsonify({'success': True, 'positions': positions})
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/wallet/sol_balance', methods=['GET'])
def get_sol_balance():
    """Fetch current SOL balance directly from RPC"""
    try:
        # Prefer sync method to avoid event loop issues when server thread changes
        balance = bot.get_wallet_balance_sync()
        return jsonify({'success': True, 'sol_balance': balance})
    except Exception as e:
        logger.error(f"Error fetching SOL balance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    """Get wallet transaction history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        # Execute in async context
        async def fetch_transactions():
            return await bot.fetch_wallet_transactions(limit)
        
        # Run in the bot's event loop if it exists
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(fetch_transactions(), loop)
            transactions = future.result(timeout=30)
        else:
            transactions = asyncio.run(fetch_transactions())
        
        return jsonify({
            'success': True,
            'transactions': transactions
        })
        
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/positions/<mint>', methods=['DELETE'])
def delete_position(mint):
    """Delete a position from backend (in-memory) without on-chain action"""
    try:
        success = bot.delete_position(mint)
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error deleting position: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# WebSocket Events
@socketio.on('connect')
def handle_connect(auth=None):
    """Handle client connection"""
    logger.info("Client connected")
    
    # Send current bot status
    status = bot.get_bot_status()
    emit('status_update', status)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("Client disconnected")

if __name__ == '__main__':
    logger.info("🚀 Starting Pump.Fun Sniper Bot Web Server...")
    logger.info(f"📁 Config file: {config_manager.config_file}")
    logger.info(f"🔗 Wallet connected: {config_manager.config.bot_state.wallet_connected}")
    logger.info(f"⚙️ Bot running: {config_manager.config.bot_state.is_running}")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False) 