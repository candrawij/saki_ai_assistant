"""
Saki Hub System Tray
System tray icon + context menu untuk Saki Hub
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer
from pathlib import Path
import webbrowser

class SakiTray:
    """System tray manager untuk Saki Hub"""
    
    def __init__(self, api_client, dashboard_window=None):
        self.api = api_client
        self.dashboard = dashboard_window
        self.tray_icon = None
        self.menu = None
        
        # Status tracking
        self.ollama_running = False
        self.streamlit_running = False
        
        # Setup tray
        self._setup_tray()
        
        # Update timer — setiap 10 detik
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(10000)
        
        # Update pertama setelah 1 detik
        QTimer.singleShot(1000, self._update_status)
    
    def _setup_tray(self):
        """Buat system tray icon dan context menu."""
        # Cari icon
        icon_path = self._find_icon("icon.ico")
        
        if icon_path and icon_path.exists():
            self.tray_icon = QSystemTrayIcon(QIcon(str(icon_path)))
        else:
            # Fallback: pakai icon bawaan Qt
            from PyQt6.QtWidgets import QApplication
            self.tray_icon = QSystemTrayIcon(QApplication.style().standardIcon(
                QApplication.style().StandardPixmap.SP_ComputerIcon
            ))
        
        self.tray_icon.setToolTip("Saki Hub | Connecting...")
        
        # === CONTEXT MENU ===
        self.menu = QMenu()
        
        # Status header (disabled — cuma info)
        self.status_action = QAction("🔴 Saki: Connecting...")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        
        self.menu.addSeparator()
        
        # Dashboard
        dashboard_action = QAction("📊 Dashboard", self.menu)
        dashboard_action.triggered.connect(self._show_dashboard)
        self.menu.addAction(dashboard_action)
        
        # Chat Saki
        chat_action = QAction("💬 Chat Saki", self.menu)
        chat_action.triggered.connect(self._open_chat)
        self.menu.addAction(chat_action)
        
        self.menu.addSeparator()
        
        # Controls
        start_all_action = QAction("▶ Start All", self.menu)
        start_all_action.triggered.connect(self._start_all)
        self.menu.addAction(start_all_action)
        
        stop_all_action = QAction("⏸ Stop All", self.menu)
        stop_all_action.triggered.connect(self._stop_all)
        self.menu.addAction(stop_all_action)
        
        restart_action = QAction("🔄 Restart All", self.menu)
        restart_action.triggered.connect(self._restart_all)
        self.menu.addAction(restart_action)
        
        self.menu.addSeparator()
        
        # Exit
        exit_action = QAction("❌ Exit", self.menu)
        exit_action.triggered.connect(self._exit_app)
        self.menu.addAction(exit_action)
        
        # Pasang menu ke tray icon
        self.tray_icon.setContextMenu(self.menu)
        
        # Double-click → buka dashboard
        self.tray_icon.activated.connect(self._on_activated)
        
        # Tampilkan
        self.tray_icon.show()
    
    def _find_icon(self, filename: str) -> Path | None:
        """Cari file icon di beberapa lokasi."""
        search_paths = [
            Path("saki_hub/assets") / filename,
            Path("assets") / filename,
            Path(__file__).parent / "assets" / filename,
        ]
        for path in search_paths:
            if path.exists():
                return path
        return None
    
    def _update_status(self):
        """Update tray icon + tooltip berdasarkan status API."""
        try:
            status = self.api.get_status()
            monitor = self.api.get_monitor()
            
            # Parse status
            components = status.get("components", [])
            running_count = 0
            total_count = len(components)
            
            for comp in components:
                comp_status = comp.get("status", "")
                if comp_status == "running":
                    running_count += 1
            
            # CPU & RAM
            cpu = monitor.get("cpu", {}).get("percent", 0)
            ram = monitor.get("ram", {}).get("percent", 0)
            
            # Update tooltip
            if total_count == 0:
                tooltip = "Saki Hub | No components"
                self.status_action.setText("🔴 Saki: No data")
            elif running_count == total_count:
                tooltip = f"Saki Hub | All Running | CPU: {cpu:.0f}% | RAM: {ram:.0f}%"
                self.status_action.setText(f"🟢 Saki Running | CPU: {cpu:.0f}% | RAM: {ram:.0f}%")
            elif running_count > 0:
                tooltip = f"Saki Hub | Partial ({running_count}/{total_count}) | CPU: {cpu:.0f}% | RAM: {ram:.0f}%"
                self.status_action.setText(f"🟡 Saki Partial ({running_count}/{total_count})")
            else:
                tooltip = "Saki Hub | All Stopped"
                self.status_action.setText("🔴 Saki Stopped")
            
            self.tray_icon.setToolTip(tooltip)
            
        except Exception:
            self.tray_icon.setToolTip("Saki Hub | API not available")
            self.status_action.setText("🔴 Saki: API unavailable")
    
    def _on_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_dashboard()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self._open_chat()
    
    def _show_dashboard(self):
        """Tampilkan dashboard window."""
        if self.dashboard:
            self.dashboard.show()
            self.dashboard.raise_()
            self.dashboard.activateWindow()
    
    def _open_chat(self):
        """Buka Saki Chat di browser."""
        webbrowser.open("http://localhost:8501")
    
    def _start_all(self):
        """Start semua komponen."""
        self.api.start_component("all")
        QTimer.singleShot(2000, self._update_status)
    
    def _stop_all(self):
        """Stop semua komponen."""
        self.api.stop_component("all")
        QTimer.singleShot(2000, self._update_status)
    
    def _restart_all(self):
        """Restart semua komponen."""
        self.api.stop_component("all")
        QTimer.singleShot(3000, lambda: self.api.start_component("all"))
        QTimer.singleShot(5000, self._update_status)
    
    def _exit_app(self):
        """Keluar dari aplikasi."""
        from PyQt6.QtWidgets import QApplication
        self.tray_icon.hide()
        QApplication.quit()
    
    def cleanup(self):
        """Bersihkan tray icon saat exit."""
        if self.tray_icon:
            self.tray_icon.hide()