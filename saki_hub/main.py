"""
Saki Hub — Desktop Control Center
Main Application
"""

import sys
import webbrowser
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, 
                              QSystemTrayIcon, QMenu, QMessageBox, QStyle,
                              QWidget, QVBoxLayout, QLabel, QStatusBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QAction

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from saki_hub.api_client import SakiAPIClient
from saki_hub.styles import DARK_THEME
from saki_hub.tabs.overview import OverviewTab
from saki_hub.tabs.components import ComponentsTab
from saki_hub.tabs.scheduler import SchedulerTab
from saki_hub.tabs.logs import LogsTab
from saki_hub.tabs.settings import SettingsTab


class SakiHub(QMainWindow):
    """Main window untuk Saki Hub Desktop"""
    
    def __init__(self):
        super().__init__()
        self.api = SakiAPIClient()
        
        # Window setup
        self.setWindowTitle("Saki Hub — Personal AI Control Center")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        
        # Apply dark theme
        self.setStyleSheet(DARK_THEME)
        
        # Setup UI
        self._setup_header()
        self._setup_tabs()
        self._setup_statusbar()
        self._setup_tray()
        
        # Connection check timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_api_connection)
        self.timer.start(10000)  # Every 10 seconds
        self._check_api_connection()
    
    def _setup_header(self):
        """Header label."""
        header = QLabel("🤖 SAKI HUB")
        header.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            padding: 12px 16px;
            background-color: #0f3460;
            color: #ffffff;
        """)
        # Pasang sebagai widget di atas tabs
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.setCentralWidget(central)
    
    def _setup_tabs(self):
        """Setup tab widget."""
        self.overview_tab = OverviewTab(self.api)
        self.components_tab = ComponentsTab(self.api)
        self.scheduler_tab = SchedulerTab(self.api)
        self.logs_tab = LogsTab(self.api)
        self.settings_tab = SettingsTab(self.api)
        
        self.tabs.addTab(self.overview_tab, "📊 Overview")
        self.tabs.addTab(self.components_tab, "🔧 Components")
        self.tabs.addTab(self.scheduler_tab, "⏰ Scheduler")
        self.tabs.addTab(self.logs_tab, "📋 Logs")
        self.tabs.addTab(self.settings_tab, "⚙ Settings")
    
    def _setup_statusbar(self):
        """Setup status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.connection_label = QLabel("🔴 Connecting...")
        self.connection_label.setStyleSheet("color: #ff4444; padding: 4px 8px;")
        self.status_bar.addPermanentWidget(self.connection_label)
    
    def _setup_tray(self):
        """Setup system tray icon dengan menu lengkap."""
        self.tray = QSystemTrayIcon(self)
        
        # Load icon
        icon_path = Path(__file__).parent / "assets" / "icon.ico"
        if icon_path.exists():
            self.tray.setIcon(QIcon(str(icon_path)))
        else:
            self.tray.setIcon(self.style().standardIcon(
                QStyle.StandardPixmap.SP_ComputerIcon
            ))
        
        self.tray.setToolTip("Saki Hub | Connecting...")
        
        # === TRAY MENU ===
        menu = QMenu()
        
        # Status header
        self.tray_status = QAction("🔴 Saki: Connecting...")
        self.tray_status.setEnabled(False)
        menu.addAction(self.tray_status)
        
        menu.addSeparator()
        
        # Dashboard
        show_action = QAction("📊 Dashboard", self)
        show_action.triggered.connect(self.show_window)
        menu.addAction(show_action)
        
        # Chat
        chat_action = QAction("💬 Chat Saki", self)
        chat_action.triggered.connect(lambda: webbrowser.open('http://localhost:8501'))
        menu.addAction(chat_action)
        
        menu.addSeparator()
        
        # Controls
        start_all = QAction("▶ Start All", self)
        start_all.triggered.connect(self._start_all)
        menu.addAction(start_all)
        
        stop_all = QAction("⏸ Stop All", self)
        stop_all.triggered.connect(self._stop_all)
        menu.addAction(stop_all)
        
        restart_all = QAction("🔄 Restart All", self)
        restart_all.triggered.connect(self._restart_all)
        menu.addAction(restart_all)
        
        menu.addSeparator()
        
        # Exit
        quit_action = QAction("❌ Exit", self)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)
        
        self.tray.setContextMenu(menu)
        self.tray.show()
        
        # Klik kiri = buka dashboard
        self.tray.activated.connect(self._tray_activated)
    
    def _tray_activated(self, reason):
        """Handle tray icon click."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()
    
    def show_window(self):
        """Tampilkan dan fokus window."""
        self.show()
        self.raise_()
        self.activateWindow()
    
    def _check_api_connection(self):
        """Check API connection + update status."""
        if self.api.check_connection():
            self.connection_label.setText("🟢 API Connected")
            self.connection_label.setStyleSheet("color: #00ff88; padding: 4px 8px;")
            
            # Update tray
            try:
                monitor = self.api.get_monitor()
                cpu = monitor.get("cpu", {}).get("percent", 0)
                ram = monitor.get("ram", {}).get("percent", 0)
                self.tray.setToolTip(f"Saki Hub | CPU: {cpu:.0f}% | RAM: {ram:.0f}%")
                self.tray_status.setText(f"🟢 Saki Running | CPU: {cpu:.0f}% | RAM: {ram:.0f}%")
            except:
                self.tray.setToolTip("Saki Hub | Connected ✅")
                self.tray_status.setText("🟢 Saki Connected")
        else:
            self.connection_label.setText("🔴 API Disconnected")
            self.connection_label.setStyleSheet("color: #ff4444; padding: 4px 8px;")
            self.tray.setToolTip("Saki Hub | API Not Available ⚠️")
            self.tray_status.setText("🔴 Saki: API Unavailable")
    
    def _start_all(self):
        """Start semua komponen."""
        self.api.start_component("all")
        QTimer.singleShot(3000, self._check_api_connection)
    
    def _stop_all(self):
        """Stop semua komponen."""
        reply = QMessageBox.question(
            self, "Konfirmasi",
            "Yakin ingin menghentikan semua komponen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.api.stop_component("all")
            QTimer.singleShot(3000, self._check_api_connection)
    
    def _restart_all(self):
        """Restart semua komponen."""
        self.api.stop_component("all")
        QTimer.singleShot(3000, lambda: self.api.start_component("all"))
        QTimer.singleShot(5000, self._check_api_connection)
    
    def _quit_app(self):
        """Exit aplikasi."""
        self.tray.hide()
        QApplication.quit()
    
    def closeEvent(self, event):
        """Close = Exit."""
        self._quit_app()


def main():
    """Entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Saki Hub")
    app.setOrganizationName("Saki AI")
    
    window = SakiHub()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()