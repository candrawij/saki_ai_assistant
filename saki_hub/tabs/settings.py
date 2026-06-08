"""
Settings Tab
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QLabel, QComboBox, QCheckBox, QPushButton, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Refresh interval
        refresh_group = QGroupBox("Dashboard")
        refresh_layout = QHBoxLayout(refresh_group)
        refresh_layout.addWidget(QLabel("Refresh interval:"))
        self.refresh_combo = QComboBox()
        self.refresh_combo.addItems(["3 detik", "5 detik", "10 detik", "30 detik", "60 detik"])
        self.refresh_combo.setCurrentIndex(1)
        refresh_layout.addWidget(self.refresh_combo)
        refresh_layout.addStretch()
        layout.addWidget(refresh_group)
        
        # Notifications
        notif_group = QGroupBox("Notifications")
        notif_layout = QVBoxLayout(notif_group)
        
        self.backup_notif = QCheckBox("Backup complete")
        self.backup_notif.setChecked(True)
        self.error_notif = QCheckBox("Error detected")
        self.error_notif.setChecked(True)
        self.reflection_notif = QCheckBox("Reflection ready")
        self.reflection_notif.setChecked(True)
        self.proactive_notif = QCheckBox("Proactive alerts")
        self.proactive_notif.setChecked(False)
        
        notif_layout.addWidget(self.backup_notif)
        notif_layout.addWidget(self.error_notif)
        notif_layout.addWidget(self.reflection_notif)
        notif_layout.addWidget(self.proactive_notif)
        layout.addWidget(notif_group)
        
        # API Status
        api_group = QGroupBox("Saki Core API")
        api_layout = QHBoxLayout(api_group)
        api_layout.addWidget(QLabel("URL: http://localhost:8503"))
        self.api_status = QLabel("● Connected")
        self.api_status.setStyleSheet("color: #10B981; font-weight: bold;")
        api_layout.addStretch()
        api_layout.addWidget(self.api_status)
        layout.addWidget(api_group)
        
        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.setMaximumWidth(150)
        layout.addWidget(save_btn)
        layout.addStretch()