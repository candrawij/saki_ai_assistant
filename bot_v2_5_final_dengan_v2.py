import ollama
import datetime
import os
import sqlite3
import json

# ========== KONFIGURASI ==========
MODEL = "qwen3:4b"  # SESUAIKAN DENGAN MODEL ANDA
NAMA_AI = "Saki"
SAVE_FOLDER = "ringkasan"
DB_FILE = "saki_memory.db"
EXPORT_FOLDER = "exports"
RINGKASAN_RIWAYAT = 300

# Ambang batas confidence untuk auto-ekstraksi (0.0 - 1.0)
AUTO_EXTRACT_THRESHOLD = 0.7

SYSTEM_PROMPT = f"""Kamu adalah asisten AI pribadi bernama {NAMA_AI}.
Kamu membantu merangkum dokumen, menjawab pertanyaan, dan mengingat informasi penting.
Kamu menjawab dalam Bahasa Indonesia yang natural, hangat, dan langsung ke inti.
Saat merangkum, gunakan format:
## Ringkasan
[3-5 poin utama dalam bahasa Indonesia yang jelas]

## Kata Kunci
[keyword1, keyword2, keyword3]"""

# ========== DATABASE ==========
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Tabel conversations
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Tabel facts
    c.execute('''CREATE TABLE IF NOT EXISTS facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT DEFAULT 'umum',
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        deleted INTEGER DEFAULT 0
    )''')
    
    # Cek dan tambah kolom source jika belum ada
    c.execute("PRAGMA table_info(facts)")
    columns = [col[1] for col in c.fetchall()]
    
    if 'source' not in columns:
        c.execute("ALTER TABLE facts ADD COLUMN source TEXT DEFAULT 'manual'")
        print("   🔧 Database: kolom 'source' ditambahkan")
    
    if 'confidence' not in columns:
        c.execute("ALTER TABLE facts ADD COLUMN confidence REAL DEFAULT 1.0")
        print("   🔧 Database: kolom 'confidence' ditambahkan")
    
    conn.commit()
    conn.close()

# ========== FUNGSI DATABASE ==========
def simpan_chat(role, content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO conversations (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

def simpan_fakta(category, content, source="manual", confidence=1.0):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO facts (category, content, source, confidence) VALUES (?, ?, ?, ?)",
              (category, content, source, confidence))
    conn.commit()
    conn.close()

def lihat_semua_fakta(include_source=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, category, content, source, confidence, created_at FROM facts WHERE deleted = 0 ORDER BY id DESC")
    results = c.fetchall()
    conn.close()
    return results

def lihat_fakta_by_id(fact_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, category, content, source, confidence, created_at FROM facts WHERE id = ? AND deleted = 0", (fact_id,))
    result = c.fetchone()
    conn.close()
    return result

def edit_fakta(fact_id, content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE facts SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (content, fact_id))
    conn.commit()
    conn.close()

def hapus_fakta(fact_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE facts SET deleted = 1 WHERE id = ?", (fact_id,))
    conn.commit()
    conn.close()

def cari_fakta(keyword):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, category, content, source, confidence, created_at FROM facts WHERE deleted = 0 AND content LIKE ? ORDER BY id DESC", (f'%{keyword}%',))
    results = c.fetchall()
    conn.close()
    return results

def lihat_riwayat_chat(limit=20):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT role, content, timestamp FROM conversations ORDER BY id DESC LIMIT ?", (limit,))
    results = c.fetchall()
    conn.close()
    return results

def cek_fakta_duplikat(content):
    """Cek apakah konten fakta sudah ada (mirip >80%)."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, content FROM facts WHERE deleted = 0")
    semua = c.fetchall()
    conn.close()
    
    for fakta in semua:
        # Cek sederhana: apakah konten baru ada dalam konten lama atau sebaliknya
        if content.lower() in fakta[1].lower() or fakta[1].lower() in content.lower():
            return fakta[0]  # Kembalikan ID yang sudah ada
    return None

# ========== AUTO-EXTRACTION (V2) ==========
def auto_ekstrak_fakta(pesan_user, pesan_ai=None):
    """
    Menganalisis pesan user (dan respons AI) untuk mendeteksi 
    informasi penting yang layak dicatat otomatis.
    """
    # Jangan ekstrak dari perintah khusus
    if pesan_user.startswith("!") or pesan_user.lower() in ["ringkas", "keluar"]:
        return None
    
    # Jangan ekstrak dari pesan yang terlalu pendek
    if len(pesan_user.split()) < 2:
        return None
    
    # Pakai AI untuk menilai: apakah pesan ini mengandung fakta penting?
    prompt = f"""Analisis pesan berikut. Apakah mengandung informasi FAKTA PENTING tentang user yang layak dicatat?

Fakta penting meliputi:
- Proyek yang sedang dikerjakan
- Preferensi pribadi (suka/tidak suka)
- Informasi kontak
- Deadline atau jadwal penting
- Info akun atau teknis
- Pekerjaan, pendidikan, skill
- Hubungan personal (keluarga, teman, kolega)

BUKAN fakta penting:
- Pertanyaan umum ("Apa itu AI?")
- Obrolan ringan ("Halo", "Apa kabar?")
- Permintaan tolong teknis ("Jelaskan cara...")
- Opini atau diskusi abstrak

PESAN USER:
"{pesan_user}"

Jawab dalam format JSON saja:
{{
    "is_fact": true/false,
    "confidence": 0.0 sampai 1.0,
    "fact": "fakta yang diekstrak (dalam bentuk kalimat ringkas, hanya jika is_fact=true)",
    "category": "proyek/preferensi/kontak/jadwal/akun/umum"
}}"""

    try:
        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Kamu adalah sistem analisis fakta. Jawab HANYA dalam format JSON. Tidak boleh ada teks lain."},
                {"role": "user", "content": prompt}
            ]
        )
        
        hasil = response["message"]["content"].strip()
        
        # Bersihkan respons (kadang AI kasih markdown code block)
        if hasil.startswith("```"):
            hasil = hasil.split("\n", 1)[1]
            if hasil.endswith("```"):
                hasil = hasil[:-3]
        hasil = hasil.strip()
        
        # Parse JSON
        data = json.loads(hasil)
        
        if data.get("is_fact") and data.get("confidence", 0) >= AUTO_EXTRACT_THRESHOLD:
            return {
                "fact": data["fact"],
                "category": data.get("category", "umum"),
                "confidence": data["confidence"]
            }
        
        return None
    
    except json.JSONDecodeError:
        # AI tidak menghasilkan JSON valid, skip
        return None
    except Exception as e:
        print(f"\n   ⚠️ Auto-ekstraksi error: {e}")
        return None

# ========== FUNGSI AI ==========
def ringkas_teks(teks):
    prompt = f"Ringkas teks berikut:\n\n{teks}"
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )
    return response["message"]["content"]

def simpan_ringkasan(teks_asal, ringkasan):
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SAVE_FOLDER}/ringkasan_{timestamp}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"=== RINGKASAN ===\n{ringkasan}\n\n")
        f.write(f"=== TEKS ASLI ===\n{teks_asal[:500]}...\n")
        f.write(f"\nDisimpan: {datetime.datetime.now()}")
    return filename

def chat_biasa(pesan, riwayat_fakta=None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if riwayat_fakta:
        # Hanya tampilkan fakta dengan confidence >= 0.5
        fakta_text = "\n".join([f"- [{f[1]}] {f[2]}" for f in riwayat_fakta if f[4] >= 0.5])
        if fakta_text:
            messages.append({"role": "system", "content": f"Informasi yang kamu ingat tentang user:\n{fakta_text}"})
    messages.append({"role": "user", "content": pesan})
    response = ollama.chat(model=MODEL, messages=messages)
    return response["message"]["content"]

def merge_fakta_dengan_ai(fakta_list):
    fakta_text = "\n".join([f"- {f[2]}" for f in fakta_list])
    prompt = f"""Gabungkan fakta-fakta berikut menjadi satu fakta yang padat dan koheren.
Jangan ada informasi yang hilang. Hilangkan pengulangan.
Output hanya fakta gabungannya saja, tanpa penjelasan.

{fakta_text}

Hasil gabungan:"""
    
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"].strip()

# ========== EKSPOR / IMPOR ==========
def ekspor_memory():
    os.makedirs(EXPORT_FOLDER, exist_ok=True)
    fakta = lihat_semua_fakta()
    if not fakta:
        return None, None
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    json_data = []
    for f in fakta:
        json_data.append({
            "id": f[0],
            "category": f[1],
            "content": f[2],
            "source": f[3],
            "confidence": f[4],
            "created_at": f[5]
        })
    
    json_path = f"{EXPORT_FOLDER}/memory_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    md_path = f"{EXPORT_FOLDER}/memory_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {NAMA_AI} Memory Export — {datetime.datetime.now().strftime('%d %B %Y, %H:%M')}\n\n")
        categories = {}
        for item in fakta:
            cat = item[1]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        for cat, items in categories.items():
            f.write(f"## {cat.upper()}\n\n")
            for item in items:
                source_tag = "🤖" if item[3] == "auto" else "👤"
                f.write(f"- **[{source_tag} #{item[0]}]** {item[2]}\n")
                f.write(f"  📅 {item[5]} | Confidence: {item[4]:.0%}\n")
            f.write("\n")
    
    return json_path, md_path

def impor_memory(filepath):
    if not filepath.lower().endswith('.json'):
        return None, "Hanya file .json yang didukung."
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        imported = 0
        skipped = 0
        
        for item in data:
            content = item.get("content", "")
            category = item.get("category", "umum")
            source = item.get("source", "imported")
            confidence = item.get("confidence", 1.0)
            
            existing_id = cek_fakta_duplikat(content)
            
            if existing_id:
                skipped += 1
            else:
                simpan_fakta(category, content, source, confidence)
                imported += 1
        
        return imported, skipped
    
    except json.JSONDecodeError:
        return None, "File bukan JSON yang valid."
    except Exception as e:
        return None, str(e)

# ========== TAMPILAN ==========
def tampilkan_fakta(fakta_list, judul="FAKTA TERSIMPAN"):
    if not fakta_list:
        print(f"\n📭 Tidak ada {judul.lower()}.")
        return
    
    categories = {}
    for f in fakta_list:
        cat = f[1]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f)
    
    print(f"\n📚 {judul}:")
    print("=" * 60)
    
    for cat, items in categories.items():
        print(f"\n  📁 {cat.upper()} ({len(items)} fakta)")
        print("  " + "-" * 50)
        for item in items:
            source_icon = "🤖" if item[3] == "auto" else "👤"
            conf_str = f" [{item[4]:.0%}]" if item[4] < 1.0 else ""
            print(f"  {source_icon} [#{item[0]}]{conf_str} {item[2]}")
            print(f"       📅 {item[5]}")
    
    print("\n" + "=" * 60)
    
    # Statistik
    manual = sum(1 for f in fakta_list if f[3] == "manual")
    auto = sum(1 for f in fakta_list if f[3] == "auto")
    print(f"Total: {len(fakta_list)} fakta | 👤 Manual: {manual} | 🤖 Auto: {auto}")
    print(f"Kategori: {len(categories)}")
    
    # Tampilkan fakta dengan confidence rendah
    low_conf = [f for f in fakta_list if f[4] < AUTO_EXTRACT_THRESHOLD and f[4] >= 0.5]
    if low_conf:
        print(f"\n⚠️ {len(low_conf)} fakta auto dengan confidence rendah. Review dengan !edit.")

# ========== PERINTAH KHUSUS ==========
def proses_perintah_khusus(user_input):
    
    # !lihat
    if user_input.lower() == "!lihat":
        fakta = lihat_semua_fakta()
        tampilkan_fakta(fakta)
        return True
    
    # !lihatauto — lihat hanya fakta auto
    if user_input.lower() == "!lihatauto":
        fakta = lihat_semua_fakta()
        fakta_auto = [f for f in fakta if f[3] == "auto"]
        tampilkan_fakta(fakta_auto, "FAKTA AUTO (Hasil Ekstraksi Otomatis)")
        return True
    
    # !lihatmanual — lihat hanya fakta manual
    if user_input.lower() == "!lihatmanual":
        fakta = lihat_semua_fakta()
        fakta_manual = [f for f in fakta if f[3] == "manual"]
        tampilkan_fakta(fakta_manual, "FAKTA MANUAL")
        return True
    
    # !cari
    if user_input.lower().startswith("!cari"):
        keyword = user_input[5:].strip()
        if not keyword:
            print("\n⚠️ Format: !cari [kata kunci]. Contoh: !cari website")
        else:
            hasil = cari_fakta(keyword)
            tampilkan_fakta(hasil, f"Hasil pencarian: '{keyword}'")
        return True
    
    # !edit
    if user_input.lower().startswith("!edit"):
        parts = user_input.split(maxsplit=1)
        if len(parts) == 2 and parts[1].isdigit():
            fact_id = int(parts[1])
            fakta = lihat_fakta_by_id(fact_id)
            if not fakta:
                print(f"\n⚠️ Fakta #{fact_id} tidak ditemukan.")
            else:
                source_tag = "🤖 Auto" if fakta[3] == "auto" else "👤 Manual"
                print(f"\n📝 Edit Fakta #{fact_id} ({source_tag}):")
                print(f"   Kategori: {fakta[1]}")
                print(f"   Confidence: {fakta[4]:.0%}")
                print(f"   Lama: {fakta[2]}")
                baru = input("   Baru: ").strip()
                if baru:
                    edit_fakta(fact_id, baru)
                    # Jika diedit, naikkan confidence ke 1.0 dan ubah source jadi manual
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("UPDATE facts SET source = 'manual', confidence = 1.0 WHERE id = ?", (fact_id,))
                    conn.commit()
                    conn.close()
                    print(f"\n✅ Fakta #{fact_id} diupdate (sekarang 👤 Manual).")
                else:
                    print("\n⚠️ Tidak ada perubahan.")
        else:
            print("\n⚠️ Format: !edit [id]. Contoh: !edit 3")
        return True
    
    # !hapus
    if user_input.lower().startswith("!hapus"):
        parts = user_input.split()
        if len(parts) == 2 and parts[1].isdigit():
            fact_id = int(parts[1])
            fakta = lihat_fakta_by_id(fact_id)
            if not fakta:
                print(f"\n⚠️ Fakta #{fact_id} tidak ditemukan.")
            else:
                print(f"\n🗑️ Hapus Fakta #{fact_id}: {fakta[2]}")
                konfirmasi = input("   Yakin? (y/n): ").strip().lower()
                if konfirmasi == "y":
                    hapus_fakta(fact_id)
                    print(f"   ✅ Fakta #{fact_id} dihapus.")
                else:
                    print("   ❌ Batal.")
        else:
            print("\n⚠️ Format: !hapus [id]. Contoh: !hapus 3")
        return True
    
    # !merge
    if user_input.lower().startswith("!merge"):
        parts = user_input.split()
        ids = [int(p) for p in parts[1:] if p.isdigit()]
        
        if len(ids) < 2:
            print("\n⚠️ Format: !merge [id1] [id2] [id3...]. Contoh: !merge 1 3")
            return True
        
        fakta_list = []
        for fid in ids:
            f = lihat_fakta_by_id(fid)
            if f:
                fakta_list.append(f)
            else:
                print(f"\n⚠️ Fakta #{fid} tidak ditemukan. Dibatalkan.")
                return True
        
        print(f"\n🔄 Menggabungkan {len(fakta_list)} fakta:")
        for f in fakta_list:
            source_tag = "🤖" if f[3] == "auto" else "👤"
            print(f"   {source_tag} [#{f[0]}] [{f[1]}] {f[2]}")
        
        konfirmasi = input("\n   Lanjutkan? (y/n): ").strip().lower()
        if konfirmasi != "y":
            print("   ❌ Batal.")
            return True
        
        print(f"   ⏳ {NAMA_AI} sedang menggabungkan...")
        hasil_merge = merge_fakta_dengan_ai(fakta_list)
        
        print(f"\n   Hasil gabungan: {hasil_merge}")
        konfirmasi2 = input("\n   Simpan? (y/n): ").strip().lower()
        
        if konfirmasi2 == "y":
            kategori = fakta_list[0][1]
            # Hasil merge selalu manual dengan confidence 1.0
            simpan_fakta(kategori, hasil_merge, "manual", 1.0)
            for f in fakta_list:
                hapus_fakta(f[0])
            print(f"   ✅ Fakta baru tersimpan (👤 Manual). {len(fakta_list)} fakta lama dihapus.")
        else:
            print("   ❌ Batal.")
        
        return True
    
    # !ekspor
    if user_input.lower() == "!ekspor":
        print("\n⏳ Mengekspor memory...")
        json_path, md_path = ekspor_memory()
        if json_path and md_path:
            print(f"\n✅ Memory diekspor ke:")
            print(f"   📄 {json_path}  (untuk import)")
            print(f"   📄 {md_path}  (untuk dibaca)")
        else:
            print("\n⚠️ Tidak ada fakta untuk diekspor.")
        return True
    
    # !impor
    if user_input.lower() == "!impor":
        print("\n⚠️ Format yang didukung: .json (hasil ekspor)")
        filepath = input("\n📂 Masukkan path file JSON: ").strip()
        
        if not filepath:
            print("\n⚠️ Path tidak boleh kosong.")
            return True
        
        if not os.path.exists(filepath):
            print(f"\n⚠️ File '{filepath}' tidak ditemukan.")
            return True
        
        print("⏳ Mengimpor memory...")
        result = impor_memory(filepath)
        
        if result[0] is None:
            print(f"\n❌ Gagal impor: {result[1]}")
        else:
            imported, skipped = result
            print(f"\n✅ Impor selesai:")
            print(f"   📥 {imported} fakta baru diimpor")
            print(f"   ⏭️ {skipped} duplikat dilewati")
        return True
    
    # !riwayat
    if user_input.lower() == "!riwayat":
        chats = lihat_riwayat_chat(20)
        if not chats:
            print("\n📭 Belum ada riwayat chat.")
        else:
            print("\n💬 RIWAYAT CHAT TERBARU:")
            print("-" * 60)
            for c in reversed(chats):
                role_icon = "🧑" if c[0] == "USER" else "🤖"
                if RINGKASAN_RIWAYAT > 0:
                    display = c[1][:RINGKASAN_RIWAYAT]
                    if len(c[1]) > RINGKASAN_RIWAYAT:
                        display += "..."
                else:
                    display = c[1]
                print(f"  {role_icon} [{c[2]}] {display}")
            print("-" * 60)
        return True
    
    # !bantuan
    if user_input.lower() == "!bantuan":
        print(f"""
╔══════════════════════════════════════════════════════╗
║       📋 PERINTAH {NAMA_AI.upper()} v2.5+ FINAL               ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  💬 CHAT & RINGKASAN                                 ║
║  ringkas        Mode meringkas teks panjang           ║
║  Catat: [teks]  Simpan fakta manual                   ║
║  [chat biasa]   AI akan auto-ekstrak fakta penting 🤖 ║
║                                                      ║
║  📚 MEMORY MANAGEMENT                                ║
║  !lihat         Lihat semua fakta                     ║
║  !lihatauto     Lihat hanya fakta auto 🤖             ║
║  !lihatmanual   Lihat hanya fakta manual 👤           ║
║  !cari [kata]   Cari fakta dengan kata kunci          ║
║  !edit [id]     Edit fakta (auto → manual)            ║
║  !hapus [id]    Hapus fakta                           ║
║  !merge [ids]   Gabungkan fakta dengan AI             ║
║  !ekspor        Ekspor memory ke JSON & Markdown      ║
║  !impor         Impor dari file JSON                  ║
║                                                      ║
║  📋 LAINNYA                                          ║
║  !riwayat       Lihat riwayat chat terbaru            ║
║  !bantuan       Tampilkan menu ini                    ║
║  keluar         Tutup program                         ║
║                                                      ║
║  ℹ️ AUTO-EXTRACTION:                                  ║
║  Saki otomatis mendeteksi fakta dari chat biasa.      ║
║  Fakta auto ditandai 🤖 dengan confidence score.      ║
║  Edit fakta auto untuk konfirmasi (jadi 👤 Manual).   ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
        """)
        return True
    
    return False

# ========== KATEGORI OTOMATIS ==========
def tebak_kategori(teks):
    teks_lower = teks.lower()
    if any(k in teks_lower for k in ["proyek", "website", "aplikasi", "coding", "program", "developer", "tugas akhir", "skripsi"]):
        return "proyek"
    elif any(k in teks_lower for k in ["suka", "tidak suka", "preferensi", "kebiasaan", "hobi", "anime", "buku", "film", "musik"]):
        return "preferensi"
    elif any(k in teks_lower for k in ["kontak", "telepon", "email", "alamat", "whatsapp"]):
        return "kontak"
    elif any(k in teks_lower for k in ["deadline", "tanggal", "jadwal", "meeting", "janji"]):
        return "jadwal"
    elif any(k in teks_lower for k in ["password", "login", "akun", "username"]):
        return "akun"
    else:
        return "umum"

# ========== LOOP UTAMA ==========
def main():
    init_db()
    
    print("=" * 60)
    print(f"🤖 {NAMA_AI} - AI Pribadi Anda (v2.5+ Final — Auto-Extraction)")
    print("=" * 60)
    print(f"✨ Fitur baru: {NAMA_AI} bisa otomatis mendeteksi & mencatat fakta!")
    print("   Fakta auto ditandai 🤖, fakta manual ditandai 👤")
    print("=" * 60)
    print("Ketik '!bantuan' untuk melihat semua perintah")
    print("=" * 60)
    
    while True:
        user_input = input("\n🧑 Anda: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() == "keluar":
            print(f"👋 {NAMA_AI}: Sampai jumpa!")
            break
        
        # Perintah khusus
        if proses_perintah_khusus(user_input):
            simpan_chat("USER", user_input)
            continue
        
        # Mode ringkasan
        if user_input.lower() == "ringkas":
            simpan_chat("USER", "ringkas")
            print("\n📝 Mode Ringkasan (paste teks, lalu ketik 'SELESAI' di baris baru):")
            lines = []
            while True:
                line = input()
                if line.strip().upper() == "SELESAI":
                    break
                lines.append(line)
            
            teks = "\n".join(lines)
            if not teks.strip():
                print("⚠️ Tidak ada teks untuk diringkas.")
                continue
            
            print("\n⏳ Meringkas...")
            ringkasan = ringkas_teks(teks)
            print(f"\n{ringkasan}")
            
            filepath = simpan_ringkasan(teks, ringkasan)
            print(f"\n💾 Ringkasan disimpan di: {filepath}")
            simpan_chat("ARIA", ringkasan)
        
        # Catat fakta (manual)
        elif user_input.lower().startswith("catat:"):
            simpan_chat("USER", user_input)
            fakta = user_input[6:].strip()
            if fakta:
                # Cek duplikat
                existing_id = cek_fakta_duplikat(fakta)
                if existing_id:
                    print(f"\n⚠️ Fakta serupa sudah ada: #{existing_id}")
                    print("   Gunakan !edit untuk mengubahnya.")
                else:
                    kategori = tebak_kategori(fakta)
                    simpan_fakta(kategori, fakta, "manual", 1.0)
                    print(f"\n✅ Tersimpan: [#{kategori}] {fakta} 👤")
            else:
                print("\n⚠️ Format: Catat: [informasi]. Contoh: Catat: Saya sedang membuat website topup")
        
        # Chat biasa + Auto-ekstraksi
        else:
            simpan_chat("USER", user_input)
            print("\n⏳ Berpikir...")
            
            # Auto-ekstrak fakta dari pesan user
            hasil_auto = auto_ekstrak_fakta(user_input)
            
            fakta = lihat_semua_fakta()
            jawaban = chat_biasa(user_input, riwayat_fakta=fakta)
            print(f"\n🤖 {NAMA_AI}: {jawaban}")
            simpan_chat("ARIA", jawaban)
            
            # Jika auto-ekstraksi berhasil
            if hasil_auto:
                existing_id = cek_fakta_duplikat(hasil_auto["fact"])
                if not existing_id:
                    simpan_fakta(
                        hasil_auto["category"],
                        hasil_auto["fact"],
                        "auto",
                        hasil_auto["confidence"]
                    )
                    print(f"\n   🤖 Auto-catat: [{hasil_auto['category']}] {hasil_auto['fact']} ({hasil_auto['confidence']:.0%})")
                else:
                    print(f"\n   🤖 Info serupa sudah ada: #{existing_id} (skip)")

if __name__ == "__main__":
    main()