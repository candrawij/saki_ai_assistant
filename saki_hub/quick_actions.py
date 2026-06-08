"""
Quick Actions — Shortcut untuk aksi cepat dari Saki Hub
"""

import os
import webbrowser
import subprocess
from pathlib import Path
from datetime import datetime


class QuickActions:
    """Aksi cepat: screenshot, open file, open chat, open terminal."""
    
    def __init__(self):
        self.screenshots_dir = Path("data/screenshots")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    def take_screenshot(self) -> str | None:
        """Ambil screenshot, return path atau None."""
        try:
            import pyautogui
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.screenshots_dir / f"screenshot_{timestamp}.png"
            pyautogui.screenshot(str(path))
            return str(path)
        except ImportError:
            try:
                from PIL import ImageGrab
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = self.screenshots_dir / f"screenshot_{timestamp}.png"
                ImageGrab.grab().save(str(path))
                return str(path)
            except ImportError:
                return None
        except Exception:
            return None
    
    def open_file_dialog(self) -> str | None:
        """Buka file dialog, return path atau None."""
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            caption="Buka File",
            directory=str(Path.home()),
            filter="Semua File (*.*)"
        )
        if file_path:
            os.startfile(file_path)
            return file_path
        return None
    
    def open_chat(self):
        """Buka Saki Chat di browser."""
        webbrowser.open("http://localhost:8501")
    
    def open_folder(self, path: str = None):
        """Buka folder di Explorer."""
        if path and os.path.exists(path):
            os.startfile(path)
        else:
            os.startfile(str(Path.home()))
    
    def open_terminal(self):
        """Buka terminal di folder project."""
        try:
            subprocess.Popen('cmd.exe', cwd=str(Path.cwd()))
        except:
            pass
    
    def open_notepad(self):
        """Buka Notepad untuk catatan cepat."""
        subprocess.Popen(['notepad.exe'])
    
    def create_backup(self) -> dict:
        """Trigger backup via API."""
        import requests
        try:
            r = requests.post("http://localhost:8502/backup/create", timeout=30)
            return r.json()
        except:
            return {"error": "API not available"}