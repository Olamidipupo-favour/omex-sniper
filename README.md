# Omex Coin Sniper Microservice API

A well-documented, production-ready API microservice for coin sniping operations on the Solana blockchain. This service provides comprehensive endpoints for monitoring new tokens, executing trades, and managing trading positions.

## 🚀 Features

- **RESTful API** with comprehensive Swagger documentation
- **Real-time token monitoring** via PumpPortal WebSocket
- **Automated trading** with configurable filters and strategies
- **Position management** with P&L tracking
- **Wallet integration** with secure private key handling
- **Health monitoring** with status endpoints
- **Docker support** for easy deployment
- **Production-ready** with proper error handling and logging

## 📋 API Endpoints

### Health & Status
- `GET /api/v1/health/status` - Get service health status
- `GET /api/v1/health/ping` - Simple ping endpoint

### Configuration
- `GET /api/v1/config/sniper` - Get sniper configuration
- `PUT /api/v1/config/sniper` - Update sniper configuration
- `POST /api/v1/config/wallet/connect` - Connect wallet
- `POST /api/v1/config/wallet/disconnect` - Disconnect wallet
- `GET /api/v1/config/wallet/balance` - Get wallet balance

### Monitoring
- `GET /api/v1/monitoring/tokens` - Get monitored tokens
- `POST /api/v1/monitoring/start` - Start monitoring
- `POST /api/v1/monitoring/stop` - Stop monitoring

### Trading
- `GET /api/v1/trading/positions` - Get trading positions
- `POST /api/v1/trading/trade` - Execute trade (buy/sell)
- `DELETE /api/v1/trading/positions/{mint}` - Close position

### Sniper Operations
- `POST /api/v1/sniper/start` - Start sniper bot
- `POST /api/v1/sniper/stop` - Stop sniper bot
- `GET /api/v1/sniper/status` - Get sniper status

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- Docker (optional)
- Helius API key (recommended)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sniper-microservice
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

### Docker Deployment

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

2. **Access the API**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs/
   - With Nginx: http://localhost

## 🔧 Configuration

### Environment Variables

```bash
# Required
HELIUS_API_KEY=your-helius-api-key-here

# Optional
PUMPPORTAL_API_KEY=your-pumpportal-api-key-here
RPC_URL=https://api.mainnet-beta.solana.com
DEBUG=false
PORT=8000
```

### Sniper Configuration

```json
{
  "sol_per_snipe": 0.01,
  "max_positions": 5,
  "profit_target_percent": 50.0,
  "stop_loss_percent": 20.0,
  "min_market_cap": 1000.0,
  "max_market_cap": 100000.0,
  "min_liquidity": 100.0,
  "min_holders": 10,
  "auto_buy": false,
  "auto_sell": true
}
```

## 📖 API Documentation

The API includes comprehensive Swagger documentation available at `/docs/` when running the service.

### Example Usage

#### Connect Wallet
```bash
curl -X POST http://localhost:8000/api/v1/config/wallet/connect \
  -H "Content-Type: application/json" \
  -d '{"private_key": "your-private-key-here"}'
```

#### Start Monitoring
```bash
curl -X POST http://localhost:8000/api/v1/monitoring/start
```

#### Execute Trade
```bash
curl -X POST http://localhost:8000/api/v1/trading/trade \
  -H "Content-Type: application/json" \
  -d '{
    "mint": "token-mint-address",
    "amount": 0.01,
    "action": "buy",
    "slippage": 5.0
  }'
```

## 🏗️ Architecture

```
├── app.py                 # Main Flask application
├── services/              # Business logic services
│   ├── sniper_service.py  # Core sniper coordination
│   ├── monitoring_service.py  # Token monitoring
│   ├── trading_service.py    # Trade execution
│   └── config_service.py     # Configuration management
├── models/                # Data models and schemas
│   └── schemas.py         # Pydantic models
├── core/                  # Core functionality
│   ├── solana_client.py  # Solana blockchain client
│   ├── pump_monitor.py   # Token monitoring
│   ├── pump_trader.py    # Trade execution
│   └── token_filter.py   # Token filtering
└── requirements.txt       # Python dependencies
```

## 🔒 Security

- Private keys are handled securely and never logged
- All API endpoints include proper error handling
- Input validation on all endpoints
- Rate limiting (recommended for production)

## 📊 Monitoring

The service includes comprehensive health checks:

- Service status and uptime
- Wallet connection status
- Active monitoring status
- Position tracking
- Error logging

## 🚀 Production Deployment

### Docker Compose
```bash
docker-compose up -d
```

### Environment Setup
1. Set up your Helius API key
2. Configure your wallet private key
3. Adjust sniper parameters
4. Set up monitoring and logging

### Health Checks
- `GET /api/v1/health/status` - Comprehensive health status
- `GET /api/v1/health/ping` - Simple connectivity check

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is for educational purposes only. Use at your own risk.

## ⚠️ Disclaimer

- **High Risk**: Cryptocurrency trading involves significant risk
- **No Guarantees**: Past performance does not guarantee future results
- **Use at Your Own Risk**: You may lose all invested funds
- **Compliance**: Ensure compliance with local laws and regulations

## 🆘 Support

For support and questions:
- Check the API documentation at `/docs/`
- Review the health status at `/api/v1/health/status`
- Check logs for error details
- Test with small amounts first

---

**⚡ Built for speed, designed for profit, crafted for traders.**