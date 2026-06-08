"""
Plugin Card Widget — Placeholder untuk Fase 3
"""

from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class PluginCard(QFrame):
    """
    Card placeholder untuk plugin.
    Fungsionalitas penuh di Fase 3.
    """
    
    def __init__(self, name: str, description: str, icon: str = "🔌", parent=None):
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
        layout.setSpacing(12)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI", 24))
        icon_label.setFixedWidth(40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(name)
        name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        info_layout.addWidget(name_label)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Toggle button (disabled — Fase 3)
        self.toggle_btn = QPushButton("OFF ○")
        self.toggle_btn.setEnabled(False)
        self.toggle_btn.setFixedWidth(70)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E1E2E;
                color: #6B7280;
                border: 1px solid #3D3D5C;
                border-radius: 10px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: normal;
            }
        """)
        layout.addWidget(self.toggle_btn)