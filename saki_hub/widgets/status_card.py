"""
Status Card Widget — Untuk menampilkan status komponen
"""

from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ..styles import STATUS_COLORS


class StatusCard(QFrame):
    """
    Card status komponen.
    Digunakan di Overview tab (tanpa buttons).
    """
    
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #2D2D44;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        self.setMinimumHeight(60)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Status indicator (bulat)
        self.indicator = QLabel("●")
        self.indicator.setFont(QFont("Segoe UI", 20))
        self.indicator.setFixedWidth(30)
        self.indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.name_label = QLabel(name)
        self.name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        
        self.detail_label = QLabel("Checking...")
        self.detail_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.detail_label.setWordWrap(True)
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.detail_label)
        
        layout.addWidget(self.indicator)
        layout.addLayout(info_layout)
        layout.addStretch()
    
    def set_status(self, status: str, detail: str = ""):
        """
        Update status card.
        
        Args:
            status: 'running', 'stopped', 'disabled', 'warning', 'error', 'unknown'
            detail: Teks detail (port, info tambahan)
        """
        color = STATUS_COLORS.get(status, STATUS_COLORS["unknown"])
        self.indicator.setStyleSheet(f"color: {color};")
        
        if detail:
            self.detail_label.setText(detail)
        else:
            status_text = status.capitalize()
            self.detail_label.setText(status_text)