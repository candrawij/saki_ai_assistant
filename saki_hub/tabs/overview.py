"""
Overview Tab — Dashboard utama Saki Hub
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QGroupBox, QGridLayout,
                              QFileDialog)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
import webbrowser
import subprocess
import os
from datetime import datetime


class OverviewTab(QWidget):
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api = api_client
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # === ROW 1: GAUGES ===
        gauges_layout = QHBoxLayout()
        
        from ..widgets.gauge import CircularGauge
        self.cpu_gauge = CircularGauge("CPU", 100, "%")
        self.ram_gauge = CircularGauge("RAM", 100, "%")
        self.disk_gauge = CircularGauge("DISK", 100, "%")
        
        gauges_layout.addWidget(self.cpu_gauge)
        gauges_layout.addWidget(self.ram_gauge)
        gauges_layout.addWidget(self.disk_gauge)
        layout.addLayout(gauges_layout)
        
        # === ROW 2: STATUS KOMPONEN ===
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
        
        # === ROW 3: QUICK ACTIONS ===
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QGridLayout(actions_group)
        
        self.screenshot_btn = QPushButton("📸 Screenshot")
        self.screenshot_btn.setObjectName("quickBtn")
        self.screenshot_btn.clicked.connect(self._take_screenshot)
        
        self.file_btn = QPushButton("📁 Buka File")
        self.file_btn.setObjectName("quickBtn")
        self.file_btn.clicked.connect(self._open_file)
        
        self.note_btn = QPushButton("📝 Note Cepat")
        self.note_btn.setObjectName("quickBtn")
        self.note_btn.clicked.connect(self._open_notepad)
        
        self.chat_btn = QPushButton("💬 Chat Saki")
        self.chat_btn.setObjectName("quickBtn")
        self.chat_btn.clicked.connect(self._open_chat)
        
        self.backup_btn = QPushButton("💾 Backup Now")
        self.backup_btn.setObjectName("quickBtn")
        self.backup_btn.clicked.connect(self._create_backup)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setObjectName("quickBtn")
        self.refresh_btn.clicked.connect(self.refresh_data)
        
        actions_layout.addWidget(self.screenshot_btn, 0, 0)
        actions_layout.addWidget(self.file_btn, 0, 1)
        actions_layout.addWidget(self.note_btn, 0, 2)
        actions_layout.addWidget(self.chat_btn, 1, 0)
        actions_layout.addWidget(self.backup_btn, 1, 1)
        actions_layout.addWidget(self.refresh_btn, 1, 2)
        layout.addWidget(actions_group)
        
        # === ROW 4: PLUGIN MANAGER (PLACEHOLDER) ===
        plugin_group = QGroupBox("Plugin Manager (Coming in Fase 3)")
        plugin_layout = QVBoxLayout(plugin_group)
        
        plugins = [
            ("🎤 Speech Recognition", "Voice control untuk Saki"),
            ("👤 Face Recognition", "Pengenalan wajah untuk autentikasi"),
            ("📄 OCR Struk", "Ekstrak data dari struk belanja"),
            ("🏕️ Camping Bot", "Bot otomatis untuk marketplace"),
        ]
        
        for name, desc in plugins:
            plugin_row = QHBoxLayout()
            icon_label = QLabel(name.split()[0])
            icon_label.setStyleSheet("font-size: 20px;")
            plugin_row.addWidget(icon_label)
            
            text_layout = QVBoxLayout()
            name_label = QLabel(name.split(" ", 1)[1] if " " in name else name)
            name_label.setStyleSheet("font-weight: bold;")
            text_layout.addWidget(name_label)
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
            text_layout.addWidget(desc_label)
            
            plugin_row.addLayout(text_layout)
            plugin_row.addStretch()
            
            off_btn = QPushButton("OFF ○")
            off_btn.setEnabled(False)
            off_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2D2D44;
                    color: #6B7280;
                    border-radius: 10px;
                    padding: 4px 12px;
                    font-size: 11px;
                }
            """)
            plugin_row.addWidget(off_btn)
            
            plugin_layout.addLayout(plugin_row)
        
        layout.addWidget(plugin_group)
        
        # === STATUS BAR ===
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Auto-refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(5000)  # 5 detik
        
        # Initial refresh
        self.refresh_data()
    
    def refresh_data(self):
        """Fetch dan update semua data."""
        try:
            # Monitor data
            monitor = self.api.get_monitor()
            
            cpu = monitor.get("cpu", {})
            if isinstance(cpu, dict):
                cpu_pct = cpu.get("percent", 0)
            else:
                cpu_pct = monitor.get("cpu_percent", 0)
            
            ram = monitor.get("ram", {})
            if isinstance(ram, dict):
                ram_pct = ram.get("percent", 0)
                ram_used = ram.get("used_gb", 0)
                ram_total = ram.get("total_gb", 16)
            else:
                ram_pct = monitor.get("ram_percent", 0)
                ram_used = monitor.get("ram_used_gb", 0)
                ram_total = monitor.get("ram_total_gb", 16)
            
            disk = monitor.get("disk", {})
            if isinstance(disk, dict):
                disk_pct = disk.get("percent", 0)
                disk_free = disk.get("free_gb", 0)
            else:
                disk_pct = monitor.get("disk_percent", 0)
                disk_free = monitor.get("disk_free_gb", 0)
            
            self.cpu_gauge.set_value(cpu_pct, f"{cpu_pct:.0f}%")
            self.ram_gauge.set_value(ram_pct, f"{ram_used:.0f}/{ram_total:.0f} GB")
            self.disk_gauge.set_value(disk_pct, f"{disk_free:.0f} GB free")
            
            # Component status
            status = self.api.get_status()
            components = status.get("components", [])
            
            for comp in components:
                name = comp.get("name", "")
                comp_status = comp.get("status", "unknown")
                is_running = comp_status == "running"
                
                if name == "ollama":
                    self.ollama_card.set_status(
                        comp_status,
                        f"Port 11434 • {'Running' if is_running else 'Down'}"
                    )
                elif name == "streamlit":
                    self.streamlit_card.set_status(
                        comp_status,
                        f"Port 8501 • {'Running' if is_running else 'Down'}"
                    )
            
            # Scheduler
            jobs = self.api.get_scheduler()
            job_count = len(jobs) if isinstance(jobs, list) else 0
            self.scheduler_card.set_status(
                "running" if job_count > 0 else "unknown",
                f"{job_count} jobs active"
            )
            
            self.status_label.setText(f"✅ Last refresh: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.status_label.setText(f"⚠️ Refresh failed: {str(e)[:50]}")
    
    def _take_screenshot(self):
        """Ambil screenshot."""
        try:
            import pyautogui
            os.makedirs("data/screenshots", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"data/screenshots/screenshot_{timestamp}.png"
            pyautogui.screenshot(path)
            self.status_label.setText(f"📸 Screenshot saved: {path}")
        except ImportError:
            try:
                from PIL import ImageGrab
                os.makedirs("data/screenshots", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = f"data/screenshots/screenshot_{timestamp}.png"
                ImageGrab.grab().save(path)
                self.status_label.setText(f"📸 Screenshot saved: {path}")
            except:
                self.status_label.setText("❌ Install pyautogui atau Pillow untuk screenshot")
        except Exception as e:
            self.status_label.setText(f"❌ Screenshot failed: {e}")
    
    def _open_file(self):
        """Buka file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Buka File")
        if file_path:
            os.startfile(file_path)
            self.status_label.setText(f"📁 Opened: {os.path.basename(file_path)}")
    
    def _open_notepad(self):
        """Buka Notepad untuk catatan cepat."""
        subprocess.Popen(['notepad.exe'])
        self.status_label.setText("📝 Notepad opened")
    
    def _open_chat(self):
        """Buka Saki Chat di browser."""
        webbrowser.open('http://localhost:8501')
        self.status_label.setText("💬 Chat opened in browser")
    
    def _create_backup(self):
        """Trigger backup."""
        result = self.api.create_backup()
        if "error" not in result:
            self.status_label.setText("💾 Backup created successfully")
        else:
            self.status_label.setText("❌ Backup failed")