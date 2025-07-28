#!/usr/bin/env python3
"""
Pump.Fun Sniper Bot Launcher
Starts the web server for the beautiful HTML frontend
"""

import os
import sys
import asyncio
import logging
from web_server import app, socketio

def main():
    """Main launcher function"""
    print("🎯 Starting Pump.Fun Sniper Bot")
    print("=" * 50)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check if we have the required environment variables
    if not os.path.exists('.env'):
        print("⚠️  Creating .env file...")
        create_env_file()
    
    print("📡 Starting web server...")
    print("🌐 Open your browser to: http://localhost:8080")
    print("🛑 Press Ctrl+C to stop the bot")
    print("=" * 50)
    
    try:
        # Start the Flask-SocketIO server
        socketio.run(
            app,
            host='0.0.0.0',
            port=8080,
            debug=False,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        sys.exit(1)

def create_env_file():
    """Create a sample .env file"""
    env_content = """# Pump.Fun Sniper Bot Configuration
# Get your Helius API key from: https://www.helius.dev/

HELIUS_API_KEY=your-helius-api-key-here

# Optional: PumpPortal API key for enhanced features
PUMPPORTAL_API_KEY=your-pumpportal-api-key-here
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("📝 Created .env file - please add your API keys")

if __name__ == "__main__":
    main() 