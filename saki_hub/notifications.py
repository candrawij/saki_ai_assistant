"""
Saki Hub Notifications — Toast notifications untuk Windows
"""

from datetime import datetime
from pathlib import Path
import json
import os


class NotificationManager:
    """Manager untuk desktop notifications."""
    
    def __init__(self):
        self.enabled = True
        self.settings = {
            "backup_complete": True,
            "error_detected": True,
            "reflection_ready": True,
            "proactive_alerts": False,
        }
        self._load_settings()
    
    def _load_settings(self):
        """Load notification settings dari file."""
        try:
            settings_path = Path("data/hub_settings.json")
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.settings.update(data.get("notifications", {}))
        except:
            pass
    
    def save_settings(self):
        """Simpan notification settings."""
        try:
            settings_path = Path("data/hub_settings.json")
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {}
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data["notifications"] = self.settings
            
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except:
            pass
    
    def show(self, title: str, message: str, notif_type: str = "info", duration: int = 5):
        """
        Tampilkan notifikasi.
        
        Args:
            title: Judul notifikasi
            message: Isi pesan
            notif_type: 'backup_complete', 'error_detected', 'reflection_ready', 'proactive_alerts'
            duration: Durasi tampil (detik)
        """
        # Cek apakah notifikasi enabled
        if not self.enabled:
            return
        
        if notif_type in self.settings and not self.settings[notif_type]:
            return
        
        # Coba pakai plyer
        try:
            from plyer import notification
            notification.notify(
                title=f"Saki: {title}",
                message=message,
                app_name="Saki Hub",
                timeout=duration,
            )
            return
        except:
            pass
        
        # Fallback: PowerShell toast
        try:
            import subprocess
            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $text = $template.GetElementsByTagName("text")
            $text[0].AppendChild($template.CreateTextNode("Saki: {title}")) > $null
            $text[1].AppendChild($template.CreateTextNode("{message}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Saki").Show($toast)
            '''
            subprocess.run(['powershell', '-Command', ps_script], capture_output=True, timeout=5)
            return
        except:
            pass
        
        # Ultimate fallback: print
        print(f"\n📢 SAKI: {title}")
        print(f"   {message}\n")
    
    def notify_backup_complete(self):
        """Notifikasi backup selesai."""
        self.show("Backup Selesai", "Database backup berhasil dibuat", "backup_complete")
    
    def notify_error(self, error_msg: str):
        """Notifikasi error."""
        self.show("Error Terdeteksi", error_msg, "error_detected")
    
    def notify_reflection_ready(self):
        """Notifikasi reflection siap."""
        self.show("Reflection Siap", "Weekly reflection telah digenerate", "reflection_ready")
    
    def notify_proactive(self, message: str):
        """Notifikasi proactive alert."""
        self.show("Proactive Alert", message, "proactive_alerts")