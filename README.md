# 🎯 KARAMBULA Sniper Bot

A beautiful, modern web-based sniper bot for Pump.Fun token launches with real-time monitoring, auto-trading capabilities, and a professional dark-themed UI.

![KARAMBULA Sniper Bot](https://img.shields.io/badge/KARAMBULA-Sniper%20Bot-blue?style=for-the-badge&logo=solana)
![Python](https://img.shields.io/badge/Python-3.9+-green?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-WebSocket-red?style=for-the-badge&logo=flask)
![Solana](https://img.shields.io/badge/Solana-Blockchain-purple?style=for-the-badge&logo=solana)

## ✨ Features

### 🔥 Core Features
- **Real-Time Token Monitoring** - Instant detection of new Pump.Fun token launches via PumpPortal WebSocket
- **Auto Buy/Sell Logic** - Automated trading with customizable profit targets and stop-loss
- **Beautiful Web Interface** - Modern dark-themed UI with real-time updates
- **Secure Wallet Integration** - Safe private key handling with Solana wallet support
- **Fast Transaction Processing** - Uses Helius RPC for lightning-fast trade execution
- **Position Management** - Track multiple positions with live P&L calculations

### 📊 Advanced Features
- **Market Cap Filtering** - Set min/max market cap criteria for token selection
- **Slippage Protection** - Configurable slippage tolerance for trades
- **Transaction History** - Complete audit trail of all buy/sell orders
- **Real-Time Notifications** - Browser notifications for new tokens and trades
- **Multiple Token Support** - Monitor and trade up to 20 tokens simultaneously
- **Live Price Updates** - Real-time price tracking via PumpPortal trade events

### 🎨 User Interface
- **Professional Design** - Clean, modern interface inspired by top trading platforms
- **Dark Theme** - Easy on the eyes for long monitoring sessions
- **Responsive Layout** - Works on desktop, tablet, and mobile devices
- **Real-Time Dashboard** - Live updates without page refreshes
- **Toast Notifications** - Elegant success/error messaging
- **Connection Status** - Visual indicators for WebSocket and wallet connectivity

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- Helius RPC API key (get free key at [helius.dev](https://www.helius.dev/))
- Solana wallet with SOL for trading

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pumpfun
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   # The bot will create a .env file on first run
   # Edit it to add your Helius API key:
   HELIUS_API_KEY=your-helius-api-key-here
   ```

4. **Launch the bot**
   ```bash
   python3 run_bot.py
   ```

5. **Open your browser**
   ```
   http://localhost:8001
   ```

## 🐳 Docker Deployment (Recommended)

### Option 1: Automated GitHub Actions (Recommended)
The bot automatically builds and pushes to DockerHub on every GitHub push!

1. **Set up GitHub Secrets** (see [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md))
2. **Push your code** to GitHub
3. **Pull and run** the latest image:
   ```bash
   docker pull tesals/karambula:latest
   docker-compose up -d
   ```

### Option 2: Manual Docker Build
```bash
docker build -t karambula-bot .
docker run -d -p 8001:8001 karambula-bot
```

## 📖 Usage Guide

### 🔗 Connecting Your Wallet

1. Click "Connect Wallet" in the top-right corner
2. Enter your Solana private key (supports both base58 and JSON array formats)
3. Your wallet address and SOL balance will be displayed once connected

**Security Note**: Your private key is processed locally and never stored permanently.

### ⚙️ Configuring Bot Settings

Navigate to the Settings section to customize:

- **SOL Amount per Trade**: Amount of SOL to spend on each buy order (0.001 - 10 SOL)
- **Max Tokens**: Maximum number of simultaneous positions (1-20)
- **Profit Target**: Profit percentage to trigger auto-sell (1-1000%)
- **Stop Loss**: Loss percentage to trigger auto-sell (1-100%)
- **Slippage**: Maximum slippage tolerance (1-50%)
- **Market Cap Range**: Min/max market cap filters for token selection
- **Auto Buy/Sell**: Toggle automated trading features

### 🎯 Starting the Bot

1. Ensure your wallet is connected
2. Configure your desired settings
3. Click "Start Monitoring" to begin detecting new tokens
4. The bot will automatically buy tokens that meet your criteria (if auto-buy is enabled)
5. Monitor your positions in real-time on the dashboard

### 📈 Monitoring Dashboard

The dashboard provides four main tabs:

1. **New Tokens** - Real-time feed of newly launched tokens
2. **Active Positions** - Your current holdings with live P&L
3. **Transaction History** - Complete record of all trades
4. **System Logs** - Bot activity and error messages

### 💰 Manual Trading

You can also trade manually:
- Click "Buy" on any token in the New Tokens tab
- Click "Sell" on any position in the Active Positions tab
- All manual trades use your configured SOL amount and slippage settings

## 🔧 Technical Details

### Architecture

- **Frontend**: Modern HTML5/CSS3/JavaScript with Socket.IO for real-time updates
- **Backend**: Python Flask with Flask-SocketIO for WebSocket communication
- **Blockchain**: Solana integration via solana-py library
- **Data Sources**: PumpPortal WebSocket for real-time data, Helius RPC for transactions

### API Integration

- **PumpPortal WebSocket**: `wss://pumpportal.fun/api/data`
  - Subscribes to new token events
  - Receives real-time trade data for price updates
  
- **PumpPortal Trade API**: `https://pumpportal.fun/api/trade-local`
  - Generates transaction data for buy/sell orders
  - Uses your own RPC for maximum speed and reliability

- **Helius RPC**: High-performance Solana RPC endpoint
  - Fast transaction submission and confirmation
  - Reliable balance and account queries

### File Structure

```
pumpfun/
├── config.py              # Configuration settings
├── sniper_bot.py          # Main bot logic
├── pump_fun_monitor.py    # PumpPortal WebSocket monitoring
├── pumpportal_trader.py   # Trading execution
├── web_server.py          # Flask web server
├── run_bot.py            # Application launcher
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Main HTML template
├── static/
│   ├── css/
│   │   └── style.css     # Stylesheet
│   └── js/
│       └── app.js        # Frontend JavaScript
└── .env                  # Environment variables
```

## ⚠️ Important Disclaimers

### Trading Risks
- **High Risk**: Pump.Fun tokens are extremely volatile and speculative
- **Loss of Capital**: You may lose all invested funds
- **Market Manipulation**: Be aware of pump and dump schemes
- **Slippage**: Prices can change rapidly during execution

### Security Notes
- **Private Keys**: Your private key is processed locally but use at your own risk
- **API Keys**: Keep your Helius API key secure
- **Testing**: Always test with small amounts first
- **Backup**: Ensure you have secure backups of your wallet

### Legal Compliance
- **Regulations**: Ensure compliance with local laws and regulations
- **Tax Obligations**: You are responsible for reporting trading gains/losses
- **Terms of Service**: Comply with Solana and exchange terms of service

## 🔍 Troubleshooting

### Common Issues

**Bot won't start**
- Check Python version (3.9+ required)
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Ensure port 8080 is available

**WebSocket connection failed**
- Check internet connection
- Verify PumpPortal service is operational
- Try refreshing the browser page

**Wallet connection issues**
- Ensure private key format is correct (base58 or JSON array)
- Check that wallet has sufficient SOL balance
- Verify Helius RPC connectivity

**Trades not executing**
- Confirm wallet is connected and has SOL
- Check slippage settings (increase if trades fail)
- Verify Helius API key is valid

### Performance Tips

- **RPC Selection**: Use a high-performance RPC like Helius for best results
- **Internet Connection**: Stable, fast connection is crucial for sniping
- **System Resources**: Close unnecessary applications for optimal performance
- **Slippage**: Higher slippage increases success rate but reduces profit

## 🛠️ Development

### Running Tests

```bash
# Test PumpPortal connectivity
python3 test_pumpportal.py
```

### Adding Features

The codebase is modular and extensible:
- Add new filters in `sniper_bot.py`
- Modify UI in `templates/index.html` and `static/`
- Extend monitoring in `pump_fun_monitor.py`
- Add trading features in `pumpportal_trader.py`

## 📄 License

This project is for educational purposes only. Use at your own risk.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 💬 Support

For support and questions:
- Check the troubleshooting section above
- Review the code documentation
- Test with small amounts first

---

**⚡ Built for speed, designed for profit, crafted for traders.**