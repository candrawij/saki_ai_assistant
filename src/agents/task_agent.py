"""
TaskAgent — Kelola tugas, deadline, reminder
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from .base import BaseAgent
from .skills.windows import notifikasi_windows

class TaskAgent(BaseAgent):
    def __init__(self, data_folder: str = "data/tasks"):
        super().__init__(
            name="Task Agent",
            description="Kelola tugas, deadline, dan pengingat"
        )
        self.data_folder = Path(data_folder)
        self.data_folder.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.data_folder / "tasks.json"
        self._load_tasks()
    
    def _load_tasks(self):
        if self.tasks_file.exists():
            with open(self.tasks_file, "r", encoding="utf-8") as f:
                self.tasks = json.load(f)
        else:
            self.tasks = []
    
    def _save_tasks(self):
        self.data_folder.mkdir(parents=True, exist_ok=True)
        with open(self.tasks_file, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)
    
    def _get_next_id(self) -> int:
        """Generate ID baru (fix bug deletion)."""
        if not self.tasks:
            return 1
        return max(t["id"] for t in self.tasks) + 1
    
    def can_handle(self, message: str) -> bool:
        msg = message.lower()
        return any(k in msg for k in [
            "tambah task", "task:", "tugas:", "list task",
            "daftar tugas", "apa tugas", "tandai task",
            "task selesai", "selesaikan task", "deadline",
            "tenggat", "ingatkan", "reminder",
            "hapus task", "delete task",  # ✅ TAMBAHAN
        ])
    
    def _parse_deadline(self, text: str) -> str:
        """Parse deadline dari text."""
        hari_map = {
            "senin": 0, "selasa": 1, "rabu": 2, "kamis": 3,
            "jumat": 4, "sabtu": 5, "minggu": 6,
            "besok": 1, "lusa": 2,
        }
        today = datetime.now()
        
        for kata, offset in hari_map.items():
            if kata in text.lower():
                if kata in ["besok", "lusa"]:
                    target = today + timedelta(days=offset)
                else:
                    days_ahead = (offset - today.weekday()) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    target = today + timedelta(days=days_ahead)
                return target.strftime("%Y-%m-%d")
        
        # Cek format tanggal (2024-12-31)
        match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
        if match:
            return match.group(1)
        
        # Default: 3 hari dari sekarang
        return (today + timedelta(days=3)).strftime("%Y-%m-%d")
    
    def _format_deadline_display(self, deadline_str: str) -> str:
        """Format deadline untuk display."""
        try:
            dl = datetime.strptime(deadline_str, "%Y-%m-%d")
            today = datetime.now()
            
            if dl.date() < today.date():
                return f"🔴 TERLAMBAT {deadline_str}"
            elif dl.date() == today.date():
                return f"🟡 HARI INI {deadline_str}"
            elif dl.date() == (today + timedelta(days=1)).date():
                return f"🟡 BESOK {deadline_str}"
            else:
                days_left = (dl - today).days
                return f"🟢 {deadline_str} ({days_left} hari lagi)"
        except:
            return deadline_str
    
    def execute(self, message: str) -> str:
        msg = message.lower()
        
        # === TAMBAH TASK ===
        if any(k in msg for k in ["tambah task", "task:", "tugas:"]):
            isi = message
            for prefix in ["tambah task:", "tambah task", "task:", "tugas:"]:
                pos = isi.lower().find(prefix)
                if pos >= 0:
                    isi = isi[pos + len(prefix):].strip()
                    break
            isi = isi.lstrip(":").strip()
            
            if not isi:
                return "❓ Task apa? Contoh: 'tambah task: revisi proposal, deadline Jumat'"
            
            # ✅ TAMBAHAN: Extract priority
            priority = "normal"
            if any(k in isi.lower() for k in ["penting", "urgent", "prioritas tinggi", "!!"]):
                priority = "high"
            elif any(k in isi.lower() for k in ["rendah", "low", "santai"]):
                priority = "low"
            
            deadline = self._parse_deadline(isi)
            
            task = {
                "id": self._get_next_id(),
                "isi": isi,
                "deadline": deadline,
                "status": "aktif",
                "priority": priority,  # ✅ TAMBAHAN
                "dibuat": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            self.tasks.append(task)
            self._save_tasks()
            
            priority_icon = {"high": "🔴", "normal": "🟡", "low": "🟢"}.get(priority, "")
            return f"✅ Task #{task['id']} ditambahkan {priority_icon}: \"{isi[:80]}\" — Deadline: {deadline}"
        
        # === LIST TASK ===
        if any(k in msg for k in ["list task", "daftar tugas", "apa tugas"]):
            aktif = [t for t in self.tasks if t.get("status") == "aktif"]
            
            # ✅ TAMBAHAN: Filter by status if requested
            if "selesai" in msg or "completed" in msg:
                aktif = [t for t in self.tasks if t.get("status") == "selesai"]
            elif "semua" in msg or "all" in msg:
                aktif = self.tasks[:]
            
            if not aktif:
                return "✅ Tidak ada tugas aktif." if "selesai" not in msg else "Tidak ada tugas selesai."
            
            # Sort by deadline
            aktif.sort(key=lambda x: x.get("deadline", "9999-12-31"))
            
            status_label = "selesai" if "selesai" in msg else "aktif"
            resp = f"📋 Tugas {status_label} ({len(aktif)}):\n"
            
            for t in aktif:
                dl = t.get("deadline", "tanpa deadline")
                dl_display = self._format_deadline_display(dl) if t.get("status") == "aktif" else dl
                priority_icon = {"high": "🔴", "normal": "🟡", "low": "🟢"}.get(t.get("priority", "normal"), "")
                
                status_icon = "✅" if t.get("status") == "selesai" else "⏳"
                resp += f"  {status_icon} #{t['id']} {priority_icon} {t['isi'][:80]} — {dl_display}\n"
            
            return resp
        
        # === TANDAI SELESAI ===
        if any(k in msg for k in ["tandai task", "task selesai", "selesaikan task"]):
            # ✅ IMPROVED: Cek #id dulu, baru angka
            match = re.search(r'#(\d+)', message)
            if match:
                tid = int(match.group(1))
            else:
                nums = re.findall(r'\d+', message)
                tid = int(nums[0]) if nums else None
            
            if tid:
                for t in self.tasks:
                    if t["id"] == tid:
                        if t.get("status") == "selesai":
                            return f"ℹ️ Task #{tid} sudah selesai sebelumnya"
                        t["status"] = "selesai"
                        t["selesai"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        self._save_tasks()
                        return f"✅ Task #{tid} selesai: \"{t['isi'][:80]}\" 🎉"
                return f"❌ Task #{tid} tidak ditemukan"
            return "❓ Sebutkan ID. Contoh: 'tandai task #3 selesai'"
        
        # === DEADLINE ===
        if "deadline" in msg or "tenggat" in msg:
            aktif = [t for t in self.tasks if t.get("status") == "aktif" and t.get("deadline")]
            today = datetime.now()
            week_end = today + timedelta(days=7)
            
            deadline_ini = []
            for t in aktif:
                try:
                    if datetime.strptime(t["deadline"], "%Y-%m-%d") <= week_end:
                        deadline_ini.append(t)
                except:
                    pass
            
            if not deadline_ini:
                return "✅ Tidak ada deadline 7 hari ke depan."
            
            deadline_ini.sort(key=lambda x: x["deadline"])
            
            resp = "⏰ Deadline 7 hari ke depan:\n"
            for t in deadline_ini:
                dl_display = self._format_deadline_display(t["deadline"])
                resp += f"  #{t['id']} {t['isi'][:80]} — {dl_display}\n"
            return resp
        
        # === HAPUS TASK === (✅ TAMBAHAN)
        if "hapus task" in msg or "delete task" in msg:
            match = re.search(r'#(\d+)', message)
            if match:
                tid = int(match.group(1))
            else:
                nums = re.findall(r'\d+', message)
                tid = int(nums[0]) if nums else None
            
            if tid:
                for i, t in enumerate(self.tasks):
                    if t["id"] == tid:
                        deleted = self.tasks.pop(i)
                        self._save_tasks()
                        return f"🗑️ Task #{tid} dihapus: \"{deleted['isi'][:80]}\""
                return f"❌ Task #{tid} tidak ditemukan"
            return "❓ Task mana? Contoh: 'hapus task #3'"
        
        # === REMINDER ===
        if "ingatkan" in msg or "reminder" in msg:
            match = re.search(r'(\d+)\s*(menit|jam|detik)', msg)
            if match:
                jumlah, satuan = int(match.group(1)), match.group(2)
                pesan = message.replace("ingatkan", "").replace("reminder", "").strip()
                # Hapus angka dan satuan dari pesan
                pesan = re.sub(r'\d+\s*(menit|jam|detik)\s*(lagi)?', '', pesan).strip()
                notifikasi_windows("Saki Reminder", f"Dalam {jumlah} {satuan}: {pesan[:100]}")
                return f"✅ Mengingatkan dalam {jumlah} {satuan}: \"{pesan[:80]}\""
            return "❓ Kapan? Contoh: 'ingatkan 30 menit lagi untuk meeting'"
        
        return "❓ Coba: tambah task [isi], list task, tandai task #[id] selesai, deadline, hapus task #[id], ingatkan [waktu]"