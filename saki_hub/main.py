"""
Saki Hub — Desktop Control Center
Main Application
"""

import sys
import webbrowser
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, 
                              QSystemTrayIcon, QMenu, QMessageBox, QStyle)
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
    def __init__(self):
        super().__init__()
        self.api = SakiAPIClient()
        
        self.setWindowTitle("Saki Hub — Personal AI Control Center")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        
        # Apply dark theme
        self.setStyleSheet(DARK_THEME)
        
        # Setup UI
        self._setup_tabs()
        self._setup_tray()
        
        # Check connection periodically
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_api_connection)
        self.timer.start(10000)  # Every 10 seconds
        self._check_api_connection()
    
    def _setup_tabs(self):
        self.tabs = QTabWidget()
        
        self.overview_tab = OverviewTab(self.api)
        self.components_tab = ComponentsTab(self.api)
        self.scheduler_tab = SchedulerTab(self.api)
        self.logs_tab = LogsTab()
        self.settings_tab = SettingsTab()
        
        self.tabs.addTab(self.overview_tab, "📊 Overview")
        self.tabs.addTab(self.components_tab, "⚙ Components")
        self.tabs.addTab(self.scheduler_tab, "📅 Scheduler")
        self.tabs.addTab(self.logs_tab, "📋 Logs")
        self.tabs.addTab(self.settings_tab, "⚙ Settings")
        
        self.setCentralWidget(self.tabs)
    
    def _setup_tray(self):
        """Setup system tray icon."""
        self.tray = QSystemTrayIcon(self)
        
        # Try to load icon, fallback to default
        icon_path = Path(__file__).parent / "assets" / "icon.ico"
        if icon_path.exists():
            self.tray.setIcon(QIcon(str(icon_path)))
        else:
            # Use built-in icon
            self.tray.setIcon(self.style().standardIcon(
                QStyle.StandardPixmap.SP_ComputerIcon
            ))
        
        self.tray.setToolTip("Saki Hub — Personal AI Control Center")
        
        # Tray menu
        menu = QMenu()
        
        show_action = QAction("📊 Dashboard", self)
        show_action.triggered.connect(self.show_window)
        menu.addAction(show_action)
        
        chat_action = QAction("💬 Chat Saki", self)
        chat_action.triggered.connect(lambda: webbrowser.open('http://localhost:8501'))
        menu.addAction(chat_action)
        
        menu.addSeparator()
        
        quit_action = QAction("❌ Exit", self)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)
        
        self.tray.setContextMenu(menu)
        self.tray.show()
        
        # Klik kiri = buka dashboard
        self.tray.activated.connect(self._tray_activated)
    
    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()
    
    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()
    
    def _check_api_connection(self):
        if self.api.check_connection():
            self.tray.setToolTip("Saki Hub | Connected ✅")
        else:
            self.tray.setToolTip("Saki Hub | API Not Available ⚠️")
    
    def _quit_app(self):
        self.tray.hide()
        QApplication.quit()
    
    def closeEvent(self, event):
        """Close = Exit."""
        self._quit_app()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Saki Hub")
    app.setOrganizationName("Saki AI")
    
    window = SakiHub()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()