"""
Windows Skills
Notifikasi, screenshot, buka aplikasi, system info
"""

import subprocess
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

# === SCREENSHOT ===

def screenshot(save_folder: str = None) -> str:
    """Tangkap layar dan simpan."""
    if save_folder is None:
        save_folder = "E:\\PrivBot\\data\\screenshots"
    
    os.makedirs(save_folder, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = os.path.join(save_folder, filename)
    
    try:
        import pyautogui
        pyautogui.screenshot(filepath)
        return filepath
    except ImportError:
        # Fallback: PIL
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            screenshot.save(filepath)
            return filepath
        except ImportError:
            # Fallback: PowerShell (simpan ke clipboard)
            subprocess.run([
                "powershell", "-Command",
                "Add-Type -AssemblyName System.Windows.Forms; "
                "[System.Windows.Forms.SendKeys]::SendWait('{PRTSC}')"
            ])
            return "📸 Screenshot disalin ke clipboard (install pyautogui/Pillow untuk save otomatis)"
    except Exception as e:
        return f"❌ Gagal screenshot: {str(e)}"

# === BUKA APLIKASI ===

def buka_aplikasi(nama: str) -> tuple[bool, str]:
    """Buka aplikasi Windows berdasarkan nama."""
    apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "kalkulator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "cmd": "cmd.exe",
        "terminal": "cmd.exe",
        "powershell": "powershell.exe",
        "task manager": "taskmgr.exe",
        "taskmanager": "taskmgr.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "browser": "msedge.exe",
        "edge": "msedge.exe",
        "chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpoint.exe",
        "ppt": "powerpoint.exe",
        "vs code": "code.exe",
        "vscode": "code.exe",
        "code": "code.exe",
        "settings": "ms-settings:",
        "pengaturan": "ms-settings:",
        "saki": "http://localhost:8501",
        "saki chat": "http://localhost:8501",
        "saki hub": "http://localhost:8502",
    }
    
    nama_lower = nama.lower().strip()
    
    # Cek di daftar aplikasi dikenal
    for key, exe in apps.items():
        if key in nama_lower or nama_lower == key:
            try:
                if exe.startswith("http"):
                    import webbrowser
                    webbrowser.open(exe)
                    return True, f"🔗 '{key}' dibuka di browser"
                subprocess.Popen([exe], shell=True)
                return True, f"✅ Aplikasi '{key}' dibuka"
            except FileNotFoundError:
                return False, f"❌ Aplikasi '{key}' tidak terinstall"
            except Exception as e:
                return False, f"❌ Gagal membuka '{key}': {str(e)}"
    
    # Coba langsung sebagai command
    try:
        subprocess.Popen([nama], shell=True)
        return True, f"✅ '{nama}' dijalankan"
    except FileNotFoundError:
        return False, f"❌ Tidak bisa membuka '{nama}'"

# === NOTIFIKASI ===

def notifikasi_windows(judul: str, pesan: str, duration: int = 5) -> bool:
    """Tampilkan notifikasi Windows."""
    try:
        from plyer import notification
        notification.notify(
            title=judul,
            message=pesan,
            app_name="Saki",
            timeout=duration,
        )
        return True
    except ImportError:
        # Fallback: PowerShell
        try:
            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $text = $template.GetElementsByTagName("text")
            $text[0].AppendChild($template.CreateTextNode("{judul}")) > $null
            $text[1].AppendChild($template.CreateTextNode("{pesan}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Saki").Show($toast)
            '''
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True, timeout=5)
            return True
        except:
            pass
    except Exception:
        pass
    
    # Ultimate fallback
    print(f"\n📢 {judul}: {pesan}\n")
    return False

# === SYSTEM INFO === (✅ TAMBAHAN)

def get_system_info() -> Dict:
    """Dapatkan informasi sistem."""
    try:
        import psutil
        
        info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": sys.version.split()[0],
            "user": os.getlogin(),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M"),
            "cpu_count": os.cpu_count(),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
        }
        return info
    except ImportError:
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": sys.version.split()[0],
            "user": os.getlogin(),
        }

# === RUN COMMAND === (✅ TAMBAHAN)

def run_command(command: str, timeout: int = 30) -> Dict:
    """Jalankan shell command dengan aman."""
    # Cek dangerous commands
    dangerous = ["del /f", "rm -rf", "format", "shutdown", "restart", "reg delete"]
    if any(d in command.lower() for d in dangerous):
        return {
            "success": False,
            "error": "⚠️ Command berbahaya tidak diizinkan",
            "command": command,
        }
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="E:\\Priv Bot",
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[:1000] if result.stdout else "",
            "stderr": result.stderr[:500] if result.stderr else "",
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"⏰ Command timeout ({timeout}s)",
            "command": command,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "command": command,
        }

# === ACTIVE WINDOW === (✅ TAMBAHAN)

def get_active_window_title() -> str:
    """Dapatkan judul window yang aktif (Windows only)."""
    if platform.system() != "Windows":
        return "Fitur ini hanya untuk Windows"
    
    try:
        import ctypes
        user32 = ctypes.windll.user32
        
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        
        return buffer.value if buffer.value else "(window tanpa judul)"
    except:
        return "(tidak bisa mendeteksi)"