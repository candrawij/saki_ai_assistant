"""
Overview Tab — Dashboard utama
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QGroupBox, QGridLayout)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import webbrowser
import subprocess
import os


class OverviewTab(QWidget):
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api = api_client
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Gauges row
        gauges_layout = QHBoxLayout()
        from ..widgets.gauge import CircularGauge
        self.cpu_gauge = CircularGauge("CPU", 100, "%")
        self.ram_gauge = CircularGauge("RAM", 100, "%")
        self.disk_gauge = CircularGauge("DISK", 100, "%")
        
        gauges_layout.addWidget(self.cpu_gauge)
        gauges_layout.addWidget(self.ram_gauge)
        gauges_layout.addWidget(self.disk_gauge)
        layout.addLayout(gauges_layout)
        
        # Status components
        status_group = QGroupBox("Status Komponen")
        status_layout = QVBoxLayout(status_group)
        
        from ..widgets.status_card import StatusCard
        self.ollama_card = StatusCard("Ollama")
        self.streamlit_card = StatusCard("Streamlit")
        self.scheduler_card = StatusCard("Scheduler")
        
        status_layout.addWidget(self.ollama_card)
        status_layout.addWidget(self.streamlit_card)
        status_layout.addWidget(self.scheduler_card)
        layout.addWidget(status_group)
        
        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QGridLayout(actions_group)
        
        self.screenshot_btn = QPushButton("📸 Screenshot")
        self.screenshot_btn.setObjectName("quickBtn")
        self.screenshot_btn.clicked.connect(self.take_screenshot)
        
        self.file_btn = QPushButton("📁 Buka File")
        self.file_btn.setObjectName("quickBtn")
        self.file_btn.clicked.connect(self.open_file)
        
        self.note_btn = QPushButton("📝 Note")
        self.note_btn.setObjectName("quickBtn")
        self.note_btn.clicked.connect(self.open_notepad)
        
        self.chat_btn = QPushButton("💬 Chat Saki")
        self.chat_btn.setObjectName("quickBtn")
        self.chat_btn.clicked.connect(self.open_chat)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setObjectName("quickBtn")
        self.refresh_btn.clicked.connect(self.refresh_data)
        
        actions_layout.addWidget(self.screenshot_btn, 0, 0)
        actions_layout.addWidget(self.file_btn, 0, 1)
        actions_layout.addWidget(self.note_btn, 0, 2)
        actions_layout.addWidget(self.chat_btn, 1, 0)
        actions_layout.addWidget(self.refresh_btn, 1, 1)
        layout.addWidget(actions_group)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # Auto-refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(5000)  # 5 detik
        
        # Initial refresh
        self.refresh_data()
    
    def refresh_data(self):
        """Fetch dan update semua data."""
        # Monitor data
        monitor = self.api.get_monitor()
        self.cpu_gauge.set_value(monitor.get("cpu_percent", 0), f"{monitor.get('cpu_percent', 0)}%")
        self.ram_gauge.set_value(
            monitor.get("ram_percent", 0),
            f"{monitor.get('ram_used_gb', 0)}/{monitor.get('ram_total_gb', 16)} GB"
        )
        self.disk_gauge.set_value(
            monitor.get("disk_percent", 0),
            f"{monitor.get('disk_free_gb', 0)} GB free"
        )
        
        # Component status
        status = self.api.get_status()
        
        ollama_status = status.get("ollama", "unknown")
        self.ollama_card.set_status(ollama_status, f"Port 11434 • {'Running' if ollama_status == 'running' else 'Down'}")
        
        streamlit_status = status.get("streamlit", "unknown")
        self.streamlit_card.set_status(streamlit_status, f"Port 8501 • {'Running' if streamlit_status == 'running' else 'Down'}")
        
        scheduler_status = "running" if self.api.check_connection() else "unknown"
        self.scheduler_card.set_status(scheduler_status, "4 jobs active")
        
        self.status_label.setText(f"Last refresh: {__import__('datetime').datetime.now().strftime('%H:%M:%S')}")
    
    def take_screenshot(self):
        try:
            import pyautogui
            os.makedirs("data/screenshots", exist_ok=True)
            timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"data/screenshots/screenshot_{timestamp}.png"
            pyautogui.screenshot(path)
            self.status_label.setText(f"Screenshot saved: {path}")
        except Exception as e:
            self.status_label.setText(f"Screenshot failed: {e}")
    
    def open_file(self):
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Buka File")
        if file_path:
            os.startfile(file_path)
    
    def open_notepad(self):
        subprocess.Popen(['notepad.exe'])
    
    def open_chat(self):
        webbrowser.open('http://localhost:8501')