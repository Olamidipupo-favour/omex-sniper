#!/usr/bin/env python3
"""
Test script for batch processing of historical tokens
"""

import asyncio
import logging
import time
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockTokenData:
    """Mock token data for testing"""
    def __init__(self, mint: str, symbol: str, name: str):
        self.mint = mint
        self.symbol = symbol
        self.name = name
        self.created_timestamp = int(time.time())
        self.market_cap = 10000.0
        self.price = 0.001
        self.liquidity = 100.0
        self.holders = 50

async def process_historical_tokens_batch(historical_tokens: List[Dict[str, Any]], batch_size: int = 10):
    """Test the batch processing logic"""
    try:
        logger.info(f"📚 Processing {len(historical_tokens)} historical tokens in batches of {batch_size}")
        
        total_processed = 0
        
        for i in range(0, len(historical_tokens), batch_size):
            batch = historical_tokens[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(historical_tokens) + batch_size - 1) // batch_size
            
            logger.info(f"🔄 Processing batch {batch_num}/{total_batches} with {len(batch)} tokens")
            
            # Process batch concurrently for better performance
            batch_tasks = []
            for token_data in batch:
                task = process_single_historical_token(token_data)
                batch_tasks.append(task)
            
            # Wait for all tokens in the batch to complete processing
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Count successful processing
            batch_processed = sum(1 for result in batch_results if result is True)
            total_processed += batch_processed
            
            logger.info(f"✅ Batch {batch_num}/{total_batches} completed: {batch_processed}/{len(batch)} tokens processed successfully")
            
            # Small delay between batches to prevent overwhelming the system
            if i + batch_size < len(historical_tokens):
                await asyncio.sleep(0.1)
        
        logger.info(f"✅ Successfully processed {total_processed}/{len(historical_tokens)} historical tokens in batches")
        return total_processed
        
    except Exception as e:
        logger.error(f"❌ Error in batch processing: {e}")
        return 0

async def process_single_historical_token(token_data: Dict[str, Any]) -> bool:
    """Process a single historical token (simulated)"""
    try:
        # Simulate processing time
        await asyncio.sleep(0.01)
        
        logger.info(f"🔄 Processing historical token: {token_data.get('symbol', 'Unknown')} ({token_data.get('mint', 'Unknown')})")
        
        # Simulate some processing logic
        # In real implementation, this would call _handle_new_token
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error processing historical token {token_data.get('mint', 'unknown')}: {e}")
        return False

def generate_mock_tokens(count: int) -> List[Dict[str, Any]]:
    """Generate mock token data for testing"""
    tokens = []
    for i in range(count):
        token = {
            'mint': f'TokenMint{i:04d}',
            'symbol': f'TOK{i:03d}',
            'name': f'Test Token {i}',
            'description': f'Test token description {i}',
            'image_uri': f'https://example.com/image{i}.png',
            'created_timestamp': int(time.time()) - (i * 3600),  # Each token 1 hour apart
            'usd_market_cap': 10000.0 + (i * 1000),
            'market_cap': 10000.0 + (i * 1000),
            'price': 0.001 + (i * 0.0001),
            'liquidity': 100.0 + (i * 10),
            'holders': 50 + (i * 5)
        }
        tokens.append(token)
    return tokens

async def test_batch_processing():
    """Test the batch processing functionality"""
    logger.info("🚀 Starting Batch Processing Test")
    
    # Test different batch sizes
    batch_sizes = [5, 10, 20]
    token_counts = [25, 50, 100]
    
    for token_count in token_counts:
        for batch_size in batch_sizes:
            logger.info(f"\n{'='*60}")
            logger.info(f"🧪 Testing with {token_count} tokens, batch size {batch_size}")
            logger.info(f"{'='*60}")
            
            # Generate mock tokens
            mock_tokens = generate_mock_tokens(token_count)
            
            # Test batch processing
            start_time = time.time()
            processed_count = await process_historical_tokens_batch(mock_tokens, batch_size)
            end_time = time.time()
            
            # Calculate performance metrics
            total_time = end_time - start_time
            tokens_per_second = processed_count / total_time if total_time > 0 else 0
            
            logger.info(f"📊 Performance Results:")
            logger.info(f"   Total tokens: {token_count}")
            logger.info(f"   Batch size: {batch_size}")
            logger.info(f"   Processed: {processed_count}")
            logger.info(f"   Total time: {total_time:.2f} seconds")
            logger.info(f"   Tokens per second: {tokens_per_second:.2f}")
            
            # Verify all tokens were processed
            if processed_count == token_count:
                logger.info(f"✅ SUCCESS: All {token_count} tokens processed correctly")
            else:
                logger.warning(f"⚠️ WARNING: Only {processed_count}/{token_count} tokens processed")
            
            await asyncio.sleep(0.5)  # Small delay between tests

async def test_concurrent_vs_sequential():
    """Test concurrent vs sequential processing performance"""
    logger.info("\n🚀 Starting Concurrent vs Sequential Performance Test")
    
    # Generate 50 mock tokens
    mock_tokens = generate_mock_tokens(50)
    
    # Test sequential processing
    logger.info("🔄 Testing sequential processing...")
    start_time = time.time()
    
    sequential_results = []
    for token_data in mock_tokens:
        result = await process_single_historical_token(token_data)
        sequential_results.append(result)
    
    sequential_time = time.time() - start_time
    sequential_processed = sum(sequential_results)
    
    logger.info(f"📊 Sequential Results:")
    logger.info(f"   Processed: {sequential_processed}/{len(mock_tokens)}")
    logger.info(f"   Time: {sequential_time:.2f} seconds")
    
    # Test concurrent processing (batch size 10)
    logger.info("🔄 Testing concurrent processing (batch size 10)...")
    start_time = time.time()
    
    concurrent_processed = await process_historical_tokens_batch(mock_tokens, 10)
    
    concurrent_time = time.time() - start_time
    
    logger.info(f"📊 Concurrent Results:")
    logger.info(f"   Processed: {concurrent_processed}/{len(mock_tokens)}")
    logger.info(f"   Time: {concurrent_time:.2f} seconds")
    
    # Calculate improvement
    if sequential_time > 0:
        improvement = ((sequential_time - concurrent_time) / sequential_time) * 100
        logger.info(f"🚀 Performance Improvement: {improvement:.1f}% faster with concurrent processing")

async def test_batch_callback():
    """Test the batch callback functionality"""
    logger.info("\n🚀 Starting Batch Callback Test")
    
    # Generate 25 mock tokens
    mock_tokens = generate_mock_tokens(25)
    
    # Track batches received
    batches_received = []
    
    async def batch_callback(token_batch: List[Dict[str, Any]]):
        """Simulate the batch callback that would be used in the real system"""
        logger.info(f"📤 CALLBACK: Received batch of {len(token_batch)} tokens")
        batches_received.append(token_batch)
        
        # Simulate processing time
        await asyncio.sleep(0.05)
        
        # Log first token in batch for verification
        if token_batch:
            first_token = token_batch[0]
            logger.info(f"   First token: {first_token.get('symbol', 'Unknown')} ({first_token.get('mint', 'Unknown')})")
    
    # Test with different batch sizes
    batch_sizes = [5, 10, 15]
    
    for batch_size in batch_sizes:
        logger.info(f"\n{'='*50}")
        logger.info(f"🧪 Testing batch callback with batch size {batch_size}")
        logger.info(f"{'='*50}")
        
        # Clear previous results
        batches_received.clear()
        
        # Simulate batch processing
        start_time = time.time()
        
        # Process tokens in batches
        for i in range(0, len(mock_tokens), batch_size):
            batch = mock_tokens[i:i + batch_size]
            await batch_callback(batch)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        logger.info(f"📊 Batch Callback Results:")
        logger.info(f"   Total tokens: {len(mock_tokens)}")
        logger.info(f"   Batch size: {batch_size}")
        logger.info(f"   Batches received: {len(batches_received)}")
        logger.info(f"   Total time: {total_time:.2f} seconds")
        
        # Verify batch sizes
        expected_batches = (len(mock_tokens) + batch_size - 1) // batch_size
        if len(batches_received) == expected_batches:
            logger.info(f"✅ SUCCESS: Correct number of batches ({expected_batches})")
        else:
            logger.warning(f"⚠️ WARNING: Expected {expected_batches} batches, got {len(batches_received)}")
        
        # Verify all tokens were processed
        total_tokens_in_batches = sum(len(batch) for batch in batches_received)
        if total_tokens_in_batches == len(mock_tokens):
            logger.info(f"✅ SUCCESS: All {len(mock_tokens)} tokens processed in batches")
        else:
            logger.warning(f"⚠️ WARNING: Expected {len(mock_tokens)} tokens, got {total_tokens_in_batches}")
        
        await asyncio.sleep(0.5)  # Small delay between tests

async def main():
    """Main test function"""
    logger.info("🔍 Historical Token Batch Processing Test")
    logger.info("=" * 60)
    
    try:
        # Test basic batch processing
        await test_batch_processing()
        
        # Test performance comparison
        await test_concurrent_vs_sequential()
        
        # Test batch callback functionality
        await test_batch_callback()
        
        logger.info("\n✅ All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main())
