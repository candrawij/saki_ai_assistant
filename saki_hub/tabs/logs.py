"""
Logs Tab — Log viewer simple
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QTextEdit, QPushButton, QComboBox, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from pathlib import Path


class LogsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        
        # Controls
        controls = QHBoxLayout()
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["INFO", "WARNING", "ERROR", "DEBUG", "ALL"])
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_logs)
        
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("stopBtn")
        
        controls.addWidget(QLabel("Filter:"))
        controls.addWidget(self.filter_combo)
        controls.addStretch()
        controls.addWidget(refresh_btn)
        controls.addWidget(clear_btn)
        layout.addLayout(controls)
        
        # Log viewer
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log_viewer)
        
        self.load_logs()
    
    def load_logs(self):
        """Load log file."""
        log_path = Path("logs/saki_core.log")
        if log_path.exists():
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            
            # Filter
            filter_level = self.filter_combo.currentText()
            if filter_level != "ALL":
                lines = [l for l in lines if filter_level in l]
            
            # Tampilkan 100 terakhir
            self.log_viewer.setPlainText("".join(lines[-100:]))
        else:
            self.log_viewer.setPlainText("No log file found.")