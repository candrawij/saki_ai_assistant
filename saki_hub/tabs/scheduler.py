"""
Scheduler Tab — Lihat & jalankan scheduled jobs
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                              QGroupBox, QScrollArea, QFrame, QHBoxLayout,
                              QMessageBox)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont


class JobCard(QFrame):
    """Card untuk satu scheduled job."""
    
    def __init__(self, job_id: str, name: str, trigger: str, next_run: str, parent=None):
        super().__init__(parent)
        self.job_id = job_id
        
        self.setStyleSheet("""
            QFrame {
                background-color: #2D2D44;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        
        # Name
        name_label = QLabel(f"📋 {name}")
        name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(name_label)
        
        # Trigger
        trigger_label = QLabel(f"Trigger: {trigger}")
        trigger_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(trigger_label)
        
        # Next run
        next_label = QLabel(f"Next run: {next_run}")
        next_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(next_label)
        
        # Run Now button
        run_btn = QPushButton("▶ Run Now")
        run_btn.setMaximumWidth(100)
        run_btn.setObjectName("startBtn")
        layout.addWidget(run_btn)
        
        # Store button reference
        self.run_btn = run_btn


class SchedulerTab(QWidget):
    """Tab untuk melihat dan menjalankan scheduled jobs."""
    
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api = api_client
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Scheduled Jobs")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        subtitle = QLabel("Tugas terjadwal Saki — klik Run Now untuk eksekusi manual")
        subtitle.setStyleSheet("color: #94A3B8;")
        layout.addWidget(subtitle)
        
        # Scroll area untuk jobs
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.addStretch()
        self.scroll.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Jobs")
        refresh_btn.clicked.connect(self.refresh_data)
        layout.addWidget(refresh_btn)
        
        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(30000)  # Every 30 seconds
        
        # Job cards storage
        self.job_cards = []
        
        # Initial load
        self.refresh_data()
    
    def refresh_data(self):
        """Fetch jobs dari API dan update display."""
        # Clear existing cards
        for card in self.job_cards:
            self.scroll_layout.removeWidget(card)
            card.deleteLater()
        self.job_cards.clear()
        
        try:
            jobs = self.api.get_scheduler()
            
            if not jobs or "error" in jobs:
                no_jobs = QLabel("Tidak ada scheduled jobs aktif")
                no_jobs.setStyleSheet("color: #94A3B8; padding: 20px;")
                self.job_cards.append(no_jobs)
                self.scroll_layout.insertWidget(0, no_jobs)
                self.status_label.setText("ℹ️ No jobs found")
                return
            
            for i, job in enumerate(jobs):
                if isinstance(job, dict):
                    job_id = job.get("id", f"job_{i}")
                    name = job.get("name", job_id)
                    trigger = job.get("trigger", "N/A")
                    next_run = job.get("next_run", "N/A")
                    
                    card = JobCard(job_id, name, trigger, next_run)
                    card.run_btn.clicked.connect(
                        lambda checked, jid=job_id: self._run_job(jid)
                    )
                    
                    self.job_cards.append(card)
                    self.scroll_layout.insertWidget(i, card)
            
            self.status_label.setText(f"✅ {len(jobs)} jobs loaded")
            
        except Exception as e:
            self.status_label.setText(f"❌ Failed to load jobs: {str(e)[:50]}")
    
    def _run_job(self, job_id: str):
        """Jalankan job secara manual."""
        try:
            result = self.api.run_job(job_id)
            
            if "error" in result:
                QMessageBox.warning(
                    self, "Error",
                    f"Gagal menjalankan job '{job_id}':\n{result['error']}"
                )
                self.status_label.setText(f"❌ Job '{job_id}' failed")
            else:
                QMessageBox.information(
                    self, "Sukses",
                    f"Job '{job_id}' berhasil dijalankan!"
                )
                self.status_label.setText(f"✅ Job '{job_id}' completed")
                self.refresh_data()
                
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Error menjalankan job: {str(e)}"
            )