// Pump.Fun Sniper Bot Frontend JavaScript
class SniperBotApp {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.walletConnected = false;
        this.botRunning = false;
        this.newTokens = [];
        this.positions = [];
        this.transactions = [];
        this.logs = [];
        
        this.initializeApp();
    }
    
    initializeApp() {
        this.setupEventListeners();
        this.connectWebSocket();
        this.startUIUpdates();
        this.loadInitialData();
    }
    
    setupEventListeners() {
        // Wallet connection
        document.getElementById('connectWalletBtn').addEventListener('click', () => this.connectWallet());
        
        // Bot controls
        document.getElementById('startBtn').addEventListener('click', () => this.startBot());
        document.getElementById('stopBtn').addEventListener('click', () => this.stopBot());
        document.getElementById('updateSettingsBtn').addEventListener('click', () => this.updateSettings());
        
        // Clear buttons
        document.getElementById('clearTokensBtn').addEventListener('click', () => this.clearTokens());
        document.getElementById('clearTransactionsBtn').addEventListener('click', () => this.clearTransactions());
        document.getElementById('clearLogsBtn').addEventListener('click', () => this.clearLogs());
        
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });
        
        // Settings form inputs
        document.querySelectorAll('.settings-form input').forEach(input => {
            input.addEventListener('change', () => this.validateSettings());
        });
        
        // Manual trade buttons (will be added dynamically)
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('buy-btn')) {
                this.buyToken(e.target.dataset.mint);
            }
            if (e.target.classList.contains('sell-btn')) {
                this.sellPosition(e.target.dataset.mint);
            }
        });
    }
    
    connectWebSocket() {
        try {
            this.socket = io();
            
            this.socket.on('connect', () => {
                this.isConnected = true;
                this.updateConnectionStatus('Connected', true);
                this.addLog('WebSocket connected', 'success');
            });
            
            this.socket.on('disconnect', () => {
                this.isConnected = false;
                this.updateConnectionStatus('Disconnected', false);
                this.addLog('WebSocket disconnected', 'error');
            });
            
            this.socket.on('new_token', (token) => {
                this.handleNewToken(token);
            });
            
            this.socket.on('position_update', (position) => {
                this.handlePositionUpdate(position);
            });
            
            this.socket.on('transaction', (transaction) => {
                this.handleTransaction(transaction);
            });
            
            this.socket.on('error', (error) => {
                this.handleError(error);
            });
            
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.addLog('Failed to connect WebSocket', 'error');
        }
    }
    
    async connectWallet() {
        const privateKey = document.getElementById('privateKeyInput').value.trim();
        
        if (!privateKey) {
            this.showToast('Please enter your private key', 'error');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/wallet/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    private_key: privateKey
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.walletConnected = true;
                document.getElementById('walletAddress').textContent = result.wallet_address;
                document.getElementById('walletBalance').textContent = `${result.sol_balance.toFixed(3)} SOL`;
                document.getElementById('solBalance').textContent = result.sol_balance.toFixed(3);
                
                // Hide wallet form and show wallet info
                document.getElementById('walletForm').style.display = 'none';
                document.getElementById('walletInfo').style.display = 'block';
                
                // Clear private key input for security
                document.getElementById('privateKeyInput').value = '';
                
                this.showToast('Wallet connected successfully!', 'success');
                this.addLog(`Wallet connected: ${this.truncateAddress(result.wallet_address)}`, 'success');
                
                this.updateBotControls();
            } else {
                this.showToast(result.error || 'Failed to connect wallet', 'error');
            }
        } catch (error) {
            console.error('Wallet connection error:', error);
            this.showToast('Connection failed', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async startBot() {
        if (!this.walletConnected) {
            this.showToast('Please connect your wallet first', 'warning');
            return;
        }
        
        if (this.botRunning) {
            this.showToast('Bot is already running', 'info');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/bot/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.botRunning = true;
                this.updateBotControls();
                this.showToast('Bot monitoring started!', 'success');
                this.addLog('Bot monitoring started', 'success');
            } else {
                this.showToast(result.error || 'Failed to start bot', 'error');
            }
        } catch (error) {
            console.error('Error starting bot:', error);
            this.showToast('Failed to start bot', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async stopBot() {
        if (!this.botRunning) {
            this.showToast('Bot is not running', 'info');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/bot/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.botRunning = false;
                this.updateBotControls();
                this.showToast('Bot monitoring stopped', 'info');
                this.addLog('Bot monitoring stopped', 'info');
            } else {
                this.showToast(result.error || 'Failed to stop bot', 'error');
            }
        } catch (error) {
            console.error('Error stopping bot:', error);
            this.showToast('Failed to stop bot', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async updateSettings() {
        this.showLoading(true);
        
        try {
            const settings = {
                sol_per_snipe: parseFloat(document.getElementById('solAmount').value),
                max_positions: parseInt(document.getElementById('maxPositions').value),
                profit_target_percent: parseFloat(document.getElementById('profitTarget').value),
                stop_loss_percent: parseFloat(document.getElementById('stopLoss').value),
                min_market_cap: parseFloat(document.getElementById('minMarketCap').value),
                max_market_cap: parseFloat(document.getElementById('maxMarketCap').value),
                auto_buy: document.getElementById('autoBuy').checked,
                auto_sell: document.getElementById('autoSell').checked
            };
            
            const response = await fetch('/api/settings/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('Settings updated successfully!', 'success');
                this.addLog('Bot settings updated', 'info');
            } else {
                this.showToast(result.error || 'Failed to update settings', 'error');
            }
        } catch (error) {
            console.error('Error updating settings:', error);
            this.showToast('Failed to update settings', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async buyToken(mint) {
        if (!this.walletConnected) {
            this.showToast('Please connect your wallet first', 'warning');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/trade/buy', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    mint: mint,
                    amount: parseFloat(document.getElementById('solAmount').value)
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('Buy order executed successfully!', 'success');
                this.addLog(`Buy order executed for ${mint.slice(0, 8)}...`, 'success');
            } else {
                this.showToast(result.error || 'Buy order failed', 'error');
            }
        } catch (error) {
            console.error('Error buying token:', error);
            this.showToast('Buy order failed', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async sellPosition(mint) {
        if (!this.walletConnected) {
            this.showToast('Please connect your wallet first', 'warning');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/trade/sell', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    mint: mint
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('Sell order executed successfully!', 'success');
                this.addLog(`Sell order executed for ${mint.slice(0, 8)}...`, 'success');
            } else {
                this.showToast(result.error || 'Sell order failed', 'error');
            }
        } catch (error) {
            console.error('Error selling position:', error);
            this.showToast('Sell order failed', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    handleNewToken(token) {
        // Enhanced debug: Log the received token data structure
        console.log('=== NEW TOKEN RECEIVED ===');
        console.log('Full token object:', token);
        console.log('Keys in token object:', Object.keys(token));
        console.log('sol_in_pool value:', token.sol_in_pool, 'type:', typeof token.sol_in_pool);
        console.log('tokens_in_pool value:', token.tokens_in_pool, 'type:', typeof token.tokens_in_pool);
        console.log('initial_buy value:', token.initial_buy, 'type:', typeof token.initial_buy);
        console.log('market_cap value:', token.market_cap, 'type:', typeof token.market_cap);
        console.log('price value:', token.price, 'type:', typeof token.price);
        console.log('===========================');
        
        this.newTokens.unshift(token);
        if (this.newTokens.length > 50) {
            this.newTokens = this.newTokens.slice(0, 50);
        }
        
        this.updateNewTokensTable();
        this.addLog(`New token detected: ${token.symbol}`, 'info');
        
        // Show notification if enabled
        if (Notification.permission === 'granted') {
            new Notification(`New Token: ${token.symbol}`, {
                body: `Market Cap: $${token.market_cap.toLocaleString()}`,
                icon: '/static/images/logo.png'
            });
        }
    }
    
    handlePositionUpdate(position) {
        const index = this.positions.findIndex(p => p.mint === position.mint);
        if (index >= 0) {
            this.positions[index] = position;
        } else {
            this.positions.push(position);
        }
        
        this.updatePositionsTable();
        this.updateTotalPnL();
    }
    
    handleTransaction(transaction) {
        this.transactions.unshift(transaction);
        if (this.transactions.length > 100) {
            this.transactions = this.transactions.slice(0, 100);
        }
        
        this.updateTransactionsTable();
        
        const type = transaction.type === 'buy' ? '🟢' : '🔴';
        this.addLog(`${type} ${transaction.type.toUpperCase()}: ${transaction.symbol}`, 'info');
    }
    
    handleError(error) {
        this.addLog(`Error: ${error}`, 'error');
        this.showToast(error, 'error');
    }
    
    updateNewTokensTable() {
        const tbody = document.querySelector('#tokensTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (this.newTokens.length === 0) {
            tbody.innerHTML = '<div class="empty-state"><i class="fas fa-search"></i><p>Waiting for new tokens...</p></div>';
            return;
        }
        
        this.newTokens.forEach((token, index) => {
            // Debug logging for table rendering
            if (index === 0) { // Only log for the first token to avoid spam
                console.log('=== RENDERING TOKEN IN TABLE ===');
                console.log('sol_in_pool for rendering:', token.sol_in_pool, '|| 0 =', token.sol_in_pool || 0);
                console.log('tokens_in_pool for rendering:', token.tokens_in_pool);
                console.log('tokens_in_pool / 1000000:', token.tokens_in_pool ? (token.tokens_in_pool / 1000000).toFixed(1) + 'M' : '0');
                console.log('initial_buy for rendering:', token.initial_buy);
                console.log('initial_buy / 1000000:', token.initial_buy ? (token.initial_buy / 1000000).toFixed(1) + 'M' : '0');
                console.log('=================================');
            }
            
            const row = document.createElement('div');
            row.className = 'table-row';
            row.innerHTML = `
                <div class="col-symbol">
                    <div class="token-info">
                        <div class="token-symbol">${token.symbol}</div>
                        <div class="token-name">${token.name || 'N/A'}</div>
                    </div>
                </div>
                <div class="col-name">
                    <span class="full-name" title="${token.name || 'N/A'}">${token.name || 'N/A'}</span>
                </div>
                <div class="col-mint">
                    <span class="mint-address" title="${token.mint}">${token.mint.slice(0, 8)}...${token.mint.slice(-4)}</span>
                    <button class="btn-tiny copy-mint" data-mint="${token.mint}" title="Copy Full Mint Address">
                        <i class="fas fa-copy"></i>
                    </button>
                    <a href="https://solscan.io/token/${token.mint}" target="_blank" class="solscan-link" title="View on Solscan">
                        <i class="fas fa-external-link-alt"></i>
                    </a>
                </div>
                <div class="col-market-cap">$${typeof token.market_cap === 'number' ? token.market_cap.toLocaleString() : '0'}</div>
                <div class="col-price">$${typeof token.price === 'number' ? token.price.toFixed(8) : '0.00000000'}</div>
                <div class="col-pool-data">
                    <div class="pool-info">
                        <small>SOL: ${typeof token.sol_in_pool === 'number' ? token.sol_in_pool.toFixed(2) : 'N/A'}</small>
                        <small>Tokens: ${typeof token.tokens_in_pool === 'number' ? (token.tokens_in_pool / 1000000000).toFixed(2) + 'B' : 'N/A'}</small>
                    </div>
                </div>
                <div class="col-initial-buy">
                    <span class="initial-buy">${this.formatTokenAmount(token.initial_buy)}</span>
                </div>
                <div class="col-time">${this.formatTime(token.created_timestamp || token.timestamp)}</div>
                <div class="col-links">
                    <a href="https://pump.fun/${token.mint}" target="_blank" class="pump-link" title="View on Pump.Fun">
                        <i class="fas fa-rocket"></i>
                    </a>
                </div>
                <div class="col-action">
                    <button class="btn buy-btn" data-mint="${token.mint}" title="Buy ${token.symbol}">
                        <i class="fas fa-shopping-cart"></i>
                        <span>Buy</span>
                    </button>
                </div>
            `;
            tbody.appendChild(row);
        });
        // Add copy-to-clipboard functionality
        tbody.querySelectorAll('.copy-mint').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const mint = btn.dataset.mint;
                navigator.clipboard.writeText(mint);
                this.showToast('Mint address copied!', 'success');
                e.stopPropagation();
            });
        });
    }
    
    updatePositionsTable() {
        const tbody = document.querySelector('#positionsTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (this.positions.length === 0) {
            tbody.innerHTML = '<div class="empty-state"><i class="fas fa-briefcase"></i><p>No active positions</p></div>';
            return;
        }
        
        this.positions.forEach(position => {
            const row = document.createElement('div');
            row.className = 'position-row';
            const pnlClass = position.current_pnl >= 0 ? 'profit' : 'loss';
            
            row.innerHTML = `
                <div class="col-token">
                    <div class="token-info">
                        <strong>${position.token_symbol}</strong>
                        <small>${position.token_name}</small>
                    </div>
                </div>
                <div class="col-entry">$${position.entry_price.toFixed(8)}</div>
                <div class="col-current">$${position.current_price.toFixed(8)}</div>
                <div class="col-amount">${position.token_amount.toLocaleString()}</div>
                <div class="col-pnl ${pnlClass}">
                    ${position.current_pnl >= 0 ? '+' : ''}${position.current_pnl.toFixed(4)} SOL
                    <br>
                    <small>(${position.current_pnl_percent >= 0 ? '+' : ''}${position.current_pnl_percent.toFixed(1)}%)</small>
                </div>
                <div class="col-status">${position.is_active ? 'Active' : 'Closed'}</div>
                <div class="col-action">
                    ${position.is_active ? `<button class="btn btn-small sell-btn" data-mint="${position.token_mint}">
                        <i class="fas fa-sign-out-alt"></i> Sell
                    </button>` : '-'}
                </div>
            `;
            tbody.appendChild(row);
        });
    }
    
    updateTransactionsTable() {
        const container = document.querySelector('#transactionsList');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (this.transactions.length === 0) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-exchange-alt"></i><p>No transactions yet</p></div>';
            return;
        }
        
        this.transactions.slice(0, 20).forEach(tx => {
            const transaction = document.createElement('div');
            transaction.className = `transaction-item ${tx.type}`;
            
            transaction.innerHTML = `
                <div class="tx-header">
                    <span class="tx-type ${tx.type}">${tx.type.toUpperCase()}</span>
                    <span class="tx-symbol">${tx.symbol}</span>
                    <span class="tx-time">${this.formatTime(tx.timestamp)}</span>
                </div>
                <div class="tx-details">
                    <span>Amount: ${tx.amount_sol.toFixed(4)} SOL</span>
                    <span>Tokens: ${tx.amount_tokens ? tx.amount_tokens.toLocaleString() : '-'}</span>
                    ${tx.profit_loss !== undefined ? 
                        `<span class="tx-pnl ${tx.profit_loss >= 0 ? 'profit' : 'loss'}">
                            P&L: ${tx.profit_loss >= 0 ? '+' : ''}${tx.profit_loss.toFixed(4)} SOL
                        </span>` : ''
                    }
                </div>
                <div class="tx-signature">
                    <a href="https://solscan.io/tx/${tx.signature}" target="_blank" class="signature-link">
                        View on Solscan: ${this.truncateSignature(tx.signature)}
                    </a>
                </div>
            `;
            container.appendChild(transaction);
        });
    }
    
    updateTotalPnL() {
        let totalPnL = 0;
        this.positions.forEach(pos => {
            totalPnL += pos.current_pnl || 0;
        });
        
        const pnlElement = document.getElementById('totalPnl');
        if (pnlElement) {
            pnlElement.textContent = `${totalPnL >= 0 ? '+' : ''}${totalPnL.toFixed(4)} SOL`;
            pnlElement.className = totalPnL >= 0 ? 'stat-value pnl profit' : 'stat-value pnl loss';
        }
        
        // Update active positions count
        const activePositionsElement = document.getElementById('activePositions');
        if (activePositionsElement) {
            activePositionsElement.textContent = this.positions.length;
        }
    }
    
    addLog(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        this.logs.unshift({
            timestamp,
            message,
            type
        });
        
        if (this.logs.length > 100) {
            this.logs = this.logs.slice(0, 100);
        }
        
        this.updateLogsTable();
    }
    
    updateLogsTable() {
        const logsContent = document.getElementById('logsContent');
        if (!logsContent) return;
        
        logsContent.innerHTML = '';
        
        this.logs.slice(0, 50).forEach(log => {
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry ${log.type}`;
            logEntry.innerHTML = `
                <span class="log-time">${log.timestamp}</span>
                <span class="log-type">${log.type.toUpperCase()}</span>
                <span class="log-message">${log.message}</span>
            `;
            logsContent.appendChild(logEntry);
        });
    }
    
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        const targetBtn = document.querySelector(`[data-tab="${tabName}"]`);
        if (targetBtn) {
            targetBtn.classList.add('active');
        }
        
        // Update tab content
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('active');
        });
        const targetPane = document.getElementById(tabName);
        if (targetPane) {
            targetPane.classList.add('active');
        }
    }
    
    validateSettings() {
        const solAmount = parseFloat(document.getElementById('solAmount').value);
        const maxPositions = parseInt(document.getElementById('maxPositions').value);
        const profitTarget = parseFloat(document.getElementById('profitTarget').value);
        const stopLoss = parseFloat(document.getElementById('stopLoss').value);
        
        let isValid = true;
        
        if (solAmount <= 0 || solAmount > 10) {
            isValid = false;
        }
        if (maxPositions <= 0 || maxPositions > 20) {
            isValid = false;
        }
        if (profitTarget <= 0 || profitTarget > 1000) {
            isValid = false;
        }
        if (stopLoss <= 0 || stopLoss > 100) {
            isValid = false;
        }
        
        document.getElementById('updateSettingsBtn').disabled = !isValid;
    }
    
    loadInitialData() {
        // Load bot status from backend
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.updateUIFromStatus(data.data);
                } else {
                    this.addLog('Failed to load bot status', 'error');
                }
            })
            .catch(error => {
                console.error('Error loading initial data:', error);
                this.addLog('Failed to connect to backend', 'error');
            });
    }
    
    updateUIFromStatus(status) {
        // Update wallet info
        if (status.wallet_connected) {
            document.getElementById('walletForm').style.display = 'none';
            document.getElementById('walletInfo').style.display = 'block';
            document.getElementById('walletAddress').textContent = status.wallet_address;
            document.getElementById('walletBalance').textContent = `${status.sol_balance.toFixed(3)} SOL`;
            document.getElementById('solBalance').textContent = status.sol_balance.toFixed(3);
            this.walletConnected = true;
        } else {
            document.getElementById('walletForm').style.display = 'block';
            document.getElementById('walletInfo').style.display = 'none';
            this.walletConnected = false;
        }
        
        // Update bot status
        this.botRunning = status.is_running;
        this.updateBotControls();
        
        // Update settings
        if (status.settings) {
            document.getElementById('solAmount').value = status.settings.sol_per_snipe;
            document.getElementById('maxPositions').value = status.settings.max_positions;
            document.getElementById('profitTarget').value = status.settings.profit_target_percent;
            document.getElementById('stopLoss').value = status.settings.stop_loss_percent;
            document.getElementById('minMarketCap').value = status.settings.min_market_cap;
            document.getElementById('maxMarketCap').value = status.settings.max_market_cap;
            document.getElementById('autoBuy').checked = status.settings.auto_buy;
            document.getElementById('autoSell').checked = status.settings.auto_sell;
        }
        
        // Update header stats
        document.getElementById('totalPnl').textContent = `${status.total_pnl >= 0 ? '+' : ''}${status.total_pnl.toFixed(4)} SOL`;
        document.getElementById('activePositions').textContent = status.active_positions;
    }
    
    startUIUpdates() {
        // Update UI every second
        setInterval(() => {
            this.updateTotalPnL();
        }, 1000);
    }
    
    updateConnectionStatus(status, connected) {
        const element = document.getElementById('connectionStatus');
        if (element) {
            element.textContent = status;
            element.className = `connection-status ${connected ? 'connected' : 'disconnected'}`;
        }
    }
    
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <i class="fas fa-${this.getToastIcon(type)}"></i>
            <span>${message}</span>
        `;
        
        document.getElementById('toastContainer').appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    }
    
    getToastIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    showLoading(show) {
        document.getElementById('loadingOverlay').style.display = show ? 'flex' : 'none';
    }
    
    truncateAddress(address) {
        return `${address.slice(0, 6)}...${address.slice(-4)}`;
    }
    
    truncateSignature(signature) {
        return `${signature.slice(0, 8)}...${signature.slice(-8)}`;
    }
    
    formatTime(timestamp) {
        if (!timestamp) return 'now';
        
        const now = Date.now();
        const time = timestamp * 1000; // Convert from seconds to milliseconds
        const diff = now - time;
        
        if (diff < 60000) return 'now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        
        const date = new Date(time);
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
        });
    }
    
    formatTokenAmount(amount) {
        if (amount === null || amount === undefined) return 'N/A';
        if (amount < 1000000) return `${(amount / 1000).toFixed(0)}K`;
        return `${(amount / 1000000).toFixed(0)}M`;
    }
    
    // Clear methods for tables
    clearTokens() {
        this.newTokens = [];
        this.updateNewTokensTable();
        this.addLog('Cleared new tokens table', 'info');
        this.showToast('Tokens table cleared', 'success');
    }
    
    clearTransactions() {
        this.transactions = [];
        this.updateTransactionsTable();
        this.addLog('Cleared transactions table', 'info');
        this.showToast('Transactions table cleared', 'success');
    }
    
    clearLogs() {
        this.logs = [];
        this.updateLogsTable();
        this.showToast('Logs table cleared', 'success');
    }

    updateBotControls() {
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const statusText = document.getElementById('statusText');
        const statusDot = document.getElementById('statusDot');
        
        if (this.botRunning) {
            startBtn.disabled = true;
            stopBtn.disabled = false;
            statusText.textContent = 'Monitoring';
            statusDot.className = 'status-dot monitoring';
        } else if (this.walletConnected) {
            startBtn.disabled = false;
            stopBtn.disabled = true;
            statusText.textContent = 'Ready';
            statusDot.className = 'status-dot ready';
        } else {
            startBtn.disabled = true;
            stopBtn.disabled = true;
            statusText.textContent = 'Connect Wallet';
            statusDot.className = 'status-dot stopped';
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.sniperBot = new SniperBotApp();
}); 