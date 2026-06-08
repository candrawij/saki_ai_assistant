"""
AgentRouter — Hard-coded keyword routing
"""

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
    
    def route(self, message: str):
        msg = message.lower()
        
        # TASK — cek dulu
        if any(k in msg for k in ["tambah task", "task:", "tugas:", "list task", "daftar tugas",
                                     "apa tugas", "tandai task", "task selesai", "selesaikan task",
                                     "deadline", "tenggat", "ingatkan", "reminder"]):
            return self.task, self.task.name
        
        # NOTE
        if any(k in msg for k in ["catat:", "note:", "catatan:", "list catatan", "list note",
                                     "daftar catatan", "tampilkan catatan", "cari catatan", "cari note",
                                     "hapus catatan", "hapus note"]):
            return self.note, self.note.name
        
        # PROJECT
        if any(k in msg for k in ["update project", "update proyek", "project:", "proyek:",
                                     "progress project", "progress proyek", "status project",
                                     "status proyek", "list project", "daftar proyek",
                                     "laporan project"]):
            return self.project, self.project.name
        
        # FILE — terakhir, dan PASTIKAN bukan keyword agent lain
        task_kw = ["task", "tugas", "deadline", "tenggat", "reminder", "ingatkan"]
        note_kw = ["catatan", "note"]
        project_kw = ["project", "proyek"]
        all_agent_kw = task_kw + note_kw + project_kw
        
        if not any(k in msg for k in all_agent_kw):
            if any(k in msg for k in ["buka folder", "buka file", "buka dokumen", "buka",
                                         "cari file", "cari dokumen", "cari",
                                         "list folder", "isi folder", "list",
                                         "ringkas folder", "ringkasan folder", "ringkas"]):
                return self.file, self.file.name
        
        return None, None