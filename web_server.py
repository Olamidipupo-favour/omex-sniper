from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import asyncio
import threading
import json
import logging
from datetime import datetime
from config import Config
from sniper_bot import SniperBot, Position
from pump_fun_monitor import TokenInfo

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pump-fun-sniper-bot-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global bot instance
bot = SniperBot()
bot_thread = None
is_monitoring = False

class WebSocketHandler:
    @staticmethod
    def emit_new_token(token: TokenInfo):
        socketio.emit('new_token', {
            'mint': token.mint,
            'symbol': token.symbol,
            'name': token.name,
            'market_cap': token.market_cap,
            'price': token.price,
            'created_timestamp': token.created_timestamp,
            'nsfw': token.nsfw,
            'description': token.description
        })
    
    @staticmethod
    def emit_position_update(position: Position):
        socketio.emit('position_update', {
            'token_mint': position.token_mint,
            'token_symbol': position.token_symbol,
            'token_name': position.token_name,
            'entry_price': position.entry_price,
            'current_price': position.current_price,
            'sol_amount': position.sol_amount,
            'current_pnl': position.current_pnl,
            'current_pnl_percent': position.current_pnl_percent,
            'is_active': position.is_active,
            'entry_time': position.entry_time.isoformat(),
            'transaction_hash': position.transaction_hash
        })
    
    @staticmethod
    def emit_transaction(transaction_data):
        socketio.emit('transaction', transaction_data)
    
    @staticmethod
    def emit_error(error_msg):
        socketio.emit('error', {'message': error_msg})

# Set up bot callbacks
bot.add_callback('new_token', WebSocketHandler.emit_new_token)
bot.add_callback('position_update', WebSocketHandler.emit_position_update)
bot.add_callback('transaction', WebSocketHandler.emit_transaction)
bot.add_callback('error', WebSocketHandler.emit_error)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/api/connect_wallet', methods=['POST'])
def connect_wallet():
    try:
        data = request.get_json()
        private_key = data.get('private_key', '').strip()
        
        if not private_key:
            return jsonify({'success': False, 'error': 'Private key is required'})
        
        if bot.set_wallet(private_key):
            wallet_address = bot.get_wallet_address()
            sol_balance = bot.get_sol_balance()
            
            return jsonify({
                'success': True,
                'wallet_address': wallet_address,
                'sol_balance': sol_balance
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid private key format'})
            
    except Exception as e:
        logger.error(f"Error connecting wallet: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update_settings', methods=['POST'])
def update_settings():
    try:
        data = request.get_json()
        
        bot.settings.sol_amount_per_snipe = float(data.get('sol_amount', Config.DEFAULT_SOL_AMOUNT))
        bot.settings.max_concurrent_positions = int(data.get('max_positions', Config.DEFAULT_MAX_TOKENS))
        bot.settings.profit_target_percent = float(data.get('profit_target', Config.DEFAULT_PROFIT_PERCENT))
        bot.settings.stop_loss_percent = float(data.get('stop_loss', Config.DEFAULT_STOP_LOSS_PERCENT))
        bot.settings.auto_buy_enabled = bool(data.get('auto_buy', False))
        bot.settings.auto_sell_enabled = bool(data.get('auto_sell', True))
        bot.settings.min_market_cap = float(data.get('min_market_cap', 1000))
        bot.settings.max_market_cap = float(data.get('max_market_cap', 1000000000000))
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/start_monitoring', methods=['POST'])
def start_monitoring():
    global bot_thread, is_monitoring
    
    try:
        if not bot.wallet_keypair:
            return jsonify({'success': False, 'error': 'Please connect wallet first'})
        
        if is_monitoring:
            return jsonify({'success': False, 'error': 'Already monitoring'})
        
        def run_bot():
            global is_monitoring
            is_monitoring = True
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(bot.start_monitoring())
            except Exception as e:
                logger.error(f"Error in bot monitoring: {e}")
            finally:
                is_monitoring = False
        
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stop_monitoring', methods=['POST'])
def stop_monitoring():
    global is_monitoring
    
    try:
        bot.stop_monitoring()
        is_monitoring = False
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/buy_token', methods=['POST'])
def buy_token():
    try:
        data = request.get_json()
        mint = data.get('mint')
        amount_sol = data.get('amount_sol', bot.settings.sol_amount_per_snipe)
        
        if not mint:
            return jsonify({'success': False, 'error': 'Token mint is required'})
        
        # Execute manual buy
        async def execute_buy():
            return await bot.manual_buy(mint, amount_sol)
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(execute_buy())
        
        return jsonify({'success': result})
        
    except Exception as e:
        logger.error(f"Error buying token: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sell_position', methods=['POST'])
def sell_position():
    try:
        data = request.get_json()
        token_mint = data.get('token_mint')
        
        if not token_mint:
            return jsonify({'success': False, 'error': 'Token mint is required'})
        
        # Find position and sell
        position = None
        for pos in bot.positions:
            if pos.token_mint == token_mint and pos.is_active:
                position = pos
                break
        
        if not position:
            return jsonify({'success': False, 'error': 'Position not found'})
        
        # Execute sell
        async def execute_sell():
            return await bot.sell_token(position, "manual")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(execute_sell())
        
        return jsonify({'success': result})
        
    except Exception as e:
        logger.error(f"Error selling position: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/get_status', methods=['GET'])
def get_status():
    try:
        wallet_address = bot.get_wallet_address() if bot.wallet_keypair else ""
        sol_balance = bot.get_sol_balance() if bot.wallet_keypair else 0.0
        pnl_data = bot.get_total_pnl()
        
        positions = []
        for pos in bot.positions:
            positions.append({
                'token_mint': pos.token_mint,
                'token_symbol': pos.token_symbol,
                'token_name': pos.token_name,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'sol_amount': pos.sol_amount,
                'token_amount': pos.token_amount,
                'current_pnl': pos.current_pnl,
                'current_pnl_percent': pos.current_pnl_percent,
                'is_active': pos.is_active,
                'entry_time': pos.entry_time.isoformat(),
                'transaction_hash': pos.transaction_hash,
                'target_profit_percent': pos.target_profit_percent,
                'stop_loss_percent': pos.stop_loss_percent
            })
        
        return jsonify({
            'success': True,
            'wallet_connected': bool(bot.wallet_keypair),
            'wallet_address': wallet_address,
            'sol_balance': sol_balance,
            'is_monitoring': is_monitoring,
            'total_pnl': pnl_data['total_pnl'],
            'total_pnl_percent': pnl_data['total_pnl_percent'],
            'total_invested': pnl_data['total_invested'],
            'active_positions': pnl_data['active_positions'],
            'positions': positions,
            'settings': {
                'sol_amount_per_snipe': bot.settings.sol_amount_per_snipe,
                'max_concurrent_positions': bot.settings.max_concurrent_positions,
                'profit_target_percent': bot.settings.profit_target_percent,
                'stop_loss_percent': bot.settings.stop_loss_percent,
                'auto_buy_enabled': bot.settings.auto_buy_enabled,
                'auto_sell_enabled': bot.settings.auto_sell_enabled,
                'min_market_cap': bot.settings.min_market_cap,
                'max_market_cap': bot.settings.max_market_cap
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'success': False, 'error': str(e)})

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    emit('connected', {'message': 'Connected to Pump.Fun Sniper Bot'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

def run_web_server():
    socketio.run(app, host='0.0.0.0', port=8080, debug=False)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_web_server() 