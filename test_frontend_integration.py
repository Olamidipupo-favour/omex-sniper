#!/usr/bin/env python3
"""
Test Frontend Integration
"""

import requests
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_frontend_integration():
    """Test the complete frontend integration flow"""
    print("🧪 Testing Frontend Integration...")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # Test 1: Check if server is running
    print("\n1️⃣ Checking server status...")
    try:
        response = requests.get(f"{base_url}/api/status")
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
    
    # Test 3: Start monitoring
    print("\n3️⃣ Starting monitoring...")
    try:
        response = requests.post(f"{base_url}/api/bot/start", 
                               headers={'Content-Type': 'application/json'})
        
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Start successful: {json.dumps(result, indent=2)}")
            
            # Wait a moment for the bot to start processing
            print("\n4️⃣ Waiting for bot to process tokens...")
            time.sleep(5)
            
            # Check status again
            print("\n5️⃣ Checking updated status...")
            response = requests.get(f"{base_url}/api/status")
            if response.status_code == 200:
                updated_status = response.json()
                print(f"   📊 Updated Bot Status: {json.dumps(updated_status, indent=2)}")
                
                # Check if bot is running
                bot_running = updated_status.get('data', {}).get('is_running', False)
                if bot_running:
                    print("   ✅ Bot is running successfully")
                else:
                    print("   ❌ Bot is not running")
            else:
                print(f"   ❌ Failed to get updated status")
                
        else:
            print(f"   ❌ Start failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Error text: {response.text}")
                
    except Exception as e:
        print(f"   ❌ Error calling start API: {e}")
    
    # Test 4: Stop monitoring
    print("\n6️⃣ Stopping monitoring...")
    try:
        response = requests.post(f"{base_url}/api/bot/stop", 
                               headers={'Content-Type': 'application/json'})
        
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Stop successful: {json.dumps(result, indent=2)}")
        else:
            print(f"   ❌ Stop failed with status {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error calling stop API: {e}")

def test_websocket_connection():
    """Test WebSocket connection"""
    print("\n🔌 Testing WebSocket Connection...")
    print("=" * 50)
    
    # This would require a WebSocket client to test properly
    # For now, we'll just check if the SocketIO endpoint is available
    try:
        response = requests.get("http://localhost:5000/socket.io/")
        print(f"   SocketIO endpoint status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ SocketIO endpoint is accessible")
        else:
            print("   ⚠️ SocketIO endpoint returned unexpected status")
    except Exception as e:
        print(f"   ❌ Cannot access SocketIO endpoint: {e}")

if __name__ == "__main__":
    print("🚀 Frontend Integration Test")
    print("=" * 60)
    
    # Test 1: Frontend integration
    test_frontend_integration()
    
    # Test 2: WebSocket connection
    test_websocket_connection()
    
    print("\n" + "=" * 60)
    print("🎯 Frontend Integration Test Complete")
    print("\n💡 If the bot is working but the frontend isn't updating,")
    print("   check the browser console for JavaScript errors.")
    print("   The issue might be in the frontend JavaScript code.") 