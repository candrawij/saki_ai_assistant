"""
Circular Gauge Widget — Custom QWidget untuk monitoring
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen


class CircularGauge(QWidget):
    """Custom circular gauge untuk CPU, RAM, Disk."""
    
    def __init__(self, title: str = "", max_value: int = 100, unit: str = "%", parent=None):
        super().__init__(parent)
        self.title = title
        self.max_value = max_value
        self.unit = unit
        self.value = 0
        self.subtitle = ""
        self.color = QColor("#7C3AED")  # Default purple
        self.setMinimumSize(160, 180)
    
    def set_value(self, value: float, subtitle: str = ""):
        """Update gauge value dan subtitle."""
        self.value = min(value, self.max_value)
        self.subtitle = subtitle
        
        # Update color based on value ratio
        ratio = self.value / self.max_value if self.max_value > 0 else 0
        if ratio < 0.5:
            self.color = QColor("#10B981")  # Green
        elif ratio < 0.75:
            self.color = QColor("#F59E0B")  # Yellow/Orange
        elif ratio < 0.9:
            self.color = QColor("#EF4444")  # Red
        else:
            self.color = QColor("#DC2626")  # Dark red (critical)
        
        self.update()  # Trigger repaint
    
    def paintEvent(self, event):
        """Custom paint untuk circular gauge."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        size = min(width, height) - 30
        rect = QRectF((width - size) / 2, 15, size, size)
        
        # === BACKGROUND ARC ===
        bg_pen = QPen(QColor("#2D2D44"), 12)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 135 * 16, 270 * 16)
        
        # === VALUE ARC ===
        if self.value > 0:
            value_pen = QPen(self.color, 12)
            value_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(value_pen)
            span = int(270 * (self.value / self.max_value))
            painter.drawArc(rect, 135 * 16, -span * 16)
        
        # === TITLE (bottom) ===
        painter.setPen(QColor("#94A3B8"))
        font = QFont("Segoe UI", 10)
        painter.setFont(font)
        title_rect = QRectF(0, height - 25, width, 20)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self.title)
        
        # === VALUE TEXT (center) ===
        painter.setPen(QColor("#F8FAFC"))
        font = QFont("Segoe UI", 22, QFont.Weight.Bold)
        painter.setFont(font)
        value_text = f"{int(self.value)}{self.unit}"
        value_rect = QRectF(0, size * 0.3, width, size * 0.4)
        painter.drawText(value_rect, Qt.AlignmentFlag.AlignCenter, value_text)
        
        # === SUBTITLE (below value) ===
        if self.subtitle:
            painter.setPen(QColor("#94A3B8"))
            font = QFont("Segoe UI", 9)
            painter.setFont(font)
            sub_rect = QRectF(0, size * 0.55, width, size * 0.3)
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, self.subtitle)