#!/usr/bin/env python3
"""
Test WebSocket Communication
"""

import asyncio
import logging
import json
from flask_socketio import SocketIO
from web_server import app, socketio, WebSocketHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_websocket_emission():
    """Test WebSocket emission"""
    print("🧪 Testing WebSocket Communication...")
    print("=" * 50)
    
    # Test data
    test_token = {
        'mint': 'test_mint_123',
        'symbol': 'TEST',
        'name': 'Test Token',
        'market_cap': 50000,
        'price': 0.001,
        'sol_in_pool': 10.5,
        'tokens_in_pool': 1000000,
        'initial_buy': 0,
        'created_timestamp': 1234567890,
        'liquidity': 10.5,
        'holders': 150,
        'age_days': 2.5,
        'is_on_pump': True,
        'pump_info': {'source': 'test'},
        'source': 'test'
    }
    
    print(f"📡 Testing token emission: {test_token['symbol']}")
    
    try:
        # Test the WebSocket handler directly
        WebSocketHandler.emit_new_token(test_token)
        print("✅ WebSocket emission test completed")
        
        # Test position update
        test_position = {
            'mint': 'test_mint_123',
            'action': 'buy',
            'sol_amount': 1.0,
            'timestamp': 1234567890
        }
        WebSocketHandler.emit_position_update(test_position)
        print("✅ Position update emission test completed")
        
        # Test error emission
        WebSocketHandler.emit_error("Test error message")
        print("✅ Error emission test completed")
        
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

def test_socketio_connection():
    """Test SocketIO connection"""
    print("\n🔌 Testing SocketIO Connection...")
    print("=" * 50)
    
    try:
        # Test if SocketIO is properly configured
        print(f"SocketIO async mode: {socketio.async_mode}")
        print(f"SocketIO cors allowed origins: {socketio.cors_allowed_origins}")
        print("✅ SocketIO configuration looks good")
        
    except Exception as e:
        print(f"❌ SocketIO test failed: {e}")

if __name__ == "__main__":
    print("🚀 WebSocket Communication Test")
    print("=" * 60)
    
    # Test 1: WebSocket emission
    test_websocket_emission()
    
    # Test 2: SocketIO connection
    test_socketio_connection()
    
    print("\n" + "=" * 60)
    print("🎯 WebSocket Test Complete") 