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
    
    def can_handle(self, message: str) -> bool:
         msg = message.lower()
         
         # === KEYWORD SPESIFIK FILE AGENT ===
         spesifik_file = [
             "buka folder", "buka file", "buka dokumen",
             "cari file", "cariin file", "cari dokumen",
             "list folder", "isi folder", "list isi folder",
             "ringkas folder", "ringkasan folder",
             "buka",  # "buka [nama]" → coba buka folder/file
         ]
         
         # Cek spesifik dulu
         for kw in spesifik_file:
             if kw in msg:
                 # TAPI: kalau mengandung keyword agent lain, tolak!
                 if kw == "buka" or kw == "list":
                     # Pastikan bukan "list task", "list catatan", dll
                     blacklist = ["task", "tugas", "catatan", "note", "project", "proyek", "reminder", "deadline"]
                     if any(b in msg for b in blacklist):
                         continue  # Skip, biarkan agent lain yang handle
                 return True
         
         # "list" sendiri tanpa objek → anggap list folder current
         if msg.strip() == "list":
             return True
         
         return False
    
    def can_handle(self, message: str) -> bool:
        msg = message.lower()
        
        # Keyword spesifik FileAgent
        spesifik = [
            "buka folder", "buka file",
            "cari file", "cariin file",
            "list folder", "isi folder",
            "ringkas folder", "ringkasan folder",
            "buka dokumen",
        ]
        if any(kw in msg for kw in spesifik):
            return True
        
        # "list" saja TANPA kata terkait agent lain
        if msg.startswith("list ") or msg == "list":
            bukan_file = ["task", "tugas", "catatan", "note", "project", "proyek"]
            if not any(word in msg for word in bukan_file):
                return True
            
        # "buka" saja (tanpa "file" atau "folder")
        if msg.startswith("buka ") and not any(w in msg for w in ["buka file", "buka folder"]):
            # Cek apakah ini perintah buka aplikasi? Kalau bukan, anggap buka folder
            return True
        
        return False
    
    def execute(self, message: str) -> str:
        msg = message.lower()
        
        # Buka folder (perbaiki deteksi)
        if "buka folder" in msg:
            nama = message.lower().split("buka folder")[-1].strip()
            success, result = filesystem.buka_folder(nama)
            return result
        
        # "buka" saja (mungkin folder atau file)
        if msg.startswith("buka ") and "file" not in msg and "folder" not in msg:
            nama = message[5:].strip()  # setelah "buka "
            # Coba sebagai folder dulu
            resolved = filesystem.resolve_path(nama)
            if resolved and os.path.isdir(resolved):
                success, result = filesystem.buka_folder(nama)
            else:
                success, result = filesystem.buka_file(nama)
            return result

        # Buka file
        if "buka file" in msg or ("buka" in msg and "file" in msg):
            nama = message.split("buka file")[-1].strip()
            if not nama:
                nama = message.split("buka")[-1].strip()
            
            success, result = filesystem.buka_file(nama)
            return result
        
        # Cari file
        if "cari file" in msg or "cariin" in msg or msg.startswith("cari"):
            nama = message.replace("cari file", "").replace("cariin", "").replace("cari", "").strip()
            results = filesystem.cari_file(nama)
            
            if not results:
                return f"Tidak menemukan file dengan nama '{nama}'"
            
            response = f"Menemukan {len(results)} file:\n"
            for r in results[:10]:
                response += f"  • {r}\n"
            if len(results) > 10:
                response += f"  ... dan {len(results) - 10} lainnya"
            
            return response
        
        # List folder
        if "list folder" in msg or "isi folder" in msg or msg.startswith("list"):
            nama = message.replace("list folder", "").replace("isi folder", "").replace("list", "").strip()
            if not nama:
                nama = "home"
            
            success, items = filesystem.list_folder(nama)
            if not success:
                return f"Folder '{nama}' tidak ditemukan"
            
            if not items:
                return f"Folder '{nama}' kosong"
            
            response = f"Isi folder:\n"
            for item in items[:15]:
                icon = "📁" if item["tipe"] == "folder" else "📄"
                response += f"  {icon} {item['nama']}"
                if item["tipe"] == "file":
                    response += f" ({item['ukuran_mb']} MB)"
                response += "\n"
            
            if len(items) > 15:
                response += f"  ... dan {len(items) - 15} item lainnya"
            
            return response
        
        # Ringkas folder
        if "ringkas folder" in msg or "ringkasan folder" in msg:
            nama = message.replace("ringkas folder", "").replace("ringkasan folder", "").replace("ringkas", "").strip()
            if not nama:
                nama = "home"
            
            success, result = filesystem.ringkas_folder(nama)
            return result
        
        return "Maaf, saya tidak mengerti perintah file itu. Coba: buka folder [nama], cari file [nama], list folder [nama], ringkas folder [nama]"