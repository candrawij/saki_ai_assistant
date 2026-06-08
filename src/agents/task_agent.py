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
    
    def can_handle(self, message: str) -> bool:
        msg = message.lower()
        return any(k in msg for k in ["tambah task", "task:", "tugas:", "list task",
                                         "daftar tugas", "apa tugas", "tandai task",
                                         "task selesai", "selesaikan task", "deadline",
                                         "tenggat", "ingatkan", "reminder"])
    
    def _parse_deadline(self, text: str) -> str:
        hari_map = {"senin": 0, "selasa": 1, "rabu": 2, "kamis": 3,
                    "jumat": 4, "sabtu": 5, "minggu": 6, "besok": 1, "lusa": 2}
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
        match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
        if match:
            return match.group(1)
        return (today + timedelta(days=3)).strftime("%Y-%m-%d")
    
    def execute(self, message: str) -> str:
        msg = message.lower()
        
        # === TAMBAH TASK ===
        if any(k in msg for k in ["tambah task", "task:", "tugas:"]):
            isi = message
            for prefix in ["tambah task:", "tambah task", "task:", "tugas:"]:
                pos = isi.lower().find(prefix)
                if pos >= 0:
                    isi = isi[pos + len(prefix):]
                    break
            isi = isi.strip().lstrip(":").strip()
            if not isi:
                return "Task apa? Contoh: 'tambah task: revisi proposal, deadline Jumat'"
            deadline = self._parse_deadline(isi)
            task = {"id": len(self.tasks) + 1, "isi": isi, "deadline": deadline,
                    "status": "aktif", "dibuat": datetime.now().strftime("%Y-%m-%d %H:%M")}
            self.tasks.append(task)
            self._save_tasks()
            return f"✅ Task #{task['id']} ditambahkan: \"{isi[:80]}\" — Deadline: {deadline}"
        
        # === LIST TASK ===
        if any(k in msg for k in ["list task", "daftar tugas", "apa tugas"]):
            aktif = [t for t in self.tasks if t.get("status") == "aktif"]
            if not aktif:
                return "Tidak ada tugas aktif."
            aktif.sort(key=lambda x: x.get("deadline", "9999-12-31"))
            resp = f"Tugas aktif ({len(aktif)}):\n"
            for t in aktif:
                dl = t.get("deadline", "tanpa deadline")
                try:
                    d = datetime.strptime(dl, "%Y-%m-%d")
                    if d < datetime.now(): dl = f"TERLAMBAT {dl}"
                    elif d < datetime.now() + timedelta(days=1): dl = f"BESOK {dl}"
                except: pass
                resp += f"  #{t['id']} {t['isi'][:80]} — {dl}\n"
            return resp
        
        # === TANDAI SELESAI ===
        if any(k in msg for k in ["tandai task", "task selesai", "selesaikan task"]):
            nums = re.findall(r'\d+', message)
            if nums:
                tid = int(nums[0])
                for t in self.tasks:
                    if t["id"] == tid:
                        t["status"] = "selesai"
                        t["selesai"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        self._save_tasks()
                        return f"✅ Task #{tid} selesai: \"{t['isi'][:80]}\""
                return f"Task #{tid} tidak ditemukan"
            return "Sebutkan ID. Contoh: 'tandai task #3 selesai'"
        
        # === DEADLINE ===
        if "deadline" in msg or "tenggat" in msg:
            aktif = [t for t in self.tasks if t.get("status") == "aktif"]
            today = datetime.now()
            week_end = today + timedelta(days=7)
            deadline_ini = []
            for t in aktif:
                try:
                    if datetime.strptime(t["deadline"], "%Y-%m-%d") <= week_end:
                        deadline_ini.append(t)
                except: pass
            if not deadline_ini:
                return "Tidak ada deadline 7 hari ke depan."
            resp = "Deadline 7 hari ke depan:\n"
            for t in deadline_ini:
                resp += f"  #{t['id']} {t['isi'][:80]} — {t['deadline']}\n"
            return resp
        
        # === REMINDER ===
        if "ingatkan" in msg or "reminder" in msg:
            match = re.search(r'(\d+)\s*(menit|jam|detik)', msg)
            if match:
                jumlah, satuan = int(match.group(1)), match.group(2)
                pesan = message.replace("ingatkan", "").replace("reminder", "").strip()
                notifikasi_windows("Saki Reminder", f"Dalam {jumlah} {satuan}: {pesan[:100]}")
                return f"✅ Mengingatkan dalam {jumlah} {satuan}: \"{pesan[:80]}\""
            return "Kapan? Contoh: 'ingatkan 30 menit lagi untuk meeting'"
        
        return "Coba: tambah task [isi], list task, tandai task #[id] selesai, deadline"