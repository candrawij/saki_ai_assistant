"""
Styles — Dark theme untuk Saki Hub
"""

# ========== STATUS COLORS ==========
STATUS_COLORS = {
    "running": "#10B981",    # Green
    "stopped": "#EF4444",    # Red
    "disabled": "#6B7280",   # Gray
    "warning": "#F59E0B",    # Yellow
    "error": "#EF4444",      # Red
    "unknown": "#6B7280",    # Gray
}

# ========== DARK THEME ==========
DARK_THEME = """
/* === MAIN WINDOW === */
QMainWindow {
    background-color: #1E1E2E;
}

QWidget {
    background-color: #1E1E2E;
    color: #F8FAFC;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

/* === TAB WIDGET === */
QTabWidget::pane {
    border: 1px solid #2D2D44;
    background-color: #1E1E2E;
}

QTabWidget::tab-bar {
    alignment: left;
}

QTabBar::tab {
    background-color: #2D2D44;
    color: #94A3B8;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background-color: #7C3AED;
    color: #FFFFFF;
}

QTabBar::tab:hover:!selected {
    background-color: #3D3D5C;
}

/* === LABELS === */
QLabel {
    color: #F8FAFC;
}

QLabel#title {
    font-size: 16px;
    font-weight: bold;
    color: #FFFFFF;
}

QLabel#subtitle {
    font-size: 12px;
    color: #94A3B8;
}

QLabel#value {
    font-size: 28px;
    font-weight: bold;
    color: #10B981;
}

QLabel#value-warning {
    font-size: 28px;
    font-weight: bold;
    color: #F59E0B;
}

QLabel#value-error {
    font-size: 28px;
    font-weight: bold;
    color: #EF4444;
}

/* === BUTTONS === */
QPushButton {
    background-color: #7C3AED;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #6D28D9;
}

QPushButton:pressed {
    background-color: #5B21B6;
}

QPushButton#stopBtn {
    background-color: #EF4444;
}

QPushButton#stopBtn:hover {
    background-color: #DC2626;
}

QPushButton#restartBtn {
    background-color: #F59E0B;
}

QPushButton#restartBtn:hover {
    background-color: #D97706;
}

QPushButton#startBtn {
    background-color: #10B981;
}

QPushButton#startBtn:hover {
    background-color: #059669;
}

QPushButton#quickBtn {
    background-color: #2D2D44;
    border: 1px solid #3D3D5C;
    padding: 12px;
    font-weight: normal;
}

QPushButton#quickBtn:hover {
    background-color: #3D3D5C;
}

/* === GROUP BOX === */
QGroupBox {
    border: 1px solid #2D2D44;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #94A3B8;
}

/* === TEXT EDIT (LOG VIEWER) === */
QTextEdit, QPlainTextEdit {
    background-color: #0F0F1A;
    color: #E2E8F0;
    border: 1px solid #2D2D44;
    border-radius: 6px;
    padding: 8px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}

/* === SCROLL BAR === */
QScrollBar:vertical {
    background-color: #1E1E2E;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #3D3D5C;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4D4D6C;
}

QScrollBar:horizontal {
    background-color: #1E1E2E;
    height: 10px;
}

QScrollBar::handle:horizontal {
    background-color: #3D3D5C;
    border-radius: 5px;
}

/* === PROGRESS BAR === */
QProgressBar {
    border: none;
    background-color: #2D2D44;
    border-radius: 10px;
    height: 6px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #7C3AED;
    border-radius: 10px;
}

/* === COMBO BOX === */
QComboBox {
    background-color: #2D2D44;
    color: #F8FAFC;
    border: 1px solid #3D3D5C;
    border-radius: 6px;
    padding: 6px 12px;
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #2D2D44;
    color: #F8FAFC;
    selection-background-color: #7C3AED;
}

/* === CHECKBOX === */
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #3D3D5C;
}

QCheckBox::indicator:checked {
    background-color: #7C3AED;
    border-color: #7C3AED;
}

/* === LINE EDIT === */
QLineEdit {
    background-color: #2D2D44;
    color: #F8FAFC;
    border: 1px solid #3D3D5C;
    border-radius: 6px;
    padding: 6px 12px;
}

QLineEdit:focus {
    border-color: #7C3AED;
}

/* === SPIN BOX === */
QSpinBox {
    background-color: #2D2D44;
    color: #F8FAFC;
    border: 1px solid #3D3D5C;
    border-radius: 6px;
    padding: 4px 8px;
}

/* === STATUS BAR === */
QStatusBar {
    background-color: #16213e;
    border-top: 1px solid #2D2D44;
    color: #94A3B8;
}
"""

# ========== STYLE SHEET (alias untuk kompatibilitas) ==========
STYLE_SHEET = DARK_THEME