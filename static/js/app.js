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
        this.loadStoredPrivateKey();
        this.loadInitialData();
    }
    
    setupEventListeners() {
        // Wallet connection
        document.getElementById('connectWalletBtn').addEventListener('click', () => this.connectWallet());
        document.getElementById('editKeyBtn').addEventListener('click', () => this.editPrivateKey());
        document.getElementById('storePrivateKey').addEventListener('change', (e) => this.handleStorePrivateKeyChange(e));
        
        // Bot controls
        document.getElementById('startBtn').addEventListener('click', () => this.startBot());
        document.getElementById('stopBtn').addEventListener('click', () => this.stopBot());
        document.getElementById('updateSettingsBtn').addEventListener('click', () => this.updateSettings());
        
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
    
    loadStoredPrivateKey() {
        try {
            const storedKey = localStorage.getItem('pump_sniper_private_key');
            const shouldStore = localStorage.getItem('pump_sniper_store_key') === 'true';
            
            if (storedKey && shouldStore) {
                document.getElementById('privateKeyInput').value = storedKey;
                document.getElementById('storePrivateKey').checked = true;
                document.getElementById('securityWarning').style.display = 'block';
                this.addLog('Private key loaded from storage', 'info');
            }
        } catch (error) {
            console.error('Failed to load stored private key:', error);
        }
    }

    handleStorePrivateKeyChange(event) {
        const shouldStore = event.target.checked;
        const securityWarning = document.getElementById('securityWarning');
        
        // Show/hide security warning
        if (shouldStore) {
            securityWarning.style.display = 'block';
        } else {
            securityWarning.style.display = 'none';
        }
        
        try {
            if (shouldStore) {
                const privateKey = document.getElementById('privateKeyInput').value.trim();
                if (privateKey) {
                    localStorage.setItem('pump_sniper_private_key', privateKey);
                    localStorage.setItem('pump_sniper_store_key', 'true');
                    this.showToast('Private key saved to local storage', 'success');
                } else {
                    this.showToast('Enter a private key first to save it', 'warning');
                    event.target.checked = false;
                    securityWarning.style.display = 'none';
                }
            } else {
                localStorage.removeItem('pump_sniper_private_key');
                localStorage.removeItem('pump_sniper_store_key');
                this.showToast('Private key removed from storage', 'info');
            }
        } catch (error) {
            console.error('Failed to handle private key storage:', error);
            this.showToast('Failed to save private key', 'error');
            event.target.checked = false;
            securityWarning.style.display = 'none';
        }
    }

    editPrivateKey() {
        if (!this.walletConnected) {
            return;
        }

        // Show input dialog for editing private key
        const currentKey = localStorage.getItem('pump_sniper_private_key') || '';
        const newKey = prompt('Enter new private key:', currentKey);
        
        if (newKey !== null && newKey.trim() !== '') {
            // Update the input field
            document.getElementById('privateKeyInput').value = newKey.trim();
            
            // Update localStorage if storing is enabled
            if (document.getElementById('storePrivateKey').checked) {
                try {
                    localStorage.setItem('pump_sniper_private_key', newKey.trim());
                    this.showToast('Private key updated', 'success');
                } catch (error) {
                    console.error('Failed to update stored private key:', error);
                    this.showToast('Failed to update stored key', 'error');
                }
            }
            
            // Disconnect current wallet and prompt to reconnect
            this.walletConnected = false;
            document.getElementById('walletInfo').style.display = 'none';
            document.getElementById('walletForm').style.display = 'block';
            document.getElementById('statusText').textContent = 'Private key updated - please reconnect';
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = true;
            
            this.showToast('Please reconnect with the new private key', 'info');
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
            const response = await fetch('/api/connect_wallet', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ private_key: privateKey })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.walletConnected = true;
                
                // Update UI
                document.getElementById('walletAddress').textContent = this.truncateAddress(result.wallet_address);
                document.getElementById('walletBalance').textContent = result.sol_balance.toFixed(4);
                document.getElementById('statusText').textContent = 'Wallet Connected';
                document.getElementById('walletInfo').style.display = 'block';
                document.getElementById('walletForm').style.display = 'none';
                
                // Handle private key storage
                if (document.getElementById('storePrivateKey').checked) {
                    try {
                        localStorage.setItem('pump_sniper_private_key', privateKey);
                        localStorage.setItem('pump_sniper_store_key', 'true');
                    } catch (error) {
                        console.error('Failed to store private key:', error);
                        this.showToast('Failed to save private key to storage', 'warning');
                    }
                }
                
                // Clear private key field for security if not storing
                if (!document.getElementById('storePrivateKey').checked) {
                    document.getElementById('privateKeyInput').value = '';
                }
                
                this.showToast('Wallet connected successfully!', 'success');
                this.addLog(`Wallet connected: ${result.wallet_address}`, 'success');
                
                // Enable bot controls
                document.getElementById('startBtn').disabled = false;
                
            } else {
                this.showToast(`Failed to connect wallet: ${result.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Wallet connection error:', error);
            this.showToast('Wallet connection failed', 'error');
        }
        
        this.showLoading(false);
    }
    
    async startBot() {
        if (!this.walletConnected) {
            this.showToast('Please connect wallet first', 'error');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/start_monitoring', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.botRunning = true;
                document.getElementById('statusText').textContent = 'Bot Running';
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
                
                this.showToast('Bot started successfully!', 'success');
                this.addLog('Bot monitoring started', 'success');
                
            } else {
                this.showToast(`Failed to start bot: ${result.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Start bot error:', error);
            this.showToast('Failed to start bot', 'error');
        }
        
        this.showLoading(false);
    }
    
    async stopBot() {
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/stop_monitoring', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.botRunning = false;
                document.getElementById('statusText').textContent = 'Bot Stopped';
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
                
                this.showToast('Bot stopped successfully!', 'info');
                this.addLog('Bot monitoring stopped', 'info');
                
            } else {
                this.showToast(`Failed to stop bot: ${result.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Stop bot error:', error);
            this.showToast('Failed to stop bot', 'error');
        }
        
        this.showLoading(false);
    }
    
    async updateSettings() {
        try {
            const response = await fetch('/api/update_settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    sol_amount: parseFloat(document.getElementById('solAmount').value),
                    max_positions: parseInt(document.getElementById('maxPositions').value),
                    profit_target: parseFloat(document.getElementById('profitTarget').value),
                    stop_loss: parseFloat(document.getElementById('stopLoss').value),
                    auto_buy_enabled: document.getElementById('autoBuy').checked,
                    auto_sell_enabled: document.getElementById('autoSell').checked,
                    min_market_cap: parseFloat(document.getElementById('minMarketCap').value),
                    max_market_cap: parseFloat(document.getElementById('maxMarketCap').value)
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('Settings updated successfully!', 'success');
                this.addLog('Bot settings updated', 'info');
            } else {
                this.showToast(`Failed to update settings: ${result.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Update settings error:', error);
            this.showToast('Failed to update settings', 'error');
        }
    }
    
    async buyToken(mint) {
        if (!this.walletConnected) {
            this.showToast('Wallet not connected', 'error');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/buy_token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ mint: mint })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('Buy order executed!', 'success');
            } else {
                this.showToast(`Buy failed: ${result.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Buy token error:', error);
            this.showToast('Buy order failed', 'error');
        }
        
        this.showLoading(false);
    }
    
    async sellPosition(mint) {
        if (!this.walletConnected) {
            this.showToast('Wallet not connected', 'error');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/sell_position', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ mint: mint })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('Sell order executed!', 'success');
            } else {
                this.showToast(`Sell failed: ${result.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Sell position error:', error);
            this.showToast('Sell order failed', 'error');
        }
        
        this.showLoading(false);
    }
    
    handleNewToken(token) {
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
        
        this.newTokens.forEach(token => {
            const row = document.createElement('div');
            row.className = 'table-row';
            row.innerHTML = `
                <div class="col-symbol">
                    <div class="token-info">
                        <strong>${token.symbol}</strong>
                        <small>${token.name}</small>
                    </div>
                </div>
                <div class="col-name">${token.name}</div>
                <div class="col-mint">
                    <span class="mint-address">${token.mint}</span>
                    <button class="btn btn-tiny copy-mint" data-mint="${token.mint}" title="Copy Mint"><i class="fas fa-copy"></i></button>
                </div>
                <div class="col-market-cap">$${token.market_cap ? token.market_cap.toLocaleString() : '0'}</div>
                <div class="col-price">$${token.price ? token.price.toFixed(8) : '0.00000000'}</div>
                <div class="col-pool-data">
                    <div class="pool-info">
                        <small>SOL: ${token.sol_in_pool || 0}</small>
                        <small>Tokens: ${token.tokens_in_pool ? (token.tokens_in_pool / 1000000).toFixed(1) + 'M' : '0'}</small>
                    </div>
                </div>
                <div class="col-initial-buy">
                    <span class="initial-buy">${token.initial_buy ? (token.initial_buy / 1000000).toFixed(1) + 'M' : '0'}</span>
                </div>
                <div class="col-time">${this.formatTime(token.created_timestamp || token.timestamp)}</div>
                <div class="col-links">
                    <a href="https://pump.fun/${token.mint}" target="_blank" class="pump-link" title="View on Pump.Fun">
                        <i class="fas fa-rocket"></i>
                    </a>
                    <a href="https://solscan.io/token/${token.mint}" target="_blank" class="solscan-link" title="View on Solscan">
                        <i class="fas fa-search"></i>
                    </a>
                </div>
                <div class="col-action">
                    <button class="btn btn-small buy-btn" data-mint="${token.mint}">
                        <i class="fas fa-shopping-cart"></i> Buy
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
    
    async loadInitialData() {
        try {
            const response = await fetch('/api/get_status');
            const status = await response.json();
            
            if (status.success && status.wallet_connected) {
                this.walletConnected = true;
                document.getElementById('walletAddress').textContent = this.truncateAddress(status.wallet_address);
                document.getElementById('walletBalance').textContent = status.sol_balance.toFixed(4);
                document.getElementById('statusText').textContent = 'Wallet Connected';
                document.getElementById('walletInfo').style.display = 'block';
                document.getElementById('walletForm').style.display = 'none';
                document.getElementById('startBtn').disabled = false;
            } else {
                // Show wallet form if not connected
                document.getElementById('walletInfo').style.display = 'none';
                document.getElementById('walletForm').style.display = 'block';
            }
            
            if (status.success && status.is_monitoring) {
                this.botRunning = true;
                document.getElementById('statusText').textContent = 'Bot Running';
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
            }
            
            // Load settings if available
            if (status.success && status.settings) {
                const settings = status.settings;
                document.getElementById('solAmount').value = settings.sol_amount_per_snipe;
                document.getElementById('maxPositions').value = settings.max_concurrent_positions;
                document.getElementById('profitTarget').value = settings.profit_target_percent;
                document.getElementById('stopLoss').value = settings.stop_loss_percent;
                document.getElementById('autoBuy').checked = settings.auto_buy_enabled;
                document.getElementById('autoSell').checked = settings.auto_sell_enabled;
                document.getElementById('minMarketCap').value = settings.min_market_cap;
                document.getElementById('maxMarketCap').value = settings.max_market_cap;
            }
            
            // Load positions
            if (status.success && status.positions) {
                this.positions = status.positions;
                this.updatePositionsTable();
                this.updateTotalPnL();
            }
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
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
        return new Date(timestamp).toLocaleTimeString();
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.sniperBot = new SniperBotApp();
}); 