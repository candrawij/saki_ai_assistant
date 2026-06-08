"""
FileAgent — Buka, cari, ringkas file/folder
"""

import os
from .base import BaseAgent
from .skills.filesystem import FileSystemSkills

class FileAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="File Agent",
            description="Buka, cari, dan ringkas file/folder"
        )
        self.fs = FileSystemSkills()
    
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
            nama = message.lower().split("buka folder")[-1].strip()
            return self._buka(nama, is_folder=True)
        
        # === BUKA FILE ===
        if "buka file" in msg or "buka dokumen" in msg:
            nama = msg.split("buka file")[-1].split("buka dokumen")[-1].strip()
            return self._buka(nama, is_folder=False)
        
        # === BUKA (implisit) ===
        if msg.startswith("buka ") and "file" not in msg and "folder" not in msg:
            nama = message[5:].strip()
            return self._buka_auto(nama)
        
        # === CARI FILE ===
        if "cari file" in msg or "cariin" in msg or (msg.startswith("cari") and "catatan" not in msg):
            nama = msg.replace("cari file", "").replace("cariin", "").replace("cari", "").strip()
            return self._cari(nama)
        
        # === LIST FOLDER ===
        if "list folder" in msg or "isi folder" in msg or msg.startswith("list"):
            nama = msg.replace("list folder", "").replace("isi folder", "").replace("list", "").strip()
            return self._list(nama)
        
        # === RINGKAS FOLDER ===
        if "ringkas folder" in msg or "ringkasan folder" in msg:
            nama = msg.replace("ringkas folder", "").replace("ringkasan folder", "").replace("ringkas", "").strip()
            return self._ringkas(nama)
        
        return "❓ Coba: buka folder [nama], cari file [nama], list folder [nama], ringkas folder [nama]"
    
    def _buka(self, nama: str, is_folder: bool = True) -> str:
        """Buka folder atau file"""
        if not nama:
            nama = "home"
        
        if is_folder:
            success = self.fs.open_folder(nama)
        else:
            success = self.fs.open_file(nama)
        
        return f"✅ Membuka: {nama}" if success else f"❌ Tidak bisa membuka '{nama}'"
    
    def _buka_auto(self, nama: str) -> str:
        """Auto-detect folder atau file"""
        resolved = self.fs.resolve_path(nama)
        if resolved and os.path.isdir(resolved):
            return self._buka(nama, is_folder=True)
        else:
            return self._buka(nama, is_folder=False)
    
    def _cari(self, nama: str) -> str:
        """Cari file"""
        if not nama:
            return "❓ Cari file apa? Contoh: 'cari file laporan'"
        
        results = self.fs.search_files(nama)
        
        if not results:
            return f"🔍 Tidak menemukan file dengan nama '{nama}'"
        
        response = f"🔍 Menemukan {len(results)} file:\n"
        for r in results[:10]:
            response += f"  • 📄 {r['name']} ({r['size']/1024:.0f} KB)\n"
        if len(results) > 10:
            response += f"  ... dan {len(results) - 10} lainnya"
        return response
    
    def _list(self, nama: str) -> str:
        """List isi folder"""
        if not nama:
            nama = "home"
        
        result = self.fs.list_folder(nama)
        
        if "error" in result:
            return f"❌ {result['error']}"
        
        items = result.get("items", [])
        if not items:
            return f"📂 Folder '{nama}' kosong"
        
        response = f"📂 Isi folder ({len(items)} item):\n"
        for item in items[:15]:
            icon = "📁" if item["type"] == "folder" else "📄"
            response += f"  {icon} {item['name']}"
            if item["type"] == "file":
                response += f" ({item['size']/1024**2:.1f} MB)"
            response += "\n"
        
        if len(items) > 15:
            response += f"  ... dan {len(items) - 15} item lainnya"
        return response
    
    def _ringkas(self, nama: str) -> str:
        """Ringkas folder"""
        if not nama:
            nama = "home"
        
        result = self.fs.summarize_folder(nama)
        
        if "error" in result:
            return f"❌ {result['error']}"
        
        return (
            f"📁 Ringkasan: {result['path']}\n"
            f"  📏 Size: {result['total_size']}\n"
            f"  📄 File: {result['file_count']}\n"
            f"  📂 Folder: {result['folder_count']}"
        )