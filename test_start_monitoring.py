#!/usr/bin/env python3
"""
Test Start Monitoring Functionality
"""

import asyncio
import logging
import requests
import json
from sniper_bot import SniperBot
from config import config_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_start_monitoring_api():
    """Test the start monitoring API endpoint"""
    print("🧪 Testing Start Monitoring API...")
    print("=" * 50)
    
    # Test 1: Check if server is running
    print("\n1️⃣ Checking server status...")
    try:
        response = requests.get('http://localhost:5000/api/status')
        if response.status_code == 200:
            status_data = response.json()
            print(f"   ✅ Server is running")
            print(f"   📊 Bot Status: {json.dumps(status_data, indent=2)}")
        else:
            print(f"   ❌ Server returned status {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Cannot connect to server: {e}")
        return
    
    # Test 2: Check wallet connection
    print("\n2️⃣ Checking wallet connection...")
    status_data = status_data.get('data', {})
    wallet_connected = status_data.get('wallet_connected', False)
    print(f"   Wallet Connected: {wallet_connected}")
    
    if not wallet_connected:
        print("   ❌ Wallet not connected - cannot test monitoring")
        print("   💡 Please connect your wallet first in the web interface")
        return
    
    # Test 3: Try to start monitoring
    print("\n3️⃣ Testing start monitoring...")
    try:
        response = requests.post('http://localhost:5000/api/bot/start', 
                               headers={'Content-Type': 'application/json'})
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Start successful: {json.dumps(result, indent=2)}")
        else:
            print(f"   ❌ Start failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Error text: {response.text}")
                
    except Exception as e:
        print(f"   ❌ Error calling start API: {e}")
    
    # Test 4: Check status after start attempt
    print("\n4️⃣ Checking status after start attempt...")
    try:
        response = requests.get('http://localhost:5000/api/status')
        if response.status_code == 200:
            status_data = response.json()
            print(f"   📊 Updated Bot Status: {json.dumps(status_data, indent=2)}")
        else:
            print(f"   ❌ Failed to get updated status")
    except Exception as e:
        print(f"   ❌ Error getting updated status: {e}")

def test_bot_directly():
    """Test the bot directly without the web server"""
    print("\n🔧 Testing Bot Directly...")
    print("=" * 50)
    
    # Create bot instance
    bot = SniperBot()
    
    # Check initial status
    print("\n1️⃣ Checking Bot Status...")
    status = bot.get_bot_status()
    print(f"   Bot Running: {status['is_running']}")
    print(f"   Wallet Connected: {status['wallet_connected']}")
    print(f"   Wallet Address: {status['wallet_address']}")
    print(f"   SOL Balance: {status['sol_balance']}")
    
    if not status['wallet_connected']:
        print("   ❌ Wallet not connected - cannot test")
        return
    
    # Test start monitoring
    print("\n2️⃣ Testing Start Monitoring...")
    try:
        success = asyncio.run(bot.start_monitoring())
        print(f"   Start Result: {success}")
        
        if success:
            # Check status after start
            asyncio.sleep(2)
            status = bot.get_bot_status()
            print(f"   Bot Running After Start: {status['is_running']}")
            
            # Test stop monitoring
            print("\n3️⃣ Testing Stop Monitoring...")
            stop_success = bot.stop_monitoring()
            print(f"   Stop Result: {stop_success}")
            
            # Check final status
            status = bot.get_bot_status()
            print(f"   Bot Running After Stop: {status['is_running']}")
        else:
            print("   ❌ Failed to start monitoring")
            
    except Exception as e:
        print(f"   ❌ Error during monitoring test: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    print("🚀 Start Monitoring Debug Test")
    print("=" * 60)
    
    # Test 1: API endpoint
    test_start_monitoring_api()
    
    # Test 2: Direct bot testing
    test_bot_directly()
    
    print("\n" + "=" * 60)
    print("🎯 Debug Test Complete") 