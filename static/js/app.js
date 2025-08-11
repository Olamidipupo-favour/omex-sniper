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
        
        // Add initial log message
        this.addLog('Pump.Fun Sniper Bot initialized', 'info');
        
        this.initializeApp();
        this.initializeTabStates();
    }
    
    initializeTabStates() {
        console.log('🔧 Initializing tab states...');
        
        // Hide ALL tab content first by removing active class
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        // Show ONLY monitoring tab by default
        const monitoringContent = document.getElementById('monitoring-content');
        if (monitoringContent) {
            monitoringContent.classList.add('active');
            console.log('✅ Monitoring tab initialized as active');
        }
        
        // Set monitoring tab button as active
        const monitoringTab = document.querySelector('[data-tab="monitoring"]');
        if (monitoringTab) {
            monitoringTab.classList.add('active');
        }
        
        console.log('✅ Tab states initialized');
    }
    
    initializeApp() {
        this.setupEventListeners();
        this.connectWebSocket();
        this.startUIUpdates();
        
        // Load initial data immediately
        this.loadInitialData();
    }
    
    setupEventListeners() {
        // Wallet connection
        document.getElementById('connectWalletBtn').addEventListener('click', () => this.connectWallet());
        document.getElementById('disconnectWalletBtn').addEventListener('click', () => this.disconnectWallet());
        
        // Bot controls
        document.getElementById('startBtn').addEventListener('click', () => this.startBot());
        document.getElementById('stopBtn').addEventListener('click', () => this.stopBot());
        document.getElementById('updateSettingsBtn').addEventListener('click', () => this.updateSettings());
        
        // Clear buttons
        document.getElementById('clearTokensBtn').addEventListener('click', () => this.clearTokens());
        document.getElementById('clearLogsBtn').addEventListener('click', () => this.clearLogs());
        
        // Note: clearTransactions is handled by onclick in HTML
        
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabName = e.currentTarget.dataset.tab;
                console.log('Tab clicked:', tabName);
                this.switchTab(tabName);
            });
        });
        
        // Settings form inputs
        document.querySelectorAll('.settings-form input').forEach(input => {
            input.addEventListener('change', () => this.validateSettings());
        });
        
        // Token age filter dropdown
        document.getElementById('tokenAgeFilter').addEventListener('change', (e) => {
            const customDaysContainer = document.getElementById('customDaysContainer');
            if (e.target.value === 'custom_days') {
                customDaysContainer.style.display = 'block';
            } else {
                customDaysContainer.style.display = 'none';
            }
        });
        
        // Manual trade buttons (will be added dynamically)
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('buy-btn')) {
                // Find the token data from the newTokens array
                const mint = e.target.dataset.mint;
                const token = this.newTokens.find(t => t.mint === mint);
                if (token) {
                    this.buyToken(mint, token.symbol, token.name);
                } else {
                    this.buyToken(mint, 'Unknown', 'Unknown');
                }
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
            
            // WebSocket event handlers
            this.socket.on('new_token', (data) => {
                this.handleNewToken(data);
            });
            
            this.socket.on('position_update', (data) => {
                console.log('📡 WebSocket: Position update received:', data);
                console.log('📊 Position update action:', data.action);
                console.log('📊 Position update mint:', data.mint);
                this.handlePositionUpdate(data);
            });
            
            this.socket.on('transaction', (data) => {
                this.handleTransaction(data);
            });
            
            this.socket.on('transaction_update', (data) => {
                this.handleTransactionUpdate(data);
            });
            
            this.socket.on('price_update', (data) => {
                console.log('📡 WebSocket: Price update received:', data);
                console.log('📊 Price update mint:', data.mint);
                console.log('📊 Price update current_price:', data.current_price);
                this.handlePriceUpdate(data);
            });
            
            this.socket.on('trade_update', (data) => {
                this.handleTradeUpdate(data);
            });
            
            this.socket.on('auto_buy_success', (data) => {
                this.handleAutoBuySuccess(data);
            });
            
            this.socket.on('auto_buy_error', (data) => {
                this.handleAutoBuyError(data);
            });
            
            this.socket.on('error', (data) => {
                this.handleError(data);
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
    
    async disconnectWallet() {
        if (!this.walletConnected) {
            this.showToast('No wallet connected', 'info');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/wallet/disconnect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.walletConnected = false;
                
                // Show wallet form and hide wallet info
                document.getElementById('walletForm').style.display = 'block';
                document.getElementById('walletInfo').style.display = 'none';
                
                // Clear wallet display
                document.getElementById('walletAddress').textContent = '-';
                document.getElementById('walletBalance').textContent = '-';
                document.getElementById('solBalance').textContent = '0.000';
                
                // Clear private key input
                document.getElementById('privateKeyInput').value = '';
                
                this.showToast('Wallet disconnected successfully!', 'success');
                this.addLog('Wallet disconnected', 'info');
                
                this.updateBotControls();
            } else {
                this.showToast(result.error || 'Failed to disconnect wallet', 'error');
            }
        } catch (error) {
            console.error('Wallet disconnection error:', error);
            this.showToast('Disconnection failed', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async startBot() {
        if (!this.walletConnected) {
            this.showToast('Please connect your wallet first', 'warning');
            return;
        }
        
        // Refresh status from backend before attempting to start
        try {
            const statusResponse = await fetch('/api/status');
            const statusResult = await statusResponse.json();
            if (statusResult.success) {
                this.updateUIFromStatus(statusResult.data);
            }
        } catch (error) {
            console.error('Error refreshing status:', error);
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
                // Refresh status again to sync with backend
                this.loadInitialData();
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
                // Refresh status to sync with backend
                this.loadInitialData();
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
                min_liquidity: parseFloat(document.getElementById('minLiquidity').value),
                min_holders: parseInt(document.getElementById('minHolders').value),
                auto_buy: document.getElementById('autoBuy').checked,
                auto_sell: document.getElementById('autoSell').checked,
                token_age_filter: document.getElementById('tokenAgeFilter').value,
                custom_days: parseInt(document.getElementById('customDays').value),
                include_pump_tokens: document.getElementById('includePumpTokens').checked,
                transaction_type: document.getElementById('transactionType').value,
                priority_fee: parseFloat(document.getElementById('priorityFee').value)
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
    
    async buyToken(mint, symbol, name) {
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
                    amount: parseFloat(document.getElementById('solAmount').value),
                    symbol: symbol,
                    name: name
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('Buy order executed successfully!', 'success');
                this.addLog(`Buy order executed for ${symbol} (${mint.slice(0, 8)}...)`, 'success');
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
    
    handlePositionUpdate(data) {
        console.log('📱 Position update received:', data);
        console.log('📊 Action type:', data.action);
        
        // Find existing position
        const existingIndex = this.positions.findIndex(p => p.mint === data.mint || p.token_mint === data.mint);
        let position;
        
        if (data.action === 'buy') {
            // New position created from buy_token
            console.log('🆕 Buy action received:', data);
            
            if (existingIndex === -1) {
                // Create new position with initial data (entry_price and token_amount will be 0)
                position = {
                    mint: data.mint,
                    token_mint: data.mint,
                    token_symbol: data.token_symbol || 'Unknown',
                    token_name: data.token_name || 'Unknown',
                    entry_price: 0,  // Will be updated by metadata_update
                    current_price: 0,
                    token_amount: 0,  // Will be updated by metadata_update
                    sol_amount: data.sol_amount || 0,
                    current_pnl: 0,
                    current_pnl_percent: 0,
                    is_active: true,
                    entry_timestamp: Date.now() / 1000
                };
                
                this.positions.push(position);
                console.log('✅ Created new position from buy action:', position);
            } else {
                // Position already exists, update only non-critical data
                position = this.positions[existingIndex];
                position.token_symbol = data.token_symbol || position.token_symbol;
                position.token_name = data.token_name || position.token_name;
                position.sol_amount = data.sol_amount || position.sol_amount;
                // DO NOT update entry_price or token_amount from buy action
                console.log('✅ Updated existing position from buy action (no entry_price/token_amount update):', position);
            }
            
            // Show success notification
            this.showToast(`Position created for ${data.token_symbol || 'Unknown'}`, 'success');
            
        } else if (data.action === 'metadata_update') {
            // Position metadata updated from WebSocket (real data)
            console.log('📝 Metadata update received:', data);
            
            if (existingIndex === -1) {
                // Create new position if it doesn't exist
                position = {
                    mint: data.mint,
                    token_mint: data.mint,
                    token_symbol: data.token_symbol || 'Unknown',
                    token_name: data.token_name || 'Unknown',
                    entry_price: data.entry_price || 0,
                    current_price: 0,
                    token_amount: data.token_amount || 0,
                    sol_amount: 0,  // Will be updated by buy action if it comes later
                    current_pnl: 0,
                    current_pnl_percent: 0,
                    is_active: true,
                    entry_timestamp: Date.now() / 1000
                };
                
                this.positions.push(position);
                console.log('✅ Created new position from metadata_update:', position);
            } else {
                // Update existing position with real data
                position = this.positions[existingIndex];
                position.token_symbol = data.token_symbol || position.token_symbol;
                position.token_name = data.token_name || position.token_name;
                position.entry_price = data.entry_price || position.entry_price;  // Only metadata_update can update this
                position.token_amount = data.token_amount || position.token_amount;  // Only metadata_update can update this
                console.log('✅ Updated existing position from metadata_update (with real data):', position);
            }
            
        } else if (data.action === 'sell') {
            // Position sold
            console.log('💸 Position sold:', data);
            
            // Remove from positions array
            this.positions = this.positions.filter(p => p.mint !== data.mint && p.token_mint !== data.mint);
            
            // Show notification
            const pnlText = data.pnl_percent ? ` (${data.pnl_percent.toFixed(2)}%)` : '';
            this.showNotification(`Position sold${pnlText}`, 'success');
        }
        
        // Always update the positions table and header stats
        this.updatePositionsTable();
        this.updateTotalPnL();
        
        // Update header stats
        const activePositionsElement = document.getElementById('activePositions');
        if (activePositionsElement) {
            activePositionsElement.textContent = this.positions.length;
        }
        
        console.log('📊 Current positions count:', this.positions.length);
    }
    
    handleTransaction(data) {
        // Update transactions table if we're on the transactions tab
        if (document.getElementById('transactions-content').style.display !== 'none') {
            this.fetchTransactions();
        }
        
        // Show notification for new transactions
        const actionText = data.action === 'buy' ? 'Buy' : 'Sell';
        this.showNotification(`${actionText} transaction completed`, 'success');
    }
    
    handleError(data) {
        this.showNotification(data.message, 'error');
    }
    
    handleBuyError(error) {
        console.error('Buy error:', error);
        let errorMessage = error.message || 'Buy failed';
        
        // Handle specific error types
        if (error.type === 'buy_failed') {
            if (errorMessage.includes('Insufficient SOL balance')) {
                errorMessage = '❌ Insufficient SOL balance. Please add more SOL to your wallet.';
            } else if (errorMessage.includes('insufficient_balance')) {
                errorMessage = '❌ Insufficient balance for this transaction.';
            }
        }
        
        this.showToast(errorMessage, 'error');
        this.addLog(`Buy failed: ${errorMessage}`, 'error');
    }
    
    handleAutoBuySuccess(data) {
        console.log('Auto-buy success:', data);
        const message = `✅ Auto-buy successful: ${data.token_symbol} (${data.sol_amount} SOL)`;
        this.showToast(message, 'success');
        this.addLog(`Auto-buy: ${data.token_symbol} - ${data.sol_amount} SOL`, 'success');
    }
    
    handleAutoBuyError(data) {
        console.error('Auto-buy error:', data);
        let errorMessage = data.message || 'Auto-buy failed';
        
        // Handle specific error types
        if (data.error === 'insufficient_balance') {
            errorMessage = `❌ Auto-buy failed: Insufficient balance for ${data.token_symbol}. Need ${data.required_amount} SOL, have ${data.available_balance} SOL.`;
        } else if (data.error === 'buy_failed') {
            errorMessage = `❌ Auto-buy failed for ${data.token_symbol}: Transaction failed`;
        } else if (data.error === 'exception') {
            errorMessage = `❌ Auto-buy error for ${data.token_symbol}: ${data.message}`;
        }
        
        this.showToast(errorMessage, 'error');
        this.addLog(`Auto-buy error: ${data.token_symbol} - ${errorMessage}`, 'error');
    }
    
    handleTransactionUpdate(data) {
        console.log('Transaction update:', data);
        this.addLog(`Transaction updated: ${data.mint.slice(0, 8)}... - Amount: ${data.token_amount_formatted}`, 'info');
        
        // Update the transaction in the UI if it exists
        this.updateTransactionsTable();
    }
    
    handlePriceUpdate(data) {
        console.log('💰 Price update received:', data);
        
        // Find and update the position in our local array
        const position = this.positions.find(p => p.mint === data.mint || p.token_mint === data.mint);
        if (position) {
            position.current_price = data.current_price;
            position.current_pnl = data.current_pnl;
            position.current_pnl_percent = data.current_pnl_percent;
            
            console.log('✅ Updated position with price data:', position);
            
            // Update the positions table to reflect the new price
            this.updatePositionsTable();
            
            // Update total P&L
            this.updateTotalPnL();
            
            // Add log entry for significant price changes
            if (Math.abs(data.current_pnl_percent) > 5) {
                this.addLog(`💰 ${data.token_symbol}: ${data.current_pnl_percent >= 0 ? '+' : ''}${data.current_pnl_percent.toFixed(2)}% ($${data.current_price.toFixed(8)})`, 'info');
            }
        } else {
            console.warning('⚠️ Price update for unknown position:', data.mint);
        }
    }
    
    handleTradeUpdate(data) {
        console.log('Trade update:', data);
        
        // Add trade activity to logs
        const tradeType = data.txType === 'buy' ? '🟢 Buy' : '🔴 Sell';
        const trader = data.traderPublicKey ? data.traderPublicKey.slice(0, 8) + '...' : 'Unknown';
        const solAmount = data.solAmount ? data.solAmount.toFixed(4) : '0';
        const tokenAmount = data.tokenAmount ? this.formatTokenAmount(data.tokenAmount) : '0';
        
        this.addLog(`${tradeType}: ${trader} - ${solAmount} SOL for ${tokenAmount} tokens`, 'info');
        
        // Update positions table if this affects our positions
        if (this.positions.some(pos => pos.mint === data.mint)) {
            this.updatePositionsTable();
        }
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
                <div class="col-liquidity">${typeof token.liquidity === 'number' ? token.liquidity.toFixed(2) : '0.00'} SOL</div>
                <div class="col-holders">${typeof token.holders === 'number' ? token.holders.toLocaleString() : '0'}</div>
                <div class="col-pool-data">
                    <div class="pool-info">
                        <small>SOL: ${typeof token.sol_in_pool === 'number' ? token.sol_in_pool.toFixed(2) : 'N/A'}</small>
                        <small>Tokens: ${typeof token.tokens_in_pool === 'number' ? (token.tokens_in_pool / 1000000000).toFixed(2) + 'B' : 'N/A'}</small>
                    </div>
                </div>
                <div class="col-initial-buy">
                    <span class="initial-buy">${this.formatTokenAmount(token.initial_buy)}</span>
                </div>
                <div class="col-time">
                    <div>${this.formatTime(token.created_timestamp || token.timestamp)}</div>
                    ${token.age_days ? `<div class="age-info" title="Token age">${token.age_days.toFixed(1)}d old</div>` : ''}
                </div>
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
        console.log('🔍 updatePositionsTable called with local positions array');
        console.log('📊 Current positions:', this.positions);
        console.log('📊 Positions count:', this.positions.length);
        
        const tbody = document.querySelector('#positions-table tbody');
        if (!tbody) {
            console.error('❌ Could not find #positions-table tbody');
            console.log('🔍 Available elements with "positions" in ID:');
            document.querySelectorAll('[id*="positions"]').forEach(el => {
                console.log('- Found element:', el.id, el);
            });
            return;
        }
        
        console.log('✅ Found positions table body, updating...');
        tbody.innerHTML = '';
        
        if (this.positions.length === 0) {
            console.log('📝 No positions to display');
            tbody.innerHTML = '<tr><td colspan="7" class="no-data">No active positions</td></tr>';
            return;
        }
        
        console.log(`📊 Displaying ${this.positions.length} positions`);
        
        let totalInvested = 0;
        let totalPnl = 0;
        
        this.positions.forEach((position, index) => {
            console.log(`📋 Position ${index}:`, position);
            
            const row = document.createElement('tr');
            
            // Calculate P&L
            let currentValue = 0;
            let pnl = 0;
            let pnlPercent = 0;
            
            if (position.current_price && position.token_amount) {
                currentValue = position.token_amount * position.current_price;
                pnl = currentValue - (position.sol_amount || 0);
                pnlPercent = position.sol_amount > 0 ? (pnl / position.sol_amount) * 100 : 0;
            }
            
            totalInvested += position.sol_amount || 0;
            totalPnl += pnl;
            
            row.innerHTML = `
                <td>
                    <div class="token-info">
                        <span class="token-symbol">${position.token_symbol || 'Unknown'}</span>
                        <span class="token-mint">${this.truncateAddress(position.mint || position.token_mint || '')}</span>
                    </div>
                </td>
                <td>${position.entry_price ? `$${position.entry_price.toFixed(6)}` : 'N/A'}</td>
                <td>${position.current_price ? `$${position.current_price.toFixed(6)}` : 'N/A'}</td>
                <td>${(position.token_amount || 0).toLocaleString()}</td>
                <td class="${pnl >= 0 ? 'positive' : 'negative'}">
                    ${pnlPercent.toFixed(2)}% (${pnl.toFixed(4)} SOL)
                </td>
                <td><span class="status active">Active</span></td>
                <td>
                    <button class="btn-sell" onclick="app.sellPosition('${position.mint || position.token_mint}')">Sell</button>
                </td>
            `;
            
            tbody.appendChild(row);
            console.log(`✅ Added row for position ${index}: ${position.token_symbol}`);
        });
        
        // Update summary
        const summaryElement = document.querySelector('.positions-summary');
        if (summaryElement) {
            summaryElement.innerHTML = `
                Total Invested: ${totalInvested.toFixed(4)} SOL | 
                P&L: <span class="${totalPnl >= 0 ? 'positive' : 'negative'}">${totalPnl.toFixed(4)} SOL</span>
            `;
            console.log('✅ Updated positions summary');
        }
        
        console.log('✅ Positions table updated successfully');
        console.log('📊 Final table content length:', tbody.innerHTML.length);
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
        console.log('🔍 updateLogsTable called');
        
        // Check what elements exist
        const logsContent = document.getElementById('logsContent');
        const logsContainer = document.querySelector('.logs-container');
        const logsContentDiv = document.querySelector('#logs-content');
        
        console.log('🔍 HTML Elements check:');
        console.log('- #logsContent:', logsContent);
        console.log('- .logs-container:', logsContainer);
        console.log('- #logs-content:', logsContentDiv);
        
        if (!logsContent) {
            console.error('❌ Could not find #logsContent');
            console.log('🔍 Available elements with "logs" in ID:');
            document.querySelectorAll('[id*="logs"]').forEach(el => {
                console.log('- Found element:', el.id, el);
            });
            return;
        }
        
        logsContent.innerHTML = '';
        
        if (this.logs.length === 0) {
            console.log('📝 No logs to display');
            logsContent.innerHTML = '<div class="log-entry"><span class="timestamp">[00:00:00]</span><span class="message">No logs yet</span></div>';
            return;
        }
        
        console.log(`📊 Displaying ${this.logs.length} log entries`);
        
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
        
        console.log('✅ Logs table updated successfully');
    }
    
    switchTab(tabName) {
        console.log('🔍 Switching to tab:', tabName);
        
        // Debug: Check current state
        console.log('🔍 Current tab states:');
        document.querySelectorAll('.tab-content').forEach(content => {
            console.log(`- ${content.id}: display=${content.style.display}, has active class=${content.classList.contains('active')}`);
        });
        
        // Hide ALL tab content by removing active class only
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        // Remove active class from all tab buttons
        document.querySelectorAll('.tab-btn').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Show ONLY the selected tab content by adding active class
        const selectedContent = document.getElementById(tabName + '-content');
        
        if (selectedContent) {
            selectedContent.classList.add('active');
            console.log('✅ Showing content for:', tabName);
            console.log('✅ Content element:', selectedContent);
            console.log('✅ Content has active class:', selectedContent.classList.contains('active'));
        } else {
            console.error('❌ Could not find content for tab:', tabName);
        }
        
        // Add active class to selected tab button
        const selectedTab = document.querySelector(`[data-tab="${tabName}"]`);
        if (selectedTab) {
            selectedTab.classList.add('active');
            console.log('✅ Activated tab button:', tabName);
        } else {
            console.error('❌ Could not find tab button for:', tabName);
        }
        
        // Load data for specific tabs - but don't fetch from API for positions
        if (tabName === 'positions') {
            // Use local positions array instead of fetching from API
            console.log('📊 Using local positions array for positions tab');
            this.updatePositionsTable(); // This will use the local this.positions array
        } else if (tabName === 'transactions') {
            this.fetchTransactions();
        } else if (tabName === 'logs') {
            this.updateLogsTable();
        }
        
        // Debug: Check final state
        setTimeout(() => {
            console.log('🔍 Final tab states:');
            document.querySelectorAll('.tab-content').forEach(content => {
                console.log(`- ${content.id}: has active class=${content.classList.contains('active')}`);
            });
        }, 50);
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
        console.log('Loading initial data...');
        
        // Load bot status from backend
        fetch('/api/status')
            .then(response => response.json())
            .then(result => {
                console.log('Status response:', result);
                if (result.success) {
                    this.updateUIFromStatus(result.data);
                } else {
                    console.error('Failed to load bot status:', result.error);
                    this.addLog('Failed to load bot status', 'error');
                }
            })
            .catch(error => {
                console.error('Error loading initial data:', error);
                this.addLog('Failed to connect to backend', 'error');
            });
    }
    
    updateUIFromStatus(status) {
        console.log('Updating UI from status:', status);
        
        // Update wallet info
        if (status.wallet_connected && status.wallet_address) {
            console.log('Restoring wallet connection...');
            document.getElementById('walletForm').style.display = 'none';
            document.getElementById('walletInfo').style.display = 'block';
            document.getElementById('walletAddress').textContent = status.wallet_address;
            document.getElementById('walletBalance').textContent = `${status.sol_balance.toFixed(3)} SOL`;
            document.getElementById('solBalance').textContent = status.sol_balance.toFixed(3);
            this.walletConnected = true;
        } else {
            console.log('No wallet connected, showing wallet form...');
            document.getElementById('walletForm').style.display = 'block';
            document.getElementById('walletInfo').style.display = 'none';
            this.walletConnected = false;
        }
        
        // Update bot status
        this.botRunning = status.is_running;
        this.updateBotControls();
        
        // Update settings
        if (status.settings) {
            console.log('Restoring settings:', status.settings);
            document.getElementById('solAmount').value = status.settings.sol_per_snipe || 0.01;
            document.getElementById('maxPositions').value = status.settings.max_positions || 5;
            document.getElementById('profitTarget').value = status.settings.profit_target_percent || 50;
            document.getElementById('stopLoss').value = status.settings.stop_loss_percent || 20;
            document.getElementById('minMarketCap').value = status.settings.min_market_cap || 1000;
            document.getElementById('maxMarketCap').value = status.settings.max_market_cap || 100000;
            document.getElementById('minLiquidity').value = status.settings.min_liquidity || 100;
            document.getElementById('minHolders').value = status.settings.min_holders || 10;
            document.getElementById('autoBuy').checked = status.settings.auto_buy || false;
            document.getElementById('autoSell').checked = status.settings.auto_sell !== false; // Default to true
            document.getElementById('tokenAgeFilter').value = status.settings.token_age_filter || 'new_only';
            document.getElementById('customDays').value = status.settings.custom_days || 7;
            document.getElementById('includePumpTokens').checked = status.settings.include_pump_tokens !== false; // Default to true
            document.getElementById('transactionType').value = status.settings.transaction_type || 'local';
            document.getElementById('priorityFee').value = status.settings.priority_fee || 0.0001;
            
            // Show/hide custom days container based on filter selection
            const customDaysContainer = document.getElementById('customDaysContainer');
            if (status.settings.token_age_filter === 'custom_days') {
                customDaysContainer.style.display = 'block';
            } else {
                customDaysContainer.style.display = 'none';
            }
        }
        
        // Update header stats
        if (status.total_pnl !== undefined) {
            document.getElementById('totalPnl').textContent = `${status.total_pnl >= 0 ? '+' : ''}${status.total_pnl.toFixed(4)} SOL`;
        }
        if (status.active_positions !== undefined) {
            document.getElementById('activePositions').textContent = status.active_positions;
        }
        
        console.log('UI update completed');
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
        const tableBody = document.querySelector('#transactions-table tbody');
        if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="6" class="no-data">No transactions yet</td></tr>';
        }
        this.showNotification('Transaction history cleared', 'info');
    }
    
    clearLogs() {
        this.logs = [];
        this.updateLogsTable();
        this.showToast('Logs table cleared', 'success');
    }
    
    showNotification(message, type = 'info') {
        this.showToast(message, type);
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

    // Add new functions for positions and transactions
    async fetchPositions() {
        // This function is no longer needed since we use local positions array
        console.log('⚠️ fetchPositions() called but we use local positions array instead');
        console.log('📊 Current local positions:', this.positions);
        this.updatePositionsTable(); // Use local array
    }
    
    async fetchTransactions() {
        try {
            console.log('🔍 Fetching transactions...');
            const response = await fetch('/api/transactions?limit=50');
            const data = await response.json();
            
            console.log('📊 Transactions API response:', data);
            
            if (data.success) {
                console.log('✅ Transactions data received:', data.transactions);
                this.updateTransactionsTable(data.transactions);
            } else {
                console.error('❌ Failed to fetch transactions:', data.error);
            }
        } catch (error) {
            console.error('❌ Error fetching transactions:', error);
        }
    }
    
    updateTransactionsTable(transactions) {
        console.log('🔍 updateTransactionsTable called with:', transactions);
        
        // Check what elements exist
        const tableBody = document.querySelector('#transactions-table tbody');
        const tableContainer = document.querySelector('#transactions-table');
        const transactionsContent = document.querySelector('#transactions-content');
        
        console.log('🔍 HTML Elements check:');
        console.log('- #transactions-table tbody:', tableBody);
        console.log('- #transactions-table:', tableContainer);
        console.log('- #transactions-content:', transactionsContent);
        
        if (!tableBody) {
            console.error('❌ Could not find #transactions-table tbody');
            console.log('🔍 Available elements with "transactions" in ID:');
            document.querySelectorAll('[id*="transactions"]').forEach(el => {
                console.log('- Found element:', el.id, el);
            });
            return;
        }
        
        tableBody.innerHTML = '';
        
        if (!transactions || transactions.length === 0) {
            console.log('📝 No transactions to display');
            tableBody.innerHTML = '<tr><td colspan="6" class="no-data">No transactions yet</td></tr>';
            return;
        }
        
        console.log(`📊 Displaying ${transactions.length} transactions`);
        
        transactions.forEach((tx, index) => {
            console.log(`📋 Transaction ${index}:`, tx);
            
            const row = document.createElement('tr');
            
            // Use the processed transaction data structure
            const timestamp = tx.timestamp || Date.now() / 1000;
            const date = new Date(timestamp * 1000).toLocaleString();
            
            // Extract transaction details from processed data
            const txType = tx.type || 'unknown';
            const amount = tx.amount || 0; // Already in correct units
            const fee = tx.fee || 0; // Already in SOL
            const signature = tx.signature || '';
            const tokenSymbol = tx.token_symbol || 'SOL';
            
            // Format the transaction type for display
            const displayType = txType.replace('_', ' ').toUpperCase();
            
            row.innerHTML = `
                <td>
                    <div class="transaction-info">
                        <span class="tx-type ${txType}">${displayType}</span>
                        <span class="tx-symbol">${tokenSymbol}</span>
                    </div>
                </td>
                <td>${amount.toFixed(6)}</td>
                <td>${fee.toFixed(6)} SOL</td>
                <td>${date}</td>
                <td>
                    <a href="https://solscan.io/tx/${signature}" target="_blank" class="tx-link">
                        ${this.truncateAddress(signature)}
                    </a>
                </td>
                <td>
                    <span class="status ${txType}">${displayType}</span>
                </td>
            `;
            
            tableBody.appendChild(row);
        });
        
        console.log('✅ Transactions table updated successfully');
    }
    
    async sellPosition(mint) {
        try {
            const response = await fetch('/api/trade/sell', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ mint })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Position sold successfully', 'success');
                // Don't fetch from API - the WebSocket will update the local array
                console.log('✅ Sell successful, waiting for WebSocket update');
            } else {
                this.showNotification(`Sell failed: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Error selling position:', error);
            this.showNotification('Error selling position', 'error');
        }
    }

    // Test method to verify tab switching works correctly
    testTabSwitching() {
        console.log('🧪 Testing tab switching...');
        
        const tabs = ['monitoring', 'positions', 'transactions', 'logs'];
        
        tabs.forEach((tabName, index) => {
            setTimeout(() => {
                console.log(`🧪 Testing tab: ${tabName}`);
                this.switchTab(tabName);
                
                // Check if only the active tab is visible
                setTimeout(() => {
                    document.querySelectorAll('.tab-content').forEach(content => {
                        const isActive = content.classList.contains('active');
                        const isVisible = content.style.display !== 'none' && content.style.visibility !== 'hidden';
                        const isPositioned = content.style.position !== 'absolute';
                        console.log(`- ${content.id}: active=${isActive}, visible=${isVisible}, positioned=${isPositioned}`);
                    });
                }, 100);
            }, index * 2000); // Test each tab with 2 second delay
        });
    }

    // Simple test function to run in console
    testTabs() {
        console.log('🧪 Running tab test...');
        this.switchTab('positions');
        setTimeout(() => this.switchTab('transactions'), 1000);
        setTimeout(() => this.switchTab('logs'), 2000);
        setTimeout(() => this.switchTab('monitoring'), 3000);
    }
    
    // Quick test function
    quickTest() {
        console.log('🧪 Quick tab test...');
        console.log('Current active tab:', document.querySelector('.tab-content.active')?.id);
        this.switchTab('positions');
        setTimeout(() => {
            console.log('After switch - active tab:', document.querySelector('.tab-content.active')?.id);
            console.log('Positions content display:', document.getElementById('positions-content').style.display);
            console.log('Positions content classList:', document.getElementById('positions-content').classList.toString());
        }, 100);
    }
    
    // Comprehensive debug function
    debugTabs() {
        console.log('🔍 === COMPREHENSIVE TAB DEBUG ===');
        
        // Check all tab content elements
        document.querySelectorAll('.tab-content').forEach(content => {
            const computedStyle = window.getComputedStyle(content);
            console.log(`📋 ${content.id}:`);
            console.log(`  - display: ${computedStyle.display}`);
            console.log(`  - visibility: ${computedStyle.visibility}`);
            console.log(`  - position: ${computedStyle.position}`);
            console.log(`  - has active class: ${content.classList.contains('active')}`);
            console.log(`  - inline display: ${content.style.display}`);
            console.log(`  - inline visibility: ${content.style.visibility}`);
        });
        
        // Check all tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            console.log(`🔘 Tab button [data-tab="${btn.dataset.tab}"]: has active class: ${btn.classList.contains('active')}`);
        });
        
        // Check CSS rules
        console.log('🎨 Checking CSS rules...');
        const styleSheets = Array.from(document.styleSheets);
        styleSheets.forEach((sheet, index) => {
            try {
                const rules = Array.from(sheet.cssRules || sheet.rules);
                rules.forEach(rule => {
                    if (rule.selectorText && rule.selectorText.includes('.tab-content')) {
                        console.log(`📝 CSS Rule in sheet ${index}: ${rule.selectorText} { display: ${rule.style.display} }`);
                    }
                });
            } catch (e) {
                console.log(`⚠️ Could not access rules from sheet ${index}:`, e.message);
            }
        });
        
        console.log('🔍 === END DEBUG ===');
    }
    
    // Force display test
    forceDisplayTest() {
        console.log('🧪 Force display test...');
        
        // Hide all tabs first
        document.querySelectorAll('.tab-content').forEach(content => {
            content.style.display = 'none';
            content.classList.remove('active');
        });
        
        // Force show positions tab
        const positionsContent = document.getElementById('positions-content');
        if (positionsContent) {
            positionsContent.style.display = 'flex';
            positionsContent.classList.add('active');
            console.log('✅ Forced positions tab to display: flex');
        }
        
        // Update tab button
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        const positionsTab = document.querySelector('[data-tab="positions"]');
        if (positionsTab) {
            positionsTab.classList.add('active');
        }
        
        console.log('✅ Force display test completed');
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new SniperBotApp();
    window.sniperBot = window.app; // Keep both references for compatibility
}); 