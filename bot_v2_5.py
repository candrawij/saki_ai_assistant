import ollama
import datetime
import os
import sqlite3
import json

# ========== KONFIGURASI ==========
MODEL = "qwen3:4b"  # <-- SESUAIKAN DENGAN MODEL ANDA (cek dengan: ollama list)
NAMA_AI = "Saki"
SAVE_FOLDER = "ringkasan"
DB_FILE = "saki_memory.db"
EXPORT_FOLDER = "exports"
RINGKASAN_RIWAYAT = 300

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
    
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT DEFAULT 'umum',
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        deleted INTEGER DEFAULT 0
    )''')
    
    conn.commit()
    conn.close()

# ========== FUNGSI DATABASE ==========
def simpan_chat(role, content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO conversations (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

def simpan_fakta(category, content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO facts (category, content) VALUES (?, ?)", (category, content))
    conn.commit()
    conn.close()

def lihat_semua_fakta():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, category, content, created_at FROM facts WHERE deleted = 0 ORDER BY id DESC")
    results = c.fetchall()
    conn.close()
    return results

def lihat_fakta_by_id(fact_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, category, content, created_at FROM facts WHERE id = ? AND deleted = 0", (fact_id,))
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
    c.execute("SELECT id, category, content, created_at FROM facts WHERE deleted = 0 AND content LIKE ? ORDER BY id DESC", (f'%{keyword}%',))
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
        fakta_text = "\n".join([f"- [{f[1]}] {f[2]}" for f in riwayat_fakta])
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
    
    # JSON export (untuk import)
    json_data = []
    for f in fakta:
        json_data.append({
            "id": f[0],
            "category": f[1],
            "content": f[2],
            "created_at": f[3]
        })
    
    json_path = f"{EXPORT_FOLDER}/memory_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    # Markdown export (untuk dibaca manusia)
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
                f.write(f"- **[#{item[0]}]** {item[2]}\n")
                f.write(f"  📅 {item[3]}\n")
            f.write("\n")
    
    return json_path, md_path

def impor_memory(filepath):
    # Cek ekstensi file
    if not filepath.lower().endswith('.json'):
        return None, "Hanya file .json yang didukung. File .md tidak bisa diimpor."
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        imported = 0
        skipped = 0
        
        for item in data:
            content = item.get("content", "")
            category = item.get("category", "umum")
            
            # Cek duplikat
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id FROM facts WHERE content = ? AND deleted = 0", (content,))
            existing = c.fetchone()
            conn.close()
            
            if existing:
                skipped += 1
            else:
                simpan_fakta(category, content)
                imported += 1
        
        return imported, skipped
    
    except json.JSONDecodeError:
        return None, "File bukan JSON yang valid. Pastikan Anda memilih file .json hasil ekspor."
    except Exception as e:
        return None, str(e)

# ========== TAMPILAN ==========
def tampilkan_fakta(fakta_list, judul="FAKTA TERSIMPAN"):
    if not fakta_list:
        print(f"\n📭 Tidak ada {judul.lower()}.")
        return
    
    # Kelompokkan per kategori
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
            print(f"  [#{item[0]}] {item[2]}")
            print(f"       📅 {item[3]}")
    
    print("\n" + "=" * 60)
    print(f"Total: {len(fakta_list)} fakta dalam {len(categories)} kategori")

# ========== PERINTAH KHUSUS ==========
def proses_perintah_khusus(user_input):
    
    # !lihat
    if user_input.lower() == "!lihat":
        fakta = lihat_semua_fakta()
        tampilkan_fakta(fakta)
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
                print(f"\n📝 Edit Fakta #{fact_id}:")
                print(f"   Kategori: {fakta[1]}")
                print(f"   Lama: {fakta[2]}")
                baru = input("   Baru: ").strip()
                if baru:
                    edit_fakta(fact_id, baru)
                    print(f"\n✅ Fakta #{fact_id} berhasil diupdate.")
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
                    print(f"   ✅ Fakta #{fact_id} dihapus. (ID tidak akan digunakan ulang)")
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
            print(f"   [#{f[0]}] [{f[1]}] {f[2]}")
        
        konfirmasi = input("\n   Lanjutkan? (y/n): ").strip().lower()
        if konfirmasi != "y":
            print("   ❌ Batal.")
            return True
        
        print("   ⏳ Saki sedang menggabungkan...")
        hasil_merge = merge_fakta_dengan_ai(fakta_list)
        
        print(f"\n   Hasil gabungan: {hasil_merge}")
        konfirmasi2 = input("\n   Simpan? (y/n): ").strip().lower()
        
        if konfirmasi2 == "y":
            kategori = fakta_list[0][1]
            simpan_fakta(kategori, hasil_merge)
            for f in fakta_list:
                hapus_fakta(f[0])
            print(f"   ✅ Fakta baru tersimpan. {len(fakta_list)} fakta lama dihapus.")
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
        print("   File .md tidak bisa diimpor.")
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
║         📋 PERINTAH {NAMA_AI.upper()} v2.5                     ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  💬 CHAT & RINGKASAN                                 ║
║  ringkas       Mode meringkas teks panjang            ║
║  Catat: [teks] Simpan fakta ke memori                 ║
║                                                      ║
║  📚 MEMORY MANAGEMENT                                ║
║  !lihat        Lihat semua fakta (per kategori)       ║
║  !cari [kata]  Cari fakta dengan kata kunci           ║
║  !edit [id]    Edit isi fakta                         ║
║  !hapus [id]   Hapus fakta (ID tetap, tak terpakai)   ║
║  !merge [ids]  Gabungkan beberapa fakta dengan AI     ║
║  !ekspor       Ekspor memory ke JSON & Markdown       ║
║  !impor        Impor dari file JSON (bukan .md!)      ║
║                                                      ║
║  📋 LAINNYA                                          ║
║  !riwayat      Lihat riwayat chat terbaru             ║
║  !bantuan      Tampilkan menu ini                     ║
║  keluar        Tutup program                          ║
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
    print(f"🤖 {NAMA_AI} - AI Pribadi Anda (v2.5 — Memory Control Center)")
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
            simpan_chat("SAKI", ringkasan)
        
        # Catat fakta
        elif user_input.lower().startswith("catat:"):
            simpan_chat("USER", user_input)
            fakta = user_input[6:].strip()
            if fakta:
                kategori = tebak_kategori(fakta)
                simpan_fakta(kategori, fakta)
                print(f"\n✅ Tersimpan: [#{kategori}] {fakta}")
            else:
                print("\n⚠️ Format: Catat: [informasi]. Contoh: Catat: Saya sedang membuat website topup")
        
        # Chat biasa
        else:
            simpan_chat("USER", user_input)
            print("\n⏳ Berpikir...")
            fakta = lihat_semua_fakta()
            jawaban = chat_biasa(user_input, riwayat_fakta=fakta)
            print(f"\n🤖 {NAMA_AI}: {jawaban}")
            simpan_chat("SAKI", jawaban)

if __name__ == "__main__":
    main()