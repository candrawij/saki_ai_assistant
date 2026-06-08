"""
NoteAgent — Catat, cari, list, hapus note
"""

import os
import json
from datetime import datetime
from pathlib import Path
from .base import BaseAgent

class NoteAgent(BaseAgent):
    def __init__(self, data_folder: str = "data/notes"):
        super().__init__(
            name="Note Agent",
            description="Catat, cari, dan kelola catatan"
        )
        self.data_folder = Path(data_folder)
        self.data_folder.mkdir(parents=True, exist_ok=True)
        self.notes_file = self.data_folder / "notes.json"
        self._load_notes()
        self.keywords = [
            "catat:", "note:", "catatan:",
            "cari catatan", "cari note",
            "list catatan", "list note", "daftar catatan",
            "hapus catatan", "hapus note",
            "tampilkan catatan",
        ]
    
    def _load_notes(self):
        """Load notes dari file JSON."""
        if self.notes_file.exists():
            with open(self.notes_file, "r", encoding="utf-8") as f:
                self.notes = json.load(f)
        else:
            self.notes = []
    
    def _save_notes(self):
        """Simpan notes ke file JSON."""
        with open(self.notes_file, "w", encoding="utf-8") as f:
            json.dump(self.notes, f, ensure_ascii=False, indent=2)
    
    def can_handle(self, message: str) -> bool:
        msg = message.lower()
        return any(kw in msg for kw in self.keywords)
    
    def execute(self, message: str) -> str:
        msg = message.lower()
        
        # Catat note baru
        if any(kw in msg for kw in ["catat:", "note:", "catatan:"]):
            # Ekstrak isi setelah "catat:" atau "note:"
            for prefix in ["catat:", "note:", "catatan:"]:
                if prefix in msg:
                    idx = message.lower().find(prefix)
                    isi = message[idx + len(prefix):].strip()
                    break
            else:
                isi = message.strip()
            
            if not isi:
                return "Apa yang ingin dicatat? Contoh: 'catat: ide untuk fitur baru'"
            
            note = {
                "id": len(self.notes) + 1,
                "isi": isi,
                "tanggal": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "kategori": "umum",
            }
            self.notes.append(note)
            self._save_notes()
            
            return f"✅ Note #{note['id']} tersimpan: \"{isi[:100]}{'...' if len(isi) > 100 else ''}\""
        
        # Cari catatan
        if "cari catatan" in msg or "cari note" in msg:
            query = message.replace("cari catatan", "").replace("cari note", "").strip()
            if not query:
                return "Cari catatan apa? Contoh: 'cari catatan meeting'"
            
            results = []
            for note in self.notes:
                if query.lower() in note["isi"].lower():
                    results.append(note)
            
            if not results:
                return f"Tidak ada catatan yang mengandung '{query}'"
            
            response = f"Menemukan {len(results)} catatan:\n"
            for r in results:
                response += f"  #{r['id']} [{r['tanggal']}] {r['isi'][:100]}\n"
            
            return response
        
        # List/tampilkan catatan
        if any(kw in msg for kw in ["list catatan", "list note", "daftar catatan", "tampilkan catatan"]):
            if not self.notes:
                return "Belum ada catatan. Mulai dengan: 'catat: ...'"
            
            # Filter minggu ini kalau diminta
            if "minggu ini" in msg:
                now = datetime.now()
                week_ago = now.replace(day=now.day-7)
                filtered = [
                    n for n in self.notes
                    if datetime.strptime(n["tanggal"], "%Y-%m-%d %H:%M") >= week_ago
                ]
                if not filtered:
                    return "Tidak ada catatan minggu ini"
                
                response = f"Catatan minggu ini ({len(filtered)}):\n"
                for n in filtered:
                    response += f"  #{n['id']} [{n['tanggal']}] {n['isi'][:80]}\n"
                return response
            
            # Tampilkan semua (maks 10 terbaru)
            recent = sorted(self.notes, key=lambda x: x["tanggal"], reverse=True)[:10]
            response = f"Catatan terbaru ({len(self.notes)} total):\n"
            for n in recent:
                response += f"  #{n['id']} [{n['tanggal']}] {n['isi'][:80]}\n"
            
            return response
        
        # Hapus catatan
        if "hapus catatan" in msg or "hapus note" in msg:
            # Coba ekstrak ID
            import re
            numbers = re.findall(r'\d+', message)
            if numbers:
                note_id = int(numbers[0])
                for i, note in enumerate(self.notes):
                    if note["id"] == note_id:
                        deleted = self.notes.pop(i)
                        self._save_notes()
                        return f"✅ Catatan #{note_id} dihapus: \"{deleted['isi'][:80]}\""
                return f"Catatan #{note_id} tidak ditemukan"
            
            return "Hapus catatan yang mana? Sebutkan ID-nya. Contoh: 'hapus catatan #3'"
        
        return "Maaf, saya tidak mengerti perintah note itu. Coba: catat: [isi], cari catatan [kata], list catatan, hapus catatan #[id]"