"""
NoteAgent — Catat, cari, list, hapus note
"""

import os
import re
import json
from datetime import datetime, timedelta
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
        
        # Keywords untuk routing
        self.keywords = [
            "catat:", "note:", "catatan:",
            "cari catatan", "cari note",
            "list catatan", "list note", "daftar catatan",
            "hapus catatan", "hapus note",
            "tampilkan catatan", "buat catatan", "tulis catatan",
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
    
    def _get_next_id(self) -> int:
        """Generate ID baru."""
        if not self.notes:
            return 1
        return max(n["id"] for n in self.notes) + 1
    
    def _extract_tags(self, text: str) -> list:
        """Extract hashtags dari text."""
        return re.findall(r'#(\w+)', text)
    
    def can_handle(self, message: str) -> bool:
        msg = message.lower()
        return any(kw in msg for kw in self.keywords)
    
    def execute(self, message: str) -> str:
        msg = message.lower()
        
        # === CATAT NOTE BARU ===
        if any(kw in msg for kw in ["catat:", "note:", "catatan:"]):
            # Ekstrak isi setelah prefix
            for prefix in ["catat:", "note:", "catatan:"]:
                if prefix in msg:
                    idx = message.lower().find(prefix)
                    isi = message[idx + len(prefix):].strip()
                    break
            else:
                isi = message.strip()
            
            # Bisa juga "catat ..." tanpa colon
            if not isi and msg.startswith("catat "):
                isi = message[6:].strip()
            
            if not isi:
                return "❓ Apa yang ingin dicatat? Contoh: 'catat: ide untuk fitur baru'"
            
            # Extract title (first sentence or first 80 chars)
            title = isi.split(".")[0][:80] if "." in isi else isi[:80]
            tags = self._extract_tags(isi)
            
            note = {
                "id": self._get_next_id(),
                "title": title,
                "isi": isi,
                "tanggal": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "kategori": tags[0] if tags else "umum",
                "tags": tags,
            }
            self.notes.append(note)
            self._save_notes()
            
            # ✅ TAMBAHAN: Simpan juga sebagai Markdown
            self._save_markdown(note)
            
            return f"✅ Note #{note['id']} tersimpan: \"{title}{'...' if len(isi) > 80 else ''}\""
        
        # === CARI CATATAN ===
        if "cari catatan" in msg or "cari note" in msg:
            query = msg.replace("cari catatan", "").replace("cari note", "").strip()
            if not query:
                return "❓ Cari catatan apa? Contoh: 'cari catatan meeting'"
            
            results = [n for n in self.notes if query.lower() in n["isi"].lower()]
            
            if not results:
                return f"🔍 Tidak ada catatan yang mengandung '{query}'"
            
            response = f"🔍 Menemukan {len(results)} catatan:\n"
            for r in results[:10]:
                response += f"  📝 #{r['id']} [{r['tanggal']}] {r['isi'][:100]}\n"
            
            if len(results) > 10:
                response += f"  ... dan {len(results) - 10} lainnya"
            return response
        
        # === LIST CATATAN ===
        if any(kw in msg for kw in ["list catatan", "list note", "daftar catatan", "tampilkan catatan"]):
            if not self.notes:
                return "📝 Belum ada catatan. Mulai dengan: 'catat: ...'"
            
            # Filter minggu ini
            if "minggu ini" in msg:
                now = datetime.now()
                week_ago = now - timedelta(days=7)
                filtered = [
                    n for n in self.notes
                    if datetime.strptime(n["tanggal"], "%Y-%m-%d %H:%M") >= week_ago
                ]
                if not filtered:
                    return "Tidak ada catatan minggu ini"
                
                response = f"📝 Catatan minggu ini ({len(filtered)}):\n"
                for n in sorted(filtered, key=lambda x: x["tanggal"], reverse=True):
                    response += f"  #{n['id']} [{n['tanggal']}] {n['isi'][:80]}\n"
                return response
            
            # Filter hari ini
            if "hari ini" in msg:
                today = datetime.now().strftime("%Y-%m-%d")
                filtered = [n for n in self.notes if n["tanggal"].startswith(today)]
                if not filtered:
                    return "Tidak ada catatan hari ini"
                
                response = f"📝 Catatan hari ini ({len(filtered)}):\n"
                for n in filtered:
                    response += f"  #{n['id']} [{n['tanggal']}] {n['isi'][:80]}\n"
                return response
            
            # Tampilkan terbaru (maks 10)
            recent = sorted(self.notes, key=lambda x: x["tanggal"], reverse=True)[:10]
            response = f"📝 Catatan terbaru ({len(self.notes)} total):\n"
            for n in recent:
                tags_str = f" [{', '.join(n.get('tags', []))}]" if n.get('tags') else ""
                response += f"  #{n['id']} [{n['tanggal']}]{tags_str} {n['isi'][:80]}\n"
            
            if len(self.notes) > 10:
                response += f"\n  ... dan {len(self.notes) - 10} catatan lainnya"
            return response
        
        # === HAPUS CATATAN ===
        if "hapus catatan" in msg or "hapus note" in msg:
            # Coba ekstrak ID dengan #
            match = re.search(r'#(\d+)', message)
            if match:
                note_id = int(match.group(1))
            else:
                # Coba cari angka pertama
                numbers = re.findall(r'\d+', message)
                note_id = int(numbers[0]) if numbers else None
            
            if note_id:
                for i, note in enumerate(self.notes):
                    if note["id"] == note_id:
                        deleted = self.notes.pop(i)
                        self._save_notes()
                        # Hapus file Markdown juga
                        self._delete_markdown(note_id)
                        return f"🗑️ Catatan #{note_id} dihapus: \"{deleted['isi'][:80]}\""
                return f"❌ Catatan #{note_id} tidak ditemukan"
            
            return "❓ Hapus catatan yang mana? Sebutkan ID-nya. Contoh: 'hapus catatan #3'"
        
        return "❓ Coba: catat: [isi], cari catatan [kata], list catatan, hapus catatan #[id]"
    
    # === TAMBAHAN DARI KODE BARU ===
    def _save_markdown(self, note: dict):
        """Simpan note sebagai file Markdown."""
        md_folder = self.data_folder / "markdown"
        md_folder.mkdir(parents=True, exist_ok=True)
        
        filename = f"note_{note['id']}_{note['tanggal'][:10].replace('-', '')}.md"
        filepath = md_folder / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Note #{note['id']}: {note.get('title', 'Tanpa Judul')}\n\n")
            f.write(f"**Tanggal:** {note['tanggal']}\n")
            f.write(f"**Kategori:** {note.get('kategori', 'umum')}\n")
            if note.get('tags'):
                f.write(f"**Tags:** {', '.join(note['tags'])}\n")
            f.write(f"\n---\n\n")
            f.write(note['isi'])
    
    def _delete_markdown(self, note_id: int):
        """Hapus file Markdown terkait."""
        md_folder = self.data_folder / "markdown"
        if md_folder.exists():
            for f in md_folder.glob(f"note_{note_id}_*.md"):
                f.unlink()