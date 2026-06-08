"""
Logs Tab — Log viewer dengan filter & auto-refresh
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QTextEdit, QPushButton, QComboBox, QLabel,
                              QCheckBox, QFileDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QColor
from pathlib import Path
from datetime import datetime


class LogsTab(QWidget):
    """Tab untuk melihat log Saki."""
    
    def __init__(self, api_client=None, parent=None):
        super().__init__(parent)
        self.api = api_client
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # === CONTROLS ===
        controls = QHBoxLayout()
        
        # Filter
        controls.addWidget(QLabel("Level:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["ALL", "INFO", "WARNING", "ERROR", "DEBUG"])
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        controls.addWidget(self.filter_combo)
        
        controls.addStretch()
        
        # Auto-scroll
        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        controls.addWidget(self.auto_scroll_cb)
        
        # Buttons
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_logs)
        controls.addWidget(refresh_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("stopBtn")
        clear_btn.clicked.connect(self._clear)
        controls.addWidget(clear_btn)
        
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export)
        controls.addWidget(export_btn)
        
        layout.addLayout(controls)
        
        # === LOG VIEWER ===
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont("Consolas", 10))
        self.log_viewer.setStyleSheet("""
            QTextEdit {
                background-color: #0F0F1A;
                color: #E2E8F0;
                border: 1px solid #2D2D44;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.log_viewer)
        
        # === STATUS ===
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # Store all lines for filtering
        self.all_lines = []
        
        # Auto-refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.load_logs)
        self.timer.start(30000)  # Every 30 seconds
        
        # Initial load
        self.load_logs()
    
    def load_logs(self):
        """Load logs — coba API dulu, fallback ke file."""
        lines = []
        source = ""
        
        # Coba dari API
        if self.api:
            try:
                result = self.api.get_logs(lines=200)
                if result and "error" not in result:
                    logs = result.get("logs", [])
                    for log in logs:
                        lines.append(log.get("raw", ""))
                    source = "API"
            except:
                pass
        
        # Fallback: baca file langsung
        if not lines:
            log_files = [
                Path("logs/saki_core.log"),
                Path("logs/saki.log"),
                Path("logs/saki_service.log"),
            ]
            
            for log_path in log_files:
                if log_path.exists():
                    try:
                        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                        source = str(log_path)
                        break
                    except:
                        continue
        
        if not lines:
            self.log_viewer.setHtml(
                '<span style="color:#6B7280;">No logs available.<br>'
                'Start Saki Core to see logs here.</span>'
            )
            self.status_label.setText("ℹ️ No log source found")
            return
        
        self.all_lines = [l.strip() for l in lines if l.strip()]
        self._apply_filter()
        self.status_label.setText(f"✅ {len(self.all_lines)} lines from {source}")
    
    def _apply_filter(self):
        """Apply level filter dan tampilkan."""
        filter_level = self.filter_combo.currentText()
        
        # Filter
        if filter_level == "ALL":
            display_lines = self.all_lines
        else:
            display_lines = [l for l in self.all_lines if filter_level in l]
        
        # Tampilkan 200 terakhir
        display_lines = display_lines[-200:]
        
        # Render dengan warna
        self.log_viewer.clear()
        
        for line in display_lines:
            color = self._get_color(line)
            escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            self.log_viewer.append(f'<span style="color:{color};">{escaped}</span>')
        
        # Auto-scroll
        if self.auto_scroll_cb.isChecked():
            cursor = self.log_viewer.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_viewer.setTextCursor(cursor)
    
    def _get_color(self, line: str) -> str:
        """Tentukan warna berdasarkan log level."""
        if "ERROR" in line or "CRITICAL" in line:
            return "#EF4444"  # Red
        elif "WARNING" in line or "WARN" in line:
            return "#F59E0B"  # Yellow
        elif "INFO" in line:
            return "#10B981"  # Green
        elif "DEBUG" in line:
            return "#8B5CF6"  # Purple
        else:
            return "#94A3B8"  # Gray
    
    def _clear(self):
        """Clear log viewer."""
        self.log_viewer.clear()
        self.all_lines = []
        self.status_label.setText("🗑️ Cleared")
    
    def _export(self):
        """Export logs ke file."""
        if not self.all_lines:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Logs",
            f"saki_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.all_lines))
            self.status_label.setText(f"📁 Exported to: {file_path}")