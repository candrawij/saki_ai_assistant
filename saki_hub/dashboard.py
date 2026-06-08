"""
Saki Hub Dashboard
Main window dengan tab layout untuk monitoring + kontrol Saki
"""

from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                              QLabel, QStatusBar, QApplication)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon

from .api_client import SakiAPIClient
from .tabs.overview import OverviewTab
from .tabs.components import ComponentsTab
from .tabs.scheduler import SchedulerTab
from .tabs.logs import LogsTab
from .tabs.settings import SettingsTab
from .styles import STYLE_SHEET


class SakiDashboard(QMainWindow):
    """Main dashboard window untuk Saki Hub"""
    
    def __init__(self):
        super().__init__()
        
        # API client
        self.api = SakiAPIClient()
        
        # Window setup
        self.setWindowTitle("Saki Hub Dashboard")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # Apply dark theme
        self.setStyleSheet(STYLE_SHEET)
        
        # Setup UI
        self._setup_ui()
        self._setup_statusbar()
        
        # Connection check timer
        self.conn_timer = QTimer()
        self.conn_timer.timeout.connect(self._check_connection)
        self.conn_timer.start(5000)
        self._check_connection()
    
    def _setup_ui(self):
        """Setup main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # === HEADER ===
        header = QLabel("🤖 SAKI HUB")
        header.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            padding: 12px 16px;
            background-color: #0f3460;
            color: #ffffff;
        """)
        layout.addWidget(header)
        
        # === TAB WIDGET ===
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # Tab 1: Overview
        self.overview_tab = OverviewTab(self.api)
        self.tabs.addTab(self.overview_tab, "📊 Overview")
        
        # Tab 2: Components
        self.components_tab = ComponentsTab(self.api)
        self.tabs.addTab(self.components_tab, "🔧 Components")
        
        # Tab 3: Scheduler
        self.scheduler_tab = SchedulerTab(self.api)
        self.tabs.addTab(self.scheduler_tab, "⏰ Scheduler")
        
        # Tab 4: Logs
        self.logs_tab = LogsTab(self.api)
        self.tabs.addTab(self.logs_tab, "📋 Logs")
        
        # Tab 5: Settings
        self.settings_tab = SettingsTab(self.api)
        self.tabs.addTab(self.settings_tab, "⚙ Settings")
        
        layout.addWidget(self.tabs)
    
    def _setup_statusbar(self):
        """Setup status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.connection_label = QLabel("🔴 Connecting...")
        self.connection_label.setStyleSheet("color: #ff4444; padding: 4px 8px;")
        self.status_bar.addPermanentWidget(self.connection_label)
    
    def _check_connection(self):
        """Check API connection dan update status bar."""
        if self.api.check_connection():
            self.connection_label.setText("🟢 API Connected")
            self.connection_label.setStyleSheet("color: #00ff88; padding: 4px 8px;")
        else:
            self.connection_label.setText("🔴 API Disconnected")
            self.connection_label.setStyleSheet("color: #ff4444; padding: 4px 8px;")
    
    def closeEvent(self, event):
        """Handle close event — exit aplikasi."""
        QApplication.quit()