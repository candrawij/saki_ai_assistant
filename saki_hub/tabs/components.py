"""
Components Tab — Detail & kontrol komponen
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QGroupBox, QFrame,
                              QMessageBox)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont


class ComponentCard(QFrame):
    """Card untuk satu komponen dengan kontrol."""
    
    def __init__(self, name: str, port: str = "", parent=None):
        super().__init__(parent)
        self.component_name = name.lower()
        
        self.setStyleSheet("""
            QFrame {
                background-color: #2D2D44;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # === HEADER ===
        header = QHBoxLayout()
        
        self.name_label = QLabel(name)
        self.name_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.addWidget(self.name_label)
        
        header.addStretch()
        
        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(QFont("Segoe UI", 16))
        header.addWidget(self.status_indicator)
        
        self.status_text = QLabel("Unknown")
        self.status_text.setStyleSheet("color: #94A3B8; font-size: 12px;")
        header.addWidget(self.status_text)
        
        layout.addLayout(header)
        
        # === INFO ===
        self.info_label = QLabel(f"Port: {port}" if port else "")
        self.info_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(self.info_label)
        
        # Resource usage
        self.resource_label = QLabel("CPU: -- | RAM: --")
        self.resource_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.resource_label)
        
        # === BUTTONS ===
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.start_btn = QPushButton("▶ Start")
        self.start_btn.setObjectName("startBtn")
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("stopBtn")
        btn_layout.addWidget(self.stop_btn)
        
        self.restart_btn = QPushButton("🔄 Restart")
        self.restart_btn.setObjectName("restartBtn")
        btn_layout.addWidget(self.restart_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def set_status(self, status: str, info: str = "", cpu: float = 0, ram: float = 0):
        """Update status card."""
        colors = {
            "running": "#10B981",
            "stopped": "#EF4444",
            "starting": "#F59E0B",
            "unknown": "#6B7280",
        }
        color = colors.get(status, "#6B7280")
        self.status_indicator.setStyleSheet(f"color: {color};")
        self.status_text.setText(status.capitalize())
        
        if info:
            self.info_label.setText(info)
        
        if cpu > 0 or ram > 0:
            self.resource_label.setText(f"CPU: {cpu:.1f}% | RAM: {ram:.0f} MB")


class ComponentsTab(QWidget):
    """Tab untuk kontrol detail setiap komponen."""
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api = api_client
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Component Control")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        subtitle = QLabel("Start, stop, atau restart komponen Saki")
        subtitle.setStyleSheet("color: #94A3B8;")
        layout.addWidget(subtitle)
        
        # Component cards
        self.ollama_card = ComponentCard("Ollama AI", "11434")
        self.streamlit_card = ComponentCard("Streamlit UI", "8501")
        self.chromadb_card = ComponentCard("ChromaDB", "Vector Store")
        self.scheduler_card = ComponentCard("Scheduler", "Task Manager")
        
        # Connect Ollama buttons
        self.ollama_card.start_btn.clicked.connect(lambda: self._start("ollama"))
        self.ollama_card.stop_btn.clicked.connect(lambda: self._stop("ollama"))
        self.ollama_card.restart_btn.clicked.connect(lambda: self._restart("ollama"))
        
        # Connect Streamlit buttons
        self.streamlit_card.start_btn.clicked.connect(lambda: self._start("streamlit"))
        self.streamlit_card.stop_btn.clicked.connect(lambda: self._stop("streamlit"))
        self.streamlit_card.restart_btn.clicked.connect(lambda: self._restart("streamlit"))
        
        # Connect Scheduler buttons
        self.scheduler_card.start_btn.clicked.connect(lambda: self._start("scheduler"))
        self.scheduler_card.stop_btn.clicked.connect(lambda: self._stop("scheduler"))
        self.scheduler_card.restart_btn.clicked.connect(lambda: self._restart("scheduler"))
        
        # ChromaDB — disable controls (managed internally)
        self.chromadb_card.start_btn.setEnabled(False)
        self.chromadb_card.stop_btn.setEnabled(False)
        self.chromadb_card.restart_btn.setEnabled(False)
        
        layout.addWidget(self.ollama_card)
        layout.addWidget(self.streamlit_card)
        layout.addWidget(self.chromadb_card)
        layout.addWidget(self.scheduler_card)
        layout.addStretch()
        
        # Refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(30000)  # Refresh setiap 30 detik
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh status semua komponen."""
        try:
            status = self.api.get_status()
            components = status.get("components", [])
            metrics = self.api.get_monitor()
            
            # Parse process info untuk CPU/RAM per komponen
            process_info = metrics.get("process", {})
            children = process_info.get("children", [])
            
            for comp in components:
                name = comp.get("name", "")
                comp_status = comp.get("status", "unknown")
                
                # Cari resource usage
                cpu = 0
                ram = 0
                for child in children:
                    child_name = child.get("name", "").lower()
                    if name in child_name or child_name in name:
                        cpu = child.get("cpu_percent", 0)
                        ram = child.get("memory_mb", 0)
                        break
                
                if name == "ollama":
                    self.ollama_card.set_status(
                        comp_status,
                        f"Port: 11434 | Model: qwen3:4b",
                        cpu, ram
                    )
                elif name == "streamlit":
                    self.streamlit_card.set_status(
                        comp_status,
                        f"Port: 8501 | http://localhost:8501",
                        cpu, ram
                    )
            
            # ChromaDB — always show as managed
            self.chromadb_card.set_status("running", "Managed internally")
            
            # Scheduler — check jobs
            jobs = self.api.get_scheduler()
            job_count = len(jobs) if isinstance(jobs, list) else 0
            self.scheduler_card.set_status(
                "running" if job_count > 0 else "stopped",
                f"{job_count} jobs active"
            )
            
        except Exception as e:
            print(f"Components refresh error: {e}")
    
    def _start(self, name: str):
        """Start komponen."""
        self.api.start_component(name)
        QTimer.singleShot(2000, self.refresh_data)
    
    def _stop(self, name: str):
        """Stop komponen dengan konfirmasi."""
        reply = QMessageBox.question(
            self, "Konfirmasi",
            f"Yakin ingin menghentikan {name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.api.stop_component(name)
            QTimer.singleShot(2000, self.refresh_data)
    
    def _restart(self, name: str):
        """Restart komponen via API."""
        self.api.restart_component(name)
        QTimer.singleShot(3000, self.refresh_data)