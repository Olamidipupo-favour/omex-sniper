#!/usr/bin/env python3
"""
Test Monitoring System
"""

import asyncio
import time
import logging
from sniper_bot import SniperBot
from config import config_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_monitoring():
    """Test the monitoring system"""
    print("🧪 Testing Monitoring System...")
    print("=" * 50)
    
    # Create bot instance
    bot = SniperBot()
    
    # Check initial status
    print("\n1️⃣ Checking Initial Status...")
    status = bot.get_bot_status()
    print(f"   Bot Running: {status['is_running']}")
    print(f"   Wallet Connected: {status['wallet_connected']}")
    print(f"   Token Age Filter: {status['settings']['token_age_filter']}")
    
    # Check if wallet is connected
    if not status['wallet_connected']:
        print("   ❌ Wallet not connected - cannot test monitoring")
        return
    
    # Test starting monitoring
    print("\n2️⃣ Testing Start Monitoring...")
    try:
        success = await bot.start_monitoring()
        print(f"   Start Result: {success}")
        
        if success:
            # Wait a bit and check status
            await asyncio.sleep(3)
            status = bot.get_bot_status()
            print(f"   Bot Running After Start: {status['is_running']}")
            
            # Keep monitoring for a few seconds
            print("\n3️⃣ Monitoring for 10 seconds...")
            start_time = time.time()
            while time.time() - start_time < 10:
                await asyncio.sleep(1)
                print(f"   Monitoring... ({int(time.time() - start_time)}s)")
            
            # Test stopping monitoring
            print("\n4️⃣ Testing Stop Monitoring...")
            stop_success = bot.stop_monitoring()
            print(f"   Stop Result: {stop_success}")
            
            # Check final status
            await asyncio.sleep(1)
            status = bot.get_bot_status()
            print(f"   Bot Running After Stop: {status['is_running']}")
            
        else:
            print("   ❌ Failed to start monitoring")
            
    except Exception as e:
        print(f"   ❌ Error during monitoring test: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
    
    print("\n" + "=" * 50)
    print("🎯 Monitoring Test Complete")

if __name__ == "__main__":
    asyncio.run(test_monitoring()) 