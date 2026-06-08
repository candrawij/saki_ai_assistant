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
        
        # ✅ TAMBAHAN: Auto-create default projects
        if not self.projects:
            self._create_default_projects()
        
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
        self.data_folder.mkdir(parents=True, exist_ok=True)
        with open(self.projects_file, "w", encoding="utf-8") as f:
            json.dump(self.projects, f, ensure_ascii=False, indent=2)
    
    def _create_default_projects(self):
        """Buat project default biar gak kosong."""
        defaults = [
            {"nama": "Saki AI", "status": "aktif", "deskripsi": "Personal AI Ecosystem"},
            {"nama": "Skripsi", "status": "pending", "deskripsi": "Tugas akhir"},
        ]
        for i, d in enumerate(defaults, 1):
            self.projects.append({
                "id": i,
                "nama": d["nama"],
                "status": d["status"],
                "deskripsi": d["deskripsi"],
                "dibuat": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "history": [{
                    "tanggal": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "dari": "baru",
                    "ke": d["status"],
                }],
                "milestones": [],
            })
        self._save_projects()
    
    def _get_next_id(self) -> int:
        """Generate ID baru."""
        if not self.projects:
            return 1
        return max(p["id"] for p in self.projects) + 1
    
    def can_handle(self, message: str) -> bool:
        msg = message.lower()
        return any(kw in msg for kw in self.keywords)
    
    def _find_project(self, nama: str) -> dict | None:
        """Cari proyek berdasarkan nama (fuzzy)."""
        nama_lower = nama.lower()
        for p in self.projects:
            if nama_lower in p["nama"].lower() or p["nama"].lower() in nama_lower:
                return p
        return None
    
    def execute(self, message: str) -> str:
        msg = message.lower()
        
        # === TAMBAH / UPDATE PROJECT ===
        if any(kw in msg for kw in ["update project", "update proyek", "project:", "proyek:"]):
            for prefix in ["update project", "update proyek", "project:", "proyek:"]:
                if prefix in msg:
                    idx = message.lower().find(prefix)
                    isi = message[idx + len(prefix):].strip()
                    break
            else:
                isi = message.strip()
            
            if not isi:
                return "❓ Project apa? Contoh: 'update project website: sudah masuk testing'"
            
            # Split "nama: status"
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
                emoji = self._status_emoji(status)
                return f"✅ Project '{existing['nama']}' diupdate: {old_status} → {emoji} {status}"
            else:
                project = {
                    "id": self._get_next_id(),
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
                emoji = self._status_emoji(status)
                return f"✅ Project baru '{nama}' dibuat: {emoji} {status}"
        
        # === PROGRESS / STATUS ===
        if any(kw in msg for kw in ["progress project", "progress proyek", "status project", "status proyek"]):
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
                        emoji_dari = self._status_emoji(h["dari"])
                        emoji_ke = self._status_emoji(h["ke"])
                        history_str += f"    {h['tanggal']}: {emoji_dari} {h['dari']} → {emoji_ke} {h['ke']}\n"
                    
                    emoji = self._status_emoji(existing["status"])
                    
                    response = (
                        f"📊 Project: {existing['nama']}\n"
                        f"   Status: {emoji} {existing['status']}\n"
                        f"   Dibuat: {existing['dibuat']}\n"
                        f"   Update: {existing['updated']}\n"
                    )
                    
                    # ✅ TAMBAHAN: Tampilkan milestones
                    if existing.get("milestones"):
                        response += f"   Milestones:\n"
                        for m in existing["milestones"]:
                            done = "✅" if m.get("done") else "⏳"
                            response += f"     {done} {m['nama']}\n"
                    
                    if history_str.strip():
                        response += f"   History:\n{history_str}"
                    
                    return response
                return f"❌ Project '{nama}' tidak ditemukan"
            
            # Tampilkan semua project
            if not self.projects:
                return "📋 Belum ada project. Mulai dengan: 'project: nama, status'"
            
            response = "📊 Progress semua project:\n"
            for p in self.projects:
                emoji = self._status_emoji(p["status"])
                response += f"  {emoji} {p['nama']}: {p['status']}\n"
            
            return response
        
        # === LIST PROJECT ===
        if "list project" in msg or "daftar proyek" in msg:
            if not self.projects:
                return "📋 Belum ada project."
            
            response = "📋 Daftar project:\n"
            for p in self.projects:
                emoji = self._status_emoji(p["status"])
                response += f"  #{p['id']} {emoji} {p['nama']} [{p['status']}] — Updated: {p['updated']}\n"
            
            return response
        
        # === LAPORAN PROJECT ===
        if "buat laporan" in msg or "laporan project" in msg:
            if not self.projects:
                return "📋 Belum ada project untuk dilaporkan."
            
            aktif = [p for p in self.projects if p["status"] not in ["selesai", "done", "completed"]]
            selesai = [p for p in self.projects if p["status"] in ["selesai", "done", "completed"]]
            
            response = f"📊 LAPORAN PROJECT — {datetime.now().strftime('%d %B %Y')}\n"
            response += "═" * 40 + "\n\n"
            response += f"📈 Total: {len(self.projects)} | Aktif: {len(aktif)} | Selesai: {len(selesai)}\n\n"
            
            if aktif:
                response += "🔄 PROJECT AKTIF:\n"
                for p in aktif:
                    emoji = self._status_emoji(p["status"])
                    response += f"  {emoji} {p['nama']} — {p['status']}"
                    if p.get("deskripsi"):
                        response += f" ({p['deskripsi']})"
                    response += f"\n     Updated: {p['updated']}\n"
                response += "\n"
            
            if selesai:
                response += "✅ PROJECT SELESAI:\n"
                for p in selesai:
                    response += f"  ✅ {p['nama']} — selesai {p['updated']}\n"
            
            return response
        
        return "❓ Coba: update project [nama: status], progress [nama], list project, laporan project"
    
    def _status_emoji(self, status: str) -> str:
        """Map status ke emoji."""
        mapping = {
            "selesai": "✅", "done": "✅", "completed": "✅",
            "aktif": "🔄", "active": "🔄", "in progress": "🔄",
            "testing": "🧪", "test": "🧪",
            "pending": "⏸️", "stuck": "🔴", "blocked": "🔴",
            "baru": "🆕", "new": "🆕",
        }
        return mapping.get(status.lower(), "📌")