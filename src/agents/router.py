"""
AgentRouter — Keyword + pattern routing
"""

import re
from typing import Tuple, Optional


class AgentRouter:
    def __init__(self):
        from src.agents.task_agent import TaskAgent
        from src.agents.note_agent import NoteAgent
        from src.agents.project_agent import ProjectAgent
        from src.agents.file_agent import FileAgent
        
        self.task = TaskAgent()
        self.note = NoteAgent()
        self.project = ProjectAgent()
        self.file = FileAgent()
        
        # Special commands handler
        self.special_keywords = {
            "screenshot": self._handle_screenshot,
            "tangkapan layar": self._handle_screenshot,
            "ss": self._handle_screenshot,
            "buka aplikasi": self._handle_open_app,
            "open app": self._handle_open_app,
            "info sistem": self._handle_system_info,
            "system info": self._handle_system_info,
            "cmd:": self._handle_command,
            "run:": self._handle_command,
        }
    
    def route(self, message: str) -> Tuple[Optional[object], Optional[str]]:
        """
        Route pesan ke agent.
        Returns: (agent_or_special_string, message)
        """
        msg = message.lower()
        
        # === SPECIAL COMMANDS ===
        for keyword, handler in self.special_keywords.items():
            if msg.startswith(keyword) or msg == keyword:
                return "special", message
        
        # === TASK — cek dulu ===
        task_keywords = ["tambah task", "task:", "tugas:", "list task", "daftar tugas",
                         "apa tugas", "tandai task", "task selesai", "selesaikan task",
                         "deadline", "tenggat", "ingatkan", "reminder",
                         "buat task", "buat tugas", "add task", "todo:"]
        if any(k in msg for k in task_keywords):
            return self.task, message
        
        # === NOTE ===
        note_keywords = ["catat:", "note:", "catatan:", "list catatan", "list note",
                         "daftar catatan", "tampilkan catatan", "cari catatan", "cari note",
                         "hapus catatan", "hapus note", "buat catatan", "tulis catatan"]
        if any(k in msg for k in note_keywords):
            return self.note, message
        
        # === PROJECT ===
        project_keywords = ["update project", "update proyek", "project:", "proyek:",
                            "progress project", "progress proyek", "status project",
                            "status proyek", "list project", "daftar proyek",
                            "laporan project", "report project"]
        if any(k in msg for k in project_keywords):
            return self.project, message
        
        # === FILE — terakhir, PASTIKAN bukan keyword agent lain ===
        all_other_kw = task_keywords + note_keywords + project_keywords
        
        if not any(k in msg for k in all_other_kw):
            file_keywords = ["buka folder", "buka file", "buka dokumen", "buka",
                             "cari file", "cari dokumen", "cari",
                             "list folder", "isi folder", "list",
                             "ringkas folder", "ringkasan folder", "ringkas"]
            if any(k in msg for k in file_keywords):
                return self.file, message
        
        # === PATTERN MATCHING (fallback) ===
        # Deteksi perintah file implisit
        if re.search(r"buka\s+(folder|file|dokumen)\s+", msg) and not any(k in msg for k in all_other_kw):
            return self.file, message
        
        # Deteksi perintah note implisit
        if re.search(r"(catat|note|simpan)\s+(.+)", msg):
            return self.note, message
        
        # Bukan perintah agent → chat biasa
        return None, None
    
    def execute_special(self, message: str) -> str:
        """Eksekusi special command"""
        msg = message.lower()
        for keyword, handler in self.special_keywords.items():
            if msg.startswith(keyword) or msg == keyword:
                return handler(message)
        return "❓ Perintah khusus tidak dikenali"
    
    # ========== SPECIAL COMMAND HANDLERS ==========
    # Semua pakai module-level functions dari skills.windows
    
    def _handle_screenshot(self, message: str) -> str:
        """Handle screenshot command."""
        from src.agents.skills.windows import screenshot
        result = screenshot()
        return f"✅ Screenshot disimpan: {result}" if result else "❌ Gagal screenshot"
    
    def _handle_open_app(self, message: str) -> str:
        """Handle open app command."""
        app_name = message.replace("buka aplikasi", "").replace("open app", "").strip()
        if not app_name:
            return "❓ Aplikasi apa? Contoh: 'buka aplikasi notepad'"
        
        from src.agents.skills.windows import buka_aplikasi
        success, msg = buka_aplikasi(app_name)
        return msg  # buka_aplikasi already returns formatted message
    
    def _handle_system_info(self, message: str) -> str:
        """Handle system info command."""
        from src.agents.skills.windows import get_system_info
        info = get_system_info()
        
        response = "📊 Informasi Sistem:\n"
        response += f"  • OS: {info.get('os', 'N/A')} {info.get('os_version', '')}\n"
        response += f"  • Processor: {info.get('processor', 'N/A')}\n"
        response += f"  • User: {info.get('user', 'N/A')}\n"
        
        if 'ram_total_gb' in info:
            response += f"  • RAM: {info['ram_total_gb']} GB\n"
        if 'boot_time' in info:
            response += f"  • Boot: {info['boot_time']}\n"
        
        return response
    
    def _handle_command(self, message: str) -> str:
        """Handle shell command execution."""
        for prefix in ["cmd:", "run:"]:
            if message.lower().startswith(prefix):
                command = message[len(prefix):].strip()
                break
        else:
            return "❓ Command apa? Contoh: 'cmd: dir'"
        
        if not command:
            return "❓ Command apa yang ingin dijalankan?"
        
        # Cek dangerous commands
        dangerous = ["del ", "rm ", "format", "shutdown", "restart", "reg delete"]
        if any(d in command.lower() for d in dangerous):
            return "⚠️ Command berbahaya tidak diizinkan untuk alasan keamanan."
        
        from src.agents.skills.windows import run_command
        result = run_command(command)
        
        if not result.get("success"):
            error = result.get("error", result.get("stderr", "Unknown error"))
            return f"❌ Command gagal:\n{error[:300]}"
        
        response = f"🖥️ Command: `{command}`\n"
        if result.get("stdout"):
            response += f"```\n{result['stdout'][:500]}\n```"
        return response
    
    def get_agent_info(self):
        """Info semua agent."""
        return [
            {"name": self.task.name, "description": self.task.description},
            {"name": self.note.name, "description": self.note.description},
            {"name": self.project.name, "description": self.project.description},
            {"name": self.file.name, "description": self.file.description},
        ]