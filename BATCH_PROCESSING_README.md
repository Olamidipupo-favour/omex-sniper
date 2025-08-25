# Historical Token Batch Processing

## Overview

The codebase has been enhanced with batch processing capabilities for historical token loading. Instead of waiting for all historical tokens to be fetched before processing them, the system now processes tokens in configurable batches and sends them to the frontend immediately as they become available.

## Key Benefits

1. **Faster Frontend Updates**: Users see tokens appear in batches rather than waiting for all tokens to load
2. **Better User Experience**: Progressive loading provides immediate feedback
3. **Configurable Batch Sizes**: Easy to adjust batch sizes based on performance requirements
4. **Preserved Functionality**: All existing features (holder updates, filtering, etc.) remain intact

## How It Works

### 1. Batch Processing Flow

```
Historical Token Request → Fetch First Batch → Process & Send to Frontend → Fetch Next Batch → Repeat
```

### 2. Batch Callback System

- **`get_recent_pump_tokens()`**: Now supports batch callbacks for immediate processing
- **`get_trending_pump_tokens()`**: Enhanced with batch processing capabilities
- **`get_hybrid_recent_tokens()`**: Orchestrates batch processing across all token sources

### 3. Configuration

The batch size is configurable through the bot settings:

```python
# In config.py - BotSettings class
historical_batch_size: int = 10  # Number of historical tokens to process in each batch
```

## Implementation Details

### Modified Methods

#### `token_filter_service.py`

1. **`get_recent_pump_tokens()`**
   - Added `batch_callback` and `batch_size` parameters
   - Processes tokens in batches as they're fetched from the API
   - Calls the batch callback when each batch is complete

2. **`get_trending_pump_tokens()`**
   - Similar batch processing implementation
   - Sends trending tokens to frontend in batches

3. **`get_hybrid_recent_tokens()`**
   - Orchestrates batch processing across all token sources
   - Maintains backward compatibility

#### `sniper_bot.py`

1. **`_load_historical_tokens()`**
   - Now uses batch callback approach instead of post-fetch batch processing
   - Creates a batch callback function that processes tokens immediately
   - Integrates with the token filter service's batch processing

2. **`_process_historical_token()`**
   - Extracted method for processing individual historical tokens
   - Maintains all existing functionality (holder updates, filtering, etc.)

### Batch Callback Function

```python
async def process_token_batch(token_batch: List[Dict[str, Any]]):
    """Process a batch of tokens immediately for frontend updates"""
    logger.info(f"📤 Processing batch of {len(token_batch)} tokens immediately")
    
    # Process each token in the batch concurrently
    batch_tasks = []
    for token_data in token_batch:
        task = self._process_historical_token(token_data)
        batch_tasks.append(task)
    
    # Wait for all tokens in the batch to complete processing
    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
    
    # Count successful processing
    batch_processed = sum(1 for result in batch_results if result is True)
    logger.info(f"✅ Batch processed: {batch_processed}/{len(token_batch)} tokens successfully")
    
    return batch_processed
```

## Usage Examples

### Basic Usage (Default Batch Size)

```python
# The system will use the default batch size from config
await self.token_filter.get_hybrid_recent_tokens(
    days=7,
    include_pump_only=True,
    batch_callback=process_token_batch
)
```

### Custom Batch Size

```python
# Customize batch size for specific use cases
await self.token_filter.get_hybrid_recent_tokens(
    days=7,
    include_pump_only=True,
    batch_callback=process_token_batch,
    batch_size=20  # Process 20 tokens at a time
)
```

### Without Batch Processing (Backward Compatibility)

```python
# Existing code continues to work without changes
tokens = await self.token_filter.get_hybrid_recent_tokens(days=7)
```

## Configuration Options

### Bot Settings

```json
{
  "bot_settings": {
    "historical_batch_size": 10,
    "token_age_filter": "last_7_days",
    "custom_days": 7
  }
}
```

### Environment Variables

```bash
# Can be overridden via environment variables
export HISTORICAL_BATCH_SIZE=15
```

## Performance Considerations

### Batch Size Recommendations

- **Small batches (5-10)**: Faster frontend updates, more responsive UI
- **Medium batches (10-20)**: Balanced performance and responsiveness
- **Large batches (20+)**: Better throughput but slower initial feedback

### Memory Usage

- Batch processing reduces memory usage by not holding all tokens in memory
- Each batch is processed and then cleared
- Final result still contains all processed tokens for compatibility

## Testing

### Test Script

Run the test script to verify batch processing functionality:

```bash
python test_batch_processing.py
```

### Test Coverage

1. **Basic Batch Processing**: Tests different batch sizes and token counts
2. **Performance Comparison**: Sequential vs concurrent processing
3. **Batch Callback**: Verifies callback functionality works correctly

## Migration Guide

### Existing Code

No changes required for existing code. The new batch processing is opt-in and backward compatible.

### Enabling Batch Processing

To enable batch processing, simply add a batch callback:

```python
# Before (sequential processing)
tokens = await token_filter.get_hybrid_recent_tokens(days=7)

# After (batch processing)
async def my_batch_callback(batch):
    # Process batch immediately
    for token in batch:
        await process_token(token)

tokens = await token_filter.get_hybrid_recent_tokens(
    days=7,
    batch_callback=my_batch_callback,
    batch_size=10
)
```

## Troubleshooting

### Common Issues

1. **Batch Callback Errors**: Check that the callback function is async and handles exceptions
2. **Memory Issues**: Reduce batch size if experiencing memory problems
3. **Performance Issues**: Increase batch size for better throughput

### Logging

The system provides detailed logging for batch processing:

```
📤 Sending batch of 10 tokens to frontend
✅ Batch processed: 10/10 tokens successfully
📤 Sending final batch of 5 tokens to frontend
```

## Future Enhancements

1. **Dynamic Batch Sizing**: Automatic batch size adjustment based on system performance
2. **Progress Indicators**: Frontend progress bars for batch processing
3. **Batch Prioritization**: Priority-based batch processing for important tokens
4. **Streaming Support**: Real-time streaming of tokens as they're discovered

## Conclusion

The batch processing system provides a significant improvement in user experience while maintaining all existing functionality. Historical tokens now appear progressively in the frontend, making the application feel more responsive and engaging.
