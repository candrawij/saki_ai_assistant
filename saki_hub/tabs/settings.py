"""
Settings Tab — Konfigurasi Saki Hub
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QLabel, QComboBox, QCheckBox, QPushButton, 
                              QGroupBox, QLineEdit, QSpinBox, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class SettingsTab(QWidget):
    """Tab untuk konfigurasi Saki Hub."""
    
    def __init__(self, api_client=None, parent=None):
        super().__init__(parent)
        self.api = api_client
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # === REFRESH INTERVAL ===
        refresh_group = QGroupBox("Dashboard Refresh")
        refresh_layout = QHBoxLayout(refresh_group)
        
        refresh_layout.addWidget(QLabel("Refresh interval:"))
        self.refresh_combo = QComboBox()
        self.refresh_combo.addItems(["3 detik", "5 detik", "10 detik", "30 detik", "60 detik"])
        self.refresh_combo.setCurrentIndex(1)  # Default: 5 detik
        refresh_layout.addWidget(self.refresh_combo)
        refresh_layout.addStretch()
        layout.addWidget(refresh_group)
        
        # === THEME (PLACEHOLDER) ===
        theme_group = QGroupBox("Appearance")
        theme_layout = QHBoxLayout(theme_group)
        theme_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark (Default)", "Light (Coming Soon)"])
        self.theme_combo.setEnabled(False)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        layout.addWidget(theme_group)
        
        # === NOTIFICATIONS ===
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
        
        # === API CONNECTION ===
        api_group = QGroupBox("Saki Core API")
        api_layout = QVBoxLayout(api_group)
        
        # URL row
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.api_url = QLineEdit("http://localhost:8502")
        url_layout.addWidget(self.api_url)
        url_layout.addStretch()
        api_layout.addLayout(url_layout)
        
        # Status + Test button
        status_layout = QHBoxLayout()
        self.api_status = QLabel("● Unknown")
        self.api_status.setStyleSheet("color: #6B7280; font-weight: bold;")
        status_layout.addWidget(self.api_status)
        status_layout.addStretch()
        
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test_connection)
        status_layout.addWidget(test_btn)
        api_layout.addLayout(status_layout)
        
        layout.addWidget(api_group)
        
        # === SAVE BUTTON ===
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setMaximumWidth(200)
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        # Test connection on startup
        QTimer.singleShot(1000, self._test_connection)
    
    def _test_connection(self):
        """Test koneksi ke Saki Core API."""
        if not self.api:
            self.api_status.setText("● No API client")
            self.api_status.setStyleSheet("color: #6B7280; font-weight: bold;")
            return
        
        # Update URL dari input
        current_url = self.api.base_url
        new_url = self.api_url.text().strip()
        if new_url and new_url != current_url:
            self.api.base_url = new_url
        
        if self.api.check_connection():
            self.api_status.setText("● Connected")
            self.api_status.setStyleSheet("color: #10B981; font-weight: bold;")
        else:
            self.api_status.setText("● Disconnected")
            self.api_status.setStyleSheet("color: #EF4444; font-weight: bold;")
    
    def _save_settings(self):
        """Simpan settings."""
        # Update API URL
        if self.api:
            self.api.base_url = self.api_url.text().strip()
        
        # Update notification settings
        from ..notifications import NotificationManager
        notif = NotificationManager()
        notif.settings["backup_complete"] = self.backup_notif.isChecked()
        notif.settings["error_detected"] = self.error_notif.isChecked()
        notif.settings["reflection_ready"] = self.reflection_notif.isChecked()
        notif.settings["proactive_alerts"] = self.proactive_notif.isChecked()
        notif.save_settings()
        
        QMessageBox.information(self, "Saved", "✅ Settings berhasil disimpan!")