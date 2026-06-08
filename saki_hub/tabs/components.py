"""
Components Tab — Detail & kontrol komponen
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QGroupBox, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class ComponentCard(QFrame):
    def __init__(self, name: str, port: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #2D2D44;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Header
        header = QHBoxLayout()
        self.name_label = QLabel(name)
        self.name_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        
        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(QFont("Segoe UI", 16))
        
        header.addWidget(self.name_label)
        header.addStretch()
        header.addWidget(self.status_indicator)
        layout.addLayout(header)
        
        # Info
        self.info_label = QLabel(f"Port: {port}" if port else "")
        self.info_label.setStyleSheet("color: #94A3B8;")
        layout.addWidget(self.info_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ Start")
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("stopBtn")
        self.restart_btn = QPushButton("🔄 Restart")
        self.restart_btn.setObjectName("restartBtn")
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.restart_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def set_status(self, status: str, info: str = ""):
        colors = {"running": "#10B981", "stopped": "#EF4444", "disabled": "#6B7280"}
        self.status_indicator.setStyleSheet(f"color: {colors.get(status, '#6B7280')};")
        if info:
            self.info_label.setText(info)


class ComponentsTab(QWidget):
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api = api_client
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        self.ollama_card = ComponentCard("Ollama", "11434")
        self.streamlit_card = ComponentCard("Streamlit", "8501")
        self.chromadb_card = ComponentCard("ChromaDB", "")
        
        # Connect buttons
        self.ollama_card.start_btn.clicked.connect(lambda: self.start_component("ollama"))
        self.ollama_card.stop_btn.clicked.connect(lambda: self.stop_component("ollama"))
        self.ollama_card.restart_btn.clicked.connect(lambda: self.restart_component("ollama"))
        
        self.streamlit_card.start_btn.clicked.connect(lambda: self.start_component("streamlit"))
        self.streamlit_card.stop_btn.clicked.connect(lambda: self.stop_component("streamlit"))
        self.streamlit_card.restart_btn.clicked.connect(lambda: self.restart_component("streamlit"))
        
        layout.addWidget(self.ollama_card)
        layout.addWidget(self.streamlit_card)
        layout.addWidget(self.chromadb_card)
        layout.addStretch()
    
    def start_component(self, name: str):
        self.api.start_component(name)
    
    def stop_component(self, name: str):
        self.api.stop_component(name)
    
    def restart_component(self, name: str):
        self.api.stop_component(name)
        __import__('time').sleep(2)
        self.api.start_component(name)