# 🤖 Saki — AI Pribadi v8.0

**Personal AI Assistant** — 100% lokal, 100% privat.

![Status](https://img.shields.io/badge/Status-Stable-green)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.58-red)
![Version](https://img.shields.io/badge/Version-8.0-purple)

---

## 🎯 Tentang Saki

Saki adalah asisten AI pribadi yang berjalan **sepenuhnya di komputer Anda**. Tidak ada data yang dikirim ke server manapun. Dibangun dengan Ollama + Streamlit.

**Dari chatbot terminal 100 baris → AI pribadi dengan 8 versi fitur.**

---

## ✨ Fitur Utama

### 💬 Chat
- Chat natural dengan AI (Qwen 3 4B)
- Auto-ekstraksi fakta dari percakapan
- Deteksi pertanyaan tugas: "Apa yang belum selesai?"

### 📝 Ringkasan & Upload
- Ringkas teks panjang
- Upload & ringkas PDF, DOCX, TXT, Markdown
- Semantic search dokumen (ChromaDB)

### 📚 Memory Management
- Catat fakta manual & otomatis
- Edit, hapus, merge fakta
- Importance scoring (1-10)
- Duplicate detection + merge suggestion

### 🧠 Intelligence
- Memory Health Dashboard
- Access tracking & importance analytics
- Peringatan fakta usang / tidak terpakai

### 🧠 Reflection Engine
- AI mengelompokkan fakta → insight
- Timeline aktivitas (bulanan/mingguan/harian)
- AI summary per bulan

### 📊 Daily Recap
- Statistik harian & mingguan
- Weekly summary dengan topik spesifik
- Kategori terbanyak minggu ini

### 🔗 Knowledge Graph
- AI ekstrak hubungan antar fakta
- Visualisasi cluster pengetahuan
- Graph-based insight

### 🔔 Proactive Assistant (V8)
- Alert otomatis: proyek mengendap, deadline mendekat
- Notifikasi insight menunggu
- Task query: "Apa tugas saya yang belum selesai?"

---

## ⚙️ Instalasi

### Prasyarat
- Python 3.10+
- [Ollama](https://ollama.com) terinstall
- Windows / Linux / Mac

### 1. Clone Repository
```bash
git clone https://github.com/USERNAME/saki-ai-assistant.git
cd saki-ai-assistant
```

### 2. Setup Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Model AI
```bash
ollama pull qwen3:4b
ollama pull nomic-embed-text
```

### 5. Konfigurasi
```bash
copy .env.example .env
# Edit .env — ganti ADMIN_PASSWORD
```

### 6. Jalankan
```bash
streamlit run saki_server.py
```
Buka http://localhost:8501 — login dengan password di .env.

📁 Struktur Project
text
E:\Priv Bot\
├── saki_server.py          # Streamlit UI
├── saki_ai.py              # Fungsi AI (chat, ekstrak, reflection)
├── saki_database.py        # SQLite + ChromaDB
├── saki_files.py           # Upload & ekstraksi file
├── .env                    # Konfigurasi (password, paths)
├── .env.example            # Template konfigurasi
├── requirements.txt        # Dependencies
├── requirements-clean.txt  # Dependencies (minimal)
│
├── data/                   # Semua data
│   ├── saki_memory.db      # Database SQLite
│   ├── chroma_db/          # Vector database
│   ├── documents/          # File upload
│   ├── exports/            # Ekspor memory
│   └── ringkasan/          # Hasil ringkasan
│
├── logs/                   # Logging
│   ├── saki.log
│   └── saki_errors.log
│
├── tests/                  # Unit tests
│   ├── test_database.py
│   ├── test_files.py
│   └── test_ai.py
│
└── Audit/                  # Laporan audit
    ├── v4.0/
    └── v8.0/

🚀 Akses Multi-Device
Mode	Link	Syarat
Lokal	http://localhost:8501	PC yang sama
WiFi/Hotspot	http://192.168.x.x:8501	Jaringan sama
Remote	http://[tailscale-ip]:8501	Tailscale aktif

🧪 Testing
bash
pip install pytest
pytest tests/ -v

📊 Riwayat Versi
Versi	Fitur
V1	Chat + Ringkasan terminal
V1.5	SQLite + Riwayat chat
V2	Auto-ekstraksi fakta
V2.5	Memory Control Center
V3	Knowledge Base + Semantic Search
V4	Web UI + Multi-device + Tailscale
V4.5	Memory Intelligence
V5	Reflection Engine
V5.5	Timeline Engine
V6	Daily Companion
V7	Personal Knowledge Graph
V8	Proactive Assistant + Task Tracking
⚠️ Catatan
100% lokal — tidak ada data keluar

Single user — didesain untuk penggunaan pribadi

Model Qwen 3 4B — bisa diganti model lain di .env

SQLite — cukup untuk ribuan fakta

Tailscale — untuk akses remote aman

📄 Lisensi
Personal project. Gunakan bebas untuk keperluan sendiri.

Dibangun dengan: Ollama · Streamlit · ChromaDB · SQLite · Python
Versi: 8.0 — Proactive Assistant
Status: Stable ✅
