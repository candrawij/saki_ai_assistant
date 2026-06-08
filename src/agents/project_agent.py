"""
ProjectAgent — Tracking progress proyek
"""

import json
from datetime import datetime
from pathlib import Path
from .base import BaseAgent

class ProjectAgent(BaseAgent):
    def __init__(self, data_folder: str = "data/projects"):
        super().__init__(
            name="Project Agent",
            description="Tracking progress dan status proyek"
        )
        self.data_folder = Path(data_folder)
        self.data_folder.mkdir(parents=True, exist_ok=True)
        self.projects_file = self.data_folder / "projects.json"
        self._load_projects()
        self.keywords = [
            "update project", "update proyek",
            "project:", "proyek:",
            "progress project", "progress proyek",
            "status project", "status proyek",
            "list project", "daftar proyek",
            "buat laporan", "laporan project",
        ]
    
    def _load_projects(self):
        if self.projects_file.exists():
            with open(self.projects_file, "r", encoding="utf-8") as f:
                self.projects = json.load(f)
        else:
            self.projects = []
    
    def _save_projects(self):
        with open(self.projects_file, "w", encoding="utf-8") as f:
            json.dump(self.projects, f, ensure_ascii=False, indent=2)
    
    def can_handle(self, message: str) -> bool:
        msg = message.lower()
        return any(kw in msg for kw in self.keywords)
    
    def _find_project(self, nama: str) -> dict | None:
        """Cari proyek berdasarkan nama."""
        for p in self.projects:
            if nama.lower() in p["nama"].lower():
                return p
        return None
    
    def execute(self, message: str) -> str:
        msg = message.lower()
        
        # Tambah/update project
        if any(kw in msg for kw in ["update project", "update proyek", "project:", "proyek:"]):
            # Ekstrak isi
            for prefix in ["update project", "update proyek", "project:", "proyek:"]:
                if prefix in msg:
                    idx = message.lower().find(prefix)
                    isi = message[idx + len(prefix):].strip()
                    break
            else:
                isi = message.strip()
            
            if not isi:
                return "Project apa yang ingin diupdate? Contoh: 'update project website: sudah masuk testing'"
            
            # Split: "nama: status"
            if ":" in isi:
                nama, status = isi.split(":", 1)
                nama, status = nama.strip(), status.strip()
            else:
                nama = isi
                status = "aktif"
            
            existing = self._find_project(nama)
            
            if existing:
                old_status = existing.get("status", "aktif")
                existing["status"] = status
                existing["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                existing["history"].append({
                    "tanggal": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "dari": old_status,
                    "ke": status,
                })
                self._save_projects()
                return f"✅ Project '{existing['nama']}' diupdate: {old_status} → {status}"
            else:
                project = {
                    "id": len(self.projects) + 1,
                    "nama": nama,
                    "status": status,
                    "dibuat": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "history": [{
                        "tanggal": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "dari": "baru",
                        "ke": status,
                    }],
                    "milestones": [],
                }
                self.projects.append(project)
                self._save_projects()
                return f"✅ Project baru '{nama}' dibuat dengan status: {status}"
        
        # Cek progress/status project
        if any(kw in msg for kw in ["progress project", "progress proyek", "status project", "status proyek"]):
            # Ekstrak nama project
            for prefix in ["progress project", "progress proyek", "status project", "status proyek"]:
                if prefix in msg:
                    nama = message.lower().replace(prefix, "").strip()
                    break
            else:
                nama = ""
            
            if nama:
                existing = self._find_project(nama)
                if existing:
                    history_str = ""
                    for h in existing.get("history", [])[-5:]:
                        history_str += f"    {h['tanggal']}: {h['dari']} → {h['ke']}\n"
                    
                    return (
                        f"Project: {existing['nama']}\n"
                        f"Status: {existing['status']}\n"
                        f"Dibuat: {existing['dibuat']}\n"
                        f"Update: {existing['updated']}\n"
                        f"History:\n{history_str}"
                    )
                return f"Project '{nama}' tidak ditemukan"
            
            # Tampilkan semua project
            if not self.projects:
                return "Belum ada project. Mulai dengan: 'project: nama, status'"
            
            response = "Progress semua project:\n"
            for p in self.projects:
                emoji = {"selesai": "✅", "aktif": "🔄", "testing": "🧪", "pending": "⏸️"}.get(p["status"], "📌")
                response += f"  {emoji} {p['nama']}: {p['status']}\n"
            
            return response
        
        # List project
        if "list project" in msg or "daftar proyek" in msg:
            if not self.projects:
                return "Belum ada project."
            
            response = "Daftar project:\n"
            for p in self.projects:
                response += f"  #{p['id']} {p['nama']} [{p['status']}] — Updated: {p['updated']}\n"
            
            return response
        
        # Laporan project
        if "buat laporan" in msg or "laporan project" in msg:
            if not self.projects:
                return "Belum ada project untuk dilaporkan."
            
            aktif = [p for p in self.projects if p["status"] != "selesai"]
            selesai = [p for p in self.projects if p["status"] == "selesai"]
            
            response = f"📊 Laporan Project — {datetime.now().strftime('%d %B %Y')}\n\n"
            response += f"Total project: {len(self.projects)}\n"
            response += f"Aktif: {len(aktif)} | Selesai: {len(selesai)}\n\n"
            
            if aktif:
                response += "Project Aktif:\n"
                for p in aktif:
                    response += f"  • {p['nama']} — {p['status']} (updated: {p['updated']})\n"
            
            if selesai:
                response += f"\nProject Selesai:\n"
                for p in selesai:
                    response += f"  • {p['nama']} — selesai pada {p['updated']}\n"
            
            return response
        
        return "Maaf, saya tidak mengerti. Coba: update project [nama: status], progress [nama], list project, laporan project"