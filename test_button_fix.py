#!/usr/bin/env python3
"""
Test Start Monitoring Button Fix
"""

import requests
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_button_fix():
    """Test the Start Monitoring button fix"""
    print("🧪 Testing Start Monitoring Button Fix...")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # Test 1: Check initial status
    print("\n1️⃣ Checking initial status...")
    try:
        response = requests.get(f"{base_url}/api/status")
        if response.status_code == 200:
            status_data = response.json()
            bot_running = status_data.get('data', {}).get('is_running', False)
            print(f"   ✅ Server is running")
            print(f"   📊 Bot Running: {bot_running}")
        else:
            print(f"   ❌ Server returned status {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Cannot connect to server: {e}")
        return
    
    # Test 2: If bot is running, stop it first
    if bot_running:
        print("\n2️⃣ Stopping bot first...")
        try:
            response = requests.post(f"{base_url}/api/bot/stop", 
                                   headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Bot stopped: {json.dumps(result, indent=2)}")
            else:
                print(f"   ❌ Failed to stop bot: {response.status_code}")
                return
        except Exception as e:
            print(f"   ❌ Error stopping bot: {e}")
            return
    
    # Test 3: Start the bot
    print("\n3️⃣ Starting bot...")
    try:
        response = requests.post(f"{base_url}/api/bot/start", 
                               headers={'Content-Type': 'application/json'})
        
        print(f"   Response Status: {response.status_code}")
        
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
            return
                
    except Exception as e:
        print(f"   ❌ Error calling start API: {e}")
        return
    
    # Test 4: Try to start again (should fail gracefully)
    print("\n4️⃣ Trying to start again (should show 'already running' message)...")
    try:
        response = requests.post(f"{base_url}/api/bot/start", 
                               headers={'Content-Type': 'application/json'})
        
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 400:
            result = response.json()
            print(f"   ✅ Correctly handled: {json.dumps(result, indent=2)}")
            if "already running" in result.get('error', '').lower():
                print("   ✅ Frontend should now show 'Bot is already running' message")
            else:
                print("   ⚠️ Unexpected error message")
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            try:
                result = response.json()
                print(f"   Response: {json.dumps(result, indent=2)}")
            except:
                print(f"   Response text: {response.text}")
                
    except Exception as e:
        print(f"   ❌ Error calling start API again: {e}")
    
    # Test 5: Check final status
    print("\n5️⃣ Checking final status...")
    try:
        response = requests.get(f"{base_url}/api/status")
        if response.status_code == 200:
            status_data = response.json()
            bot_running = status_data.get('data', {}).get('is_running', False)
            print(f"   📊 Final Bot Status: {'Running' if bot_running else 'Stopped'}")
            
            if bot_running:
                print("   ✅ Bot is running successfully")
                print("   🎯 The Start Monitoring button should now work correctly!")
            else:
                print("   ❌ Bot is not running")
        else:
            print(f"   ❌ Failed to get final status")
    except Exception as e:
        print(f"   ❌ Error getting final status: {e}")

if __name__ == "__main__":
    print("🚀 Start Monitoring Button Fix Test")
    print("=" * 60)
    
    test_button_fix()
    
    print("\n" + "=" * 60)
    print("🎯 Button Fix Test Complete")
    print("\n💡 Now try clicking the 'Start Monitoring' button in your browser.")
    print("   It should work correctly and show appropriate messages.") 