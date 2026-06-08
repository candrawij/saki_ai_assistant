"""
FileAgent — Buka, cari, ringkas file/folder
"""

import os
from .base import BaseAgent
from .skills import filesystem


class FileAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="File Agent",
            description="Buka, cari, dan ringkas file/folder"
        )
        # Tidak perlu self.fs — pakai module functions langsung
    
    def can_handle(self, message: str) -> bool:
        msg = message.lower()
        
        # Keyword spesifik FileAgent
        spesifik = [
            "buka folder", "buka file", "buka dokumen",
            "cari file", "cariin file", "cari dokumen",
            "list folder", "isi folder", "list isi folder",
            "ringkas folder", "ringkasan folder",
        ]
        
        for kw in spesifik:
            if kw in msg:
                # Guard: pastikan bukan keyword agent lain
                if kw in ["buka", "list"]:
                    blacklist = ["task", "tugas", "catatan", "note", "project", "proyek", "reminder", "deadline"]
                    if any(b in msg for b in blacklist):
                        continue
                return True
        
        # "list" sendiri tanpa objek → list folder current
        if msg.strip() == "list":
            return True
        
        # "list ..." tapi bukan punya agent lain
        if msg.startswith("list "):
            blacklist = ["task", "tugas", "catatan", "note", "project", "proyek"]
            if not any(b in msg for b in blacklist):
                return True
        
        # "buka ..." (implisit)
        if msg.startswith("buka ") and "file" not in msg and "folder" not in msg:
            blacklist = ["task", "tugas", "catatan", "note", "project", "proyek", "aplikasi"]
            if not any(b in msg for b in blacklist):
                return True
        
        return False
    
    def execute(self, message: str) -> str:
        msg = message.lower()
        
        # === BUKA FOLDER ===
        if "buka folder" in msg:
            nama = msg.split("buka folder")[-1].strip()
            success, result = filesystem.buka_folder(nama) if nama else (False, "Folder apa?")
            return result
        
        # === BUKA FILE ===
        if "buka file" in msg or "buka dokumen" in msg:
            nama = msg.split("buka file")[-1].split("buka dokumen")[-1].strip()
            success, result = filesystem.buka_file(nama) if nama else (False, "File apa?")
            return result
        
        # === BUKA (implisit) ===
        if msg.startswith("buka ") and "file" not in msg and "folder" not in msg:
            nama = message[5:].strip()
            if not nama:
                return "❓ Buka apa? Contoh: 'buka data' atau 'buka folder data'"
            
            # Auto-detect: folder atau file
            resolved = filesystem.resolve_path(nama)
            if resolved and os.path.isdir(resolved):
                success, result = filesystem.buka_folder(nama)
            else:
                success, result = filesystem.buka_file(nama)
            return result
        
        # === CARI FILE ===
        if "cari file" in msg or "cariin" in msg or (msg.startswith("cari") and "catatan" not in msg):
            nama = msg.replace("cari file", "").replace("cariin", "").replace("cari", "").strip()
            if not nama:
                return "❓ Cari file apa? Contoh: 'cari file laporan'"
            
            results = filesystem.cari_file(nama)
            
            if not results:
                return f"🔍 Tidak menemukan file dengan nama '{nama}'"
            
            response = f"🔍 Menemukan {len(results)} file:\n"
            for r in results[:10]:
                # results isinya list of path strings
                file_name = os.path.basename(r)
                response += f"  • 📄 {file_name}\n"
            if len(results) > 10:
                response += f"  ... dan {len(results) - 10} lainnya"
            return response
        
        # === LIST FOLDER ===
        if "list folder" in msg or "isi folder" in msg or msg.startswith("list"):
            nama = msg.replace("list folder", "").replace("isi folder", "").replace("list", "").strip()
            if not nama:
                nama = "data"
            
            success, items = filesystem.list_folder(nama)
            if not success:
                return f"❌ Folder '{nama}' tidak ditemukan"
            
            if not items:
                return f"📂 Folder '{nama}' kosong"
            
            response = f"📂 Isi folder ({len(items)} item):\n"
            for item in items[:15]:
                icon = "📁" if item["tipe"] == "folder" else "📄"
                response += f"  {icon} {item['nama']}"
                if item["tipe"] == "file" and item.get("ukuran_mb", 0) > 0:
                    response += f" ({item['ukuran_mb']:.1f} MB)"
                response += "\n"
            
            if len(items) > 15:
                response += f"  ... dan {len(items) - 15} item lainnya"
            return response
        
        # === RINGKAS FOLDER ===
        if "ringkas folder" in msg or "ringkasan folder" in msg:
            nama = msg.replace("ringkas folder", "").replace("ringkasan folder", "").replace("ringkas", "").strip()
            if not nama:
                nama = "data"
            
            success, result = filesystem.ringkas_folder(nama)
            return result
        
        return "❓ Coba: buka folder [nama], cari file [nama], list folder [nama], ringkas folder [nama]"