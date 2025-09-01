# Docker Deployment Guide for Pump.Fun Sniper Bot

## Prerequisites

- Docker and Docker Compose installed
- Helius API key
- PumpPortal API key (optional)

## Quick Start

### 1. Environment Setup

Create a `.env` file in the project root:

```bash
# Required API Keys
HELIUS_API_KEY=your_helius_api_key_here
PUMPPORTAL_API_KEY=your_pumpportal_api_key_here

# Optional Configuration
PYTHONUNBUFFERED=1
TZ=UTC
```

### 2. Build and Run

```bash
# Build the Docker image
docker-compose build

# Run the container
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Stop the Container

```bash
docker-compose down
```

## Manual Docker Commands

### Build Image
```bash
docker build -t pumpfun-sniper-bot .
```

### Run Container
```bash
docker run -d \
  --name pumpfun-sniper-bot \
  --restart unless-stopped \
  -e HELIUS_API_KEY=your_key_here \
  -e PUMPPORTAL_API_KEY=your_key_here \
  -v $(pwd)/bot_config.json:/app/bot_config.json \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  -p 8001:8001 \
  pumpfun-sniper-bot
```

## Configuration

### Persistent Data
The following directories are mounted as volumes:
- `./bot_config.json` - Bot configuration file
- `./logs/` - Application logs
- `./data/` - Persistent data storage

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HELIUS_API_KEY` | Yes | Your Helius API key for RPC access |
| `PUMPPORTAL_API_KEY` | No | PumpPortal API key (optional) |
| `PYTHONUNBUFFERED` | No | Set to 1 for immediate log output |
| `TZ` | No | Timezone (default: UTC) |

### Web Interface
The bot runs a Flask-SocketIO web server on port 8001. Access it at:
- **Local**: http://localhost:8001
- **Docker**: http://localhost:8001 (when using docker-compose)

## Troubleshooting

### View Logs
```bash
# View real-time logs
docker-compose logs -f

# View specific service logs
docker logs pumpfun-sniper-bot
```

### Access Container Shell
```bash
docker exec -it pumpfun-sniper-bot /bin/bash
```

### Check Health
```bash
docker ps
docker inspect pumpfun-sniper-bot
```

### Common Issues

1. **Permission Errors**: Ensure the mounted directories have proper permissions
2. **API Key Issues**: Verify your Helius API key is valid
3. **Network Issues**: Check if port 8001 is available
4. **Memory Issues**: Adjust resource limits in docker-compose.yml
5. **Web Interface**: Access the bot at http://localhost:8001

## Production Deployment

### Security Considerations
- Use secrets management for API keys
- Run container as non-root user (already configured)
- Limit resource usage
- Use HTTPS for web interface

### Monitoring
- Health checks are configured
- Logs are persisted to host
- Resource limits prevent resource exhaustion

### Scaling
For high-frequency trading, consider:
- Increasing memory limits
- Using multiple containers
- Implementing load balancing
- Using external databases for state persistence
