"""
Windows Skills
Notifikasi, screenshot, buka aplikasi
"""

import subprocess
import os
from datetime import datetime
from pathlib import Path

def screenshot(save_folder: str = None) -> str:
    """Tangkap layar dan simpan."""
    if save_folder is None:
        save_folder = "E:\\Priv Bot\\data\\screenshots"
    
    os.makedirs(save_folder, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = os.path.join(save_folder, filename)
    
    try:
        import pyautogui
        pyautogui.screenshot(filepath)
        return filepath
    except ImportError:
        # Fallback: pakai PowerShell
        subprocess.run([
            "powershell", "-Command",
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"[System.Windows.Forms.SendKeys]::SendWait('{{PRTSC}}')"
        ])
        return "Screenshot disalin ke clipboard (pyautogui tidak terinstall)"
    except Exception as e:
        return f"Gagal screenshot: {str(e)}"

def buka_aplikasi(nama: str) -> tuple[bool, str]:
    """Buka aplikasi Windows berdasarkan nama."""
    apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "kalkulator": "calc.exe",
        "paint": "mspaint.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "task manager": "taskmgr.exe",
        "explorer": "explorer.exe",
        "browser": "msedge.exe",
        "edge": "msedge.exe",
        "chrome": "chrome.exe",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpoint.exe",
        "vs code": "code.exe",
        "vscode": "code.exe",
    }
    
    nama_lower = nama.lower().strip()
    
    # Cek di daftar aplikasi dikenal
    for key, exe in apps.items():
        if key in nama_lower:
            try:
                subprocess.Popen([exe])
                return True, f"Aplikasi '{key}' dibuka"
            except FileNotFoundError:
                return False, f"Aplikasi '{key}' tidak terinstall"
    
    # Coba langsung sebagai command
    try:
        subprocess.Popen([nama])
        return True, f"'{nama}' dijalankan"
    except FileNotFoundError:
        return False, f"Tidak bisa membuka '{nama}'"

def notifikasi_windows(judul: str, pesan: str) -> bool:
    """Tampilkan notifikasi Windows."""
    try:
        from plyer import notification
        notification.notify(
            title=judul,
            message=pesan,
            app_name="Saki",
            timeout=5,
        )
        return True
    except ImportError:
        # Fallback: PowerShell
        subprocess.run([
            "powershell", "-Command",
            f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $text = $template.GetElementsByTagName("text")
            $text[0].AppendChild($template.CreateTextNode("{judul}")) > $null
            $text[1].AppendChild($template.CreateTextNode("{pesan}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Saki").Show($toast)
            """
        ])
        return True
    except Exception:
        return False