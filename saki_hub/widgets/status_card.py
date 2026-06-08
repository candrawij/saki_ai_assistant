"""
Status Card Widget
"""

from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ..styles import STATUS_COLORS


class StatusCard(QFrame):
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #2D2D44;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        self.setMinimumHeight(80)
        
        layout = QHBoxLayout(self)
        
        # Status indicator
        self.indicator = QLabel("●")
        self.indicator.setFont(QFont("Segoe UI", 20))
        self.indicator.setFixedWidth(30)
        
        # Info
        info_layout = QVBoxLayout()
        self.name_label = QLabel(name)
        self.name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        
        self.detail_label = QLabel("Checking...")
        self.detail_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.detail_label)
        
        layout.addWidget(self.indicator)
        layout.addLayout(info_layout)
        layout.addStretch()
    
    def set_status(self, status: str, detail: str = ""):
        color = STATUS_COLORS.get(status, STATUS_COLORS["unknown"])
        self.indicator.setStyleSheet(f"color: {color};")
        self.detail_label.setText(detail)