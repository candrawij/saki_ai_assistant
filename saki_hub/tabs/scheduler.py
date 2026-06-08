"""
Scheduler Tab — Lihat & jalankan jobs
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                              QGroupBox, QScrollArea, QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class JobCard(QFrame):
    def __init__(self, name: str, cron: str, next_run: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #2D2D44;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        name_label = QLabel(name)
        name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        
        cron_label = QLabel(f"Cron: {cron}")
        cron_label.setStyleSheet("color: #94A3B8;")
        
        next_label = QLabel(f"Next: {next_run}")
        next_label.setStyleSheet("color: #94A3B8;")
        
        run_btn = QPushButton("▶ Run Now")
        run_btn.setMaximumWidth(100)
        
        layout.addWidget(name_label)
        layout.addWidget(cron_label)
        layout.addWidget(next_label)
        layout.addWidget(run_btn)


class SchedulerTab(QWidget):
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api = api_client
        
        layout = QVBoxLayout(self)
        
        title = QLabel("Scheduled Jobs")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        jobs = [
            ("backup_database", "0 2 * * *", "2:00 AM daily"),
            ("weekly_reflection", "0 3 * * 0", "3:00 AM Sunday"),
            ("cleanup_temp", "0 4 * * *", "4:00 AM daily"),
            ("health_check", "*/30 * * * *", "Every 30 minutes"),
        ]
        
        for name, cron, next_run in jobs:
            scroll_layout.addWidget(JobCard(name, cron, next_run))
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)