import sys
import asyncio
import threading
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit,
                           QTableWidget, QTableWidgetItem, QTabWidget, QGroupBox,
                           QSpinBox, QDoubleSpinBox, QCheckBox, QProgressBar,
                           QComboBox, QFrame, QSplitter, QScrollArea)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap

from config import Config
from sniper_bot import SniperBot, Position
from pump_fun_monitor import TokenInfo
import logging

logger = logging.getLogger(__name__)

class AsyncWorker(QThread):
    """Worker thread for async operations"""
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.running = False
    
    def run(self):
        """Run the async event loop"""
        self.running = True
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.bot.start_monitoring())
        except Exception as e:
            logger.error(f"Error in async worker: {e}")
    
    def stop(self):
        """Stop the worker"""
        self.running = False
        self.bot.stop_monitoring()

class SniperBotGUI(QMainWindow):
    # Signals for thread-safe GUI updates
    new_token_signal = pyqtSignal(object)
    position_update_signal = pyqtSignal(object)
    transaction_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.bot = SniperBot()
        self.worker = None
        self.setup_ui()
        self.setup_bot_callbacks()
        self.setup_timers()
        
        # Connect signals
        self.new_token_signal.connect(self.on_new_token_gui)
        self.position_update_signal.connect(self.on_position_update_gui)
        self.transaction_signal.connect(self.on_transaction_gui)
        self.error_signal.connect(self.on_error_gui)
    
    def setup_ui(self):
        """Setup the main UI"""
        self.setWindowTitle("Pump.Fun Sniper Bot - Helius Powered")
        self.setGeometry(100, 100, Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT)
        self.setStyleSheet(self.get_dark_stylesheet())
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Create main splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Settings and Controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Monitoring and Positions
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter sizes
        splitter.setSizes([400, 800])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
    
    def create_left_panel(self):
        """Create left settings panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("🎯 Pump.Fun Sniper")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Wallet Section
        wallet_group = QGroupBox("💳 Wallet")
        wallet_layout = QVBoxLayout(wallet_group)
        
        self.wallet_input = QLineEdit()
        self.wallet_input.setPlaceholderText("Enter private key (Base58 or JSON array)")
        self.wallet_input.setEchoMode(QLineEdit.Password)
        wallet_layout.addWidget(self.wallet_input)
        
        self.connect_wallet_btn = QPushButton("Connect Wallet")
        self.connect_wallet_btn.clicked.connect(self.connect_wallet)
        wallet_layout.addWidget(self.connect_wallet_btn)
        
        self.wallet_address_label = QLabel("Not connected")
        wallet_layout.addWidget(self.wallet_address_label)
        
        self.sol_balance_label = QLabel("SOL Balance: 0.0")
        wallet_layout.addWidget(self.sol_balance_label)
        
        layout.addWidget(wallet_group)
        
        # Bot Settings Section
        settings_group = QGroupBox("⚙️ Bot Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # SOL Amount
        sol_layout = QHBoxLayout()
        sol_layout.addWidget(QLabel("SOL per snipe:"))
        self.sol_amount_input = QDoubleSpinBox()
        self.sol_amount_input.setRange(0.001, 10.0)
        self.sol_amount_input.setSingleStep(0.01)
        self.sol_amount_input.setDecimals(3)
        self.sol_amount_input.setValue(Config.DEFAULT_SOL_AMOUNT)
        sol_layout.addWidget(self.sol_amount_input)
        settings_layout.addLayout(sol_layout)
        
        # Max Tokens
        max_tokens_layout = QHBoxLayout()
        max_tokens_layout.addWidget(QLabel("Max positions:"))
        self.max_tokens_input = QSpinBox()
        self.max_tokens_input.setRange(1, 20)
        self.max_tokens_input.setValue(Config.DEFAULT_MAX_TOKENS)
        max_tokens_layout.addWidget(self.max_tokens_input)
        settings_layout.addLayout(max_tokens_layout)
        
        # Profit Target
        profit_layout = QHBoxLayout()
        profit_layout.addWidget(QLabel("Profit target %:"))
        self.profit_input = QDoubleSpinBox()
        self.profit_input.setRange(1.0, 1000.0)
        self.profit_input.setValue(Config.DEFAULT_PROFIT_PERCENT)
        profit_layout.addWidget(self.profit_input)
        settings_layout.addLayout(profit_layout)
        
        # Stop Loss
        stop_loss_layout = QHBoxLayout()
        stop_loss_layout.addWidget(QLabel("Stop loss %:"))
        self.stop_loss_input = QDoubleSpinBox()
        self.stop_loss_input.setRange(1.0, 100.0)
        self.stop_loss_input.setValue(Config.DEFAULT_STOP_LOSS_PERCENT)
        stop_loss_layout.addWidget(self.stop_loss_input)
        settings_layout.addLayout(stop_loss_layout)
        
        # Auto Buy/Sell
        self.auto_buy_checkbox = QCheckBox("Auto Buy")
        settings_layout.addWidget(self.auto_buy_checkbox)
        
        self.auto_sell_checkbox = QCheckBox("Auto Sell")
        self.auto_sell_checkbox.setChecked(True)
        settings_layout.addWidget(self.auto_sell_checkbox)
        
        layout.addWidget(settings_group)
        
        # Control Buttons
        control_group = QGroupBox("🎮 Controls")
        control_layout = QVBoxLayout(control_group)
        
        self.start_btn = QPushButton("🚀 Start Monitoring")
        self.start_btn.clicked.connect(self.start_monitoring)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop Monitoring")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        layout.addWidget(control_group)
        
        # Status
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        return widget
    
    def create_right_panel(self):
        """Create right monitoring panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # Monitoring Tab
        monitoring_tab = self.create_monitoring_tab()
        tab_widget.addTab(monitoring_tab, "📊 Monitoring")
        
        # Positions Tab
        positions_tab = self.create_positions_tab()
        tab_widget.addTab(positions_tab, "💼 Positions")
        
        # Logs Tab
        logs_tab = self.create_logs_tab()
        tab_widget.addTab(logs_tab, "📝 Logs")
        
        return widget
    
    def create_monitoring_tab(self):
        """Create monitoring tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Stats
        stats_group = QGroupBox("📈 Statistics")
        stats_layout = QHBoxLayout(stats_group)
        
        self.total_pnl_label = QLabel("Total P&L: $0.00")
        stats_layout.addWidget(self.total_pnl_label)
        
        self.total_pnl_percent_label = QLabel("(0.00%)")
        stats_layout.addWidget(self.total_pnl_percent_label)
        
        stats_layout.addStretch()
        layout.addWidget(stats_group)
        
        # New Tokens Table
        tokens_group = QGroupBox("🆕 New Tokens Detected")
        tokens_layout = QVBoxLayout(tokens_group)
        
        self.tokens_table = QTableWidget()
        self.tokens_table.setColumnCount(6)
        self.tokens_table.setHorizontalHeaderLabels([
            "Symbol", "Name", "Market Cap", "Price", "Time", "Action"
        ])
        tokens_layout.addWidget(self.tokens_table)
        
        layout.addWidget(tokens_group)
        
        return widget
    
    def create_positions_tab(self):
        """Create positions tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Positions Table
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(9)
        self.positions_table.setHorizontalHeaderLabels([
            "Symbol", "Entry Price", "Current Price", "SOL Amount", 
            "P&L", "P&L %", "Entry Time", "Status", "Action"
        ])
        layout.addWidget(self.positions_table)
        
        return widget
    
    def create_logs_tab(self):
        """Create logs tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        layout.addWidget(self.logs_text)
        
        # Clear logs button
        clear_btn = QPushButton("Clear Logs")
        clear_btn.clicked.connect(self.clear_logs)
        layout.addWidget(clear_btn)
        
        return widget
    
    def setup_bot_callbacks(self):
        """Setup bot event callbacks"""
        self.bot.add_callback('new_token', self.new_token_signal.emit)
        self.bot.add_callback('position_update', self.position_update_signal.emit)
        self.bot.add_callback('transaction', self.transaction_signal.emit)
        self.bot.add_callback('error', self.error_signal.emit)
    
    def setup_timers(self):
        """Setup GUI update timers"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_gui)
        self.update_timer.start(Config.UPDATE_INTERVAL)
    
    def connect_wallet(self):
        """Connect wallet"""
        private_key = self.wallet_input.text().strip()
        if not private_key:
            self.log_message("Please enter a private key")
            return
        
        if self.bot.set_wallet(private_key):
            address = self.bot.get_wallet_address()
            self.wallet_address_label.setText(f"Connected: {address[:8]}...{address[-8:]}")
            self.connect_wallet_btn.setText("✓ Connected")
            self.connect_wallet_btn.setEnabled(False)
            self.log_message(f"Wallet connected: {address}")
        else:
            self.log_message("Failed to connect wallet. Check private key format.")
    
    def update_settings(self):
        """Update bot settings from GUI"""
        self.bot.settings.sol_amount_per_snipe = self.sol_amount_input.value()
        self.bot.settings.max_concurrent_positions = self.max_tokens_input.value()
        self.bot.settings.profit_target_percent = self.profit_input.value()
        self.bot.settings.stop_loss_percent = self.stop_loss_input.value()
        self.bot.settings.auto_buy_enabled = self.auto_buy_checkbox.isChecked()
        self.bot.settings.auto_sell_enabled = self.auto_sell_checkbox.isChecked()
    
    def start_monitoring(self):
        """Start bot monitoring"""
        if not self.bot.wallet_keypair:
            self.log_message("Please connect wallet first")
            return
        
        self.update_settings()
        
        self.worker = AsyncWorker(self.bot)
        self.worker.start()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Status: Monitoring...")
        self.log_message("Started monitoring for new tokens")
    
    def stop_monitoring(self):
        """Stop bot monitoring"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.worker = None
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Status: Stopped")
        self.log_message("Stopped monitoring")
    
    def update_gui(self):
        """Update GUI elements"""
        if self.bot.wallet_keypair:
            balance = self.bot.get_sol_balance()
            self.sol_balance_label.setText(f"SOL Balance: {balance:.3f}")
        
        # Update P&L
        pnl_data = self.bot.get_total_pnl()
        self.total_pnl_label.setText(f"Total P&L: {pnl_data['total_pnl']:.4f} SOL")
        self.total_pnl_percent_label.setText(f"({pnl_data['total_pnl_percent']:+.2f}%)")
        
        # Update positions table
        self.update_positions_table()
    
    def update_positions_table(self):
        """Update positions table"""
        positions = self.bot.positions
        self.positions_table.setRowCount(len(positions))
        
        for i, position in enumerate(positions):
            self.positions_table.setItem(i, 0, QTableWidgetItem(position.token_symbol))
            self.positions_table.setItem(i, 1, QTableWidgetItem(f"{position.entry_price:.8f}"))
            self.positions_table.setItem(i, 2, QTableWidgetItem(f"{position.current_price:.8f}"))
            self.positions_table.setItem(i, 3, QTableWidgetItem(f"{position.sol_amount:.3f}"))
            self.positions_table.setItem(i, 4, QTableWidgetItem(f"{position.current_pnl:+.4f}"))
            
            pnl_item = QTableWidgetItem(f"{position.current_pnl_percent:+.2f}%")
            if position.current_pnl_percent > 0:
                pnl_item.setBackground(QColor(0, 255, 0, 50))
            elif position.current_pnl_percent < 0:
                pnl_item.setBackground(QColor(255, 0, 0, 50))
            self.positions_table.setItem(i, 5, pnl_item)
            
            self.positions_table.setItem(i, 6, QTableWidgetItem(position.entry_time.strftime("%H:%M:%S")))
            
            status = "🟢 Active" if position.is_active else "🔴 Closed"
            self.positions_table.setItem(i, 7, QTableWidgetItem(status))
            
            # Sell button
            if position.is_active:
                sell_btn = QPushButton("Sell")
                sell_btn.clicked.connect(lambda checked, p=position: self.manual_sell(p))
                self.positions_table.setCellWidget(i, 8, sell_btn)
    
    def manual_sell(self, position):
        """Manual sell position"""
        asyncio.create_task(self.bot.sell_token(position, "manual"))
    
    def on_new_token_gui(self, token: TokenInfo):
        """Handle new token in GUI"""
        row = self.tokens_table.rowCount()
        self.tokens_table.insertRow(row)
        
        self.tokens_table.setItem(row, 0, QTableWidgetItem(token.symbol))
        self.tokens_table.setItem(row, 1, QTableWidgetItem(token.name[:30]))
        self.tokens_table.setItem(row, 2, QTableWidgetItem(f"${token.market_cap:.0f}"))
        self.tokens_table.setItem(row, 3, QTableWidgetItem(f"{token.price:.8f}"))
        self.tokens_table.setItem(row, 4, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
        
        # Buy button
        buy_btn = QPushButton("Buy")
        buy_btn.clicked.connect(lambda checked, t=token: self.manual_buy(t))
        self.tokens_table.setCellWidget(row, 5, buy_btn)
        
        # Scroll to new token
        self.tokens_table.scrollToBottom()
    
    def manual_buy(self, token: TokenInfo):
        """Manual buy token"""
        asyncio.create_task(self.bot.buy_token(token))
    
    def on_position_update_gui(self, position: Position):
        """Handle position update in GUI"""
        pass  # Position updates are handled by update_gui timer
    
    def on_transaction_gui(self, transaction_data):
        """Handle transaction in GUI"""
        tx_type = transaction_data['type']
        tx_hash = transaction_data['tx_hash']
        
        if tx_type == 'buy':
            token = transaction_data['token']
            self.log_message(f"✅ Bought {token.symbol} - TX: {tx_hash}")
        elif tx_type == 'sell':
            position = transaction_data['position']
            reason = transaction_data['reason']
            self.log_message(f"💰 Sold {position.token_symbol} ({reason}) - TX: {tx_hash}")
    
    def on_error_gui(self, error_msg):
        """Handle error in GUI"""
        self.log_message(f"❌ Error: {error_msg}")
    
    def log_message(self, message):
        """Add message to logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs_text.append(f"[{timestamp}] {message}")
    
    def clear_logs(self):
        """Clear logs"""
        self.logs_text.clear()
    
    def get_dark_stylesheet(self):
        """Get dark theme stylesheet"""
        return """
        QMainWindow {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QWidget {
            background-color: #2d2d2d;
            color: #ffffff;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #555;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QPushButton {
            background-color: #0078d4;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
        QPushButton:disabled {
            background-color: #555;
            color: #888;
        }
        QLineEdit, QSpinBox, QDoubleSpinBox {
            padding: 8px;
            border: 1px solid #555;
            border-radius: 4px;
            background-color: #3c3c3c;
        }
        QTableWidget {
            gridline-color: #555;
            background-color: #2d2d2d;
            alternate-background-color: #3c3c3c;
        }
        QHeaderView::section {
            background-color: #555;
            padding: 8px;
            border: none;
            font-weight: bold;
        }
        QTextEdit {
            background-color: #1e1e1e;
            border: 1px solid #555;
            border-radius: 4px;
        }
        QTabWidget::pane {
            border: 1px solid #555;
            background-color: #2d2d2d;
        }
        QTabBar::tab {
            background-color: #3c3c3c;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #0078d4;
        }
        """
    
    def closeEvent(self, event):
        """Handle window close"""
        self.stop_monitoring()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    window = SniperBotGUI()
    window.show()
    
    sys.exit(app.exec_()) 