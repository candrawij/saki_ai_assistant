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
    
    def _handle_screenshot(self, message: str) -> str:
        from src.agents.skills.windows import WindowsSkills
        ws = WindowsSkills()
        result = ws.take_screenshot()
        return f"✅ Screenshot disimpan: {result}" if result else "❌ Gagal screenshot"
    
    def _handle_open_app(self, message: str) -> str:
        app_name = message.replace("buka aplikasi", "").replace("open app", "").strip()
        if not app_name:
            return "❓ Aplikasi apa? Contoh: 'buka aplikasi notepad'"
        from src.agents.skills.windows import WindowsSkills
        ws = WindowsSkills()
        success = ws.open_app(app_name)
        return f"✅ {app_name} dibuka" if success else f"❌ Gagal membuka {app_name}"
    
    def _handle_system_info(self, message: str) -> str:
        from src.agents.skills.windows import WindowsSkills
        ws = WindowsSkills()
        info = ws.get_system_info()
        return f"📊 Sistem: {info.get('os', 'N/A')} | {info.get('processor', 'N/A')}"
    
    def _handle_command(self, message: str) -> str:
        for prefix in ["cmd:", "run:"]:
            if message.lower().startswith(prefix):
                command = message[len(prefix):].strip()
                break
        else:
            return "❓ Command apa?"
        
        dangerous = ["del ", "rm ", "format", "shutdown"]
        if any(d in command.lower() for d in dangerous):
            return "⚠️ Command berbahaya tidak diizinkan"
        
        from src.agents.skills.windows import WindowsSkills
        ws = WindowsSkills()
        result = ws.run_command(command)
        return f"🖥️ Output:\n{result.get('stdout', '')[:500]}"
    
    def get_agent_info(self):
        """Info semua agent"""
        return [
            {"name": self.task.name, "description": self.task.description},
            {"name": self.note.name, "description": self.note.description},
            {"name": self.project.name, "description": self.project.description},
            {"name": self.file.name, "description": self.file.description},
        ]