import ollama
import datetime
import os
import sqlite3

# ========== KONFIGURASI ==========
MODEL = "qwen3:4b"  # ganti ke "qwen2.5:3b" kalau qwen3 belum ada
SAVE_FOLDER = "ringkasan"
DB_FILE = "aria_memory.db"
SYSTEM_PROMPT = """Kamu adalah asisten AI pribadi bernama Aria.
Kamu membantu merangkum dokumen, menjawab pertanyaan, dan mengingat informasi penting.
Kamu menjawab dalam Bahasa Indonesia yang natural, hangat, dan langsung ke inti.
Saat merangkum, gunakan format:
## Ringkasan
[3-5 poin utama dalam bahasa Indonesia yang jelas]

## Kata Kunci
[keyword1, keyword2, keyword3]"""

# ========== DATABASE ==========
def init_db():
    """Buat tabel kalau belum ada."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Tabel riwayat chat
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Tabel fakta (memori jangka panjang)
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

def simpan_chat(role, content):
    """Simpan setiap pesan ke tabel conversations."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO conversations (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

def simpan_fakta(category, content):
    """Simpan fakta ke tabel facts."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO facts (category, content) VALUES (?, ?)", (category, content))
    conn.commit()
    conn.close()

def lihat_semua_fakta():
    """Ambil semua fakta yang belum dihapus."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, category, content, created_at FROM facts WHERE deleted = 0 ORDER BY created_at DESC")
    results = c.fetchall()
    conn.close()
    return results

def hapus_fakta(fact_id):
    """Soft delete fakta."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE facts SET deleted = 1 WHERE id = ?", (fact_id,))
    conn.commit()
    conn.close()

def lihat_riwayat_chat(limit=20):
    """Ambil riwayat chat terbaru."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT role, content, timestamp FROM conversations ORDER BY id DESC LIMIT ?", (limit,))
    results = c.fetchall()
    conn.close()
    return results

# ========== FUNGSI AI ==========
def ringkas_teks(teks):
    """Meringkas teks panjang."""
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
    """Simpan ringkasan ke file .txt."""
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SAVE_FOLDER}/ringkasan_{timestamp}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"=== RINGKASAN ===\n{ringkasan}\n\n")
        f.write(f"=== TEKS ASLI ===\n{teks_asal[:500]}...\n")
        f.write(f"\nDisimpan: {datetime.datetime.now()}")
    
    return filename

def chat_biasa(pesan, riwayat_fakta=None):
    """Chat biasa dengan konteks fakta."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Sisipkan fakta yang diingat sebagai konteks
    if riwayat_fakta:
        fakta_text = "\n".join([f"- [{f[1]}] {f[2]}" for f in riwayat_fakta])
        messages.append({"role": "system", "content": f"Informasi yang kamu ingat tentang user:\n{fakta_text}"})
    
    messages.append({"role": "user", "content": pesan})
    
    response = ollama.chat(model=MODEL, messages=messages)
    return response["message"]["content"]

# ========== PERINTAH ==========
def proses_perintah_khusus(user_input):
    """Tangani perintah khusus seperti !lihat, !hapus, !riwayat, dll."""
    
    # !lihat — tampilkan semua fakta
    if user_input.lower() == "!lihat":
        fakta = lihat_semua_fakta()
        if not fakta:
            print("\n📭 Belum ada fakta yang tersimpan.")
        else:
            print("\n📚 FAKTA TERSIMPAN:")
            print("-" * 40)
            for f in fakta:
                print(f"  [{f[0]}] 📁 {f[1]} | {f[2]}")
                print(f"       📅 {f[3]}")
            print("-" * 40)
        return True
    
    # !hapus [id] — hapus fakta
    if user_input.lower().startswith("!hapus"):
        parts = user_input.split()
        if len(parts) == 2 and parts[1].isdigit():
            fact_id = int(parts[1])
            hapus_fakta(fact_id)
            print(f"\n🗑️ Fakta #{fact_id} dihapus.")
        else:
            print("\n⚠️ Format: !hapus [id]. Contoh: !hapus 3")
        return True
    
    # !riwayat — lihat riwayat chat
    if user_input.lower() == "!riwayat":
        chats = lihat_riwayat_chat(20)
        if not chats:
            print("\n📭 Belum ada riwayat chat.")
        else:
            print("\n💬 RIWAYAT CHAT TERBARU:")
            print("-" * 40)
            for c in reversed(chats):
                role_icon = "🧑" if c[0] == "USER" else "🤖"
                print(f"  {role_icon} [{c[2]}] {c[1][:100]}...")
            print("-" * 40)
        return True
    
    # !bantuan — tampilkan semua perintah
    if user_input.lower() == "!bantuan":
        print("""
📋 PERINTAH TERSEDIA:
  ringkas       — Mode meringkas teks panjang
  Catat: [teks] — Simpan fakta ke memori (contoh: Catat: Saya suka kopi)
  !lihat        — Lihat semua fakta tersimpan
  !hapus [id]   — Hapus fakta (contoh: !hapus 3)
  !riwayat      — Lihat riwayat chat terbaru
  !bantuan      — Tampilkan menu ini
  keluar        — Tutup program
        """)
        return True
    
    return False

# ========== LOOP UTAMA ==========
def main():
    init_db()
    
    print("=" * 50)
    print("🤖 Aria - AI Pribadi Anda (v1.5)")
    print("=" * 50)
    print("Perintah:")
    print("  ringkas       : Mode ringkasan teks")
    print("  Catat: [info] : Simpan informasi ke memori")
    print("  !lihat        : Lihat semua fakta")
    print("  !hapus [id]   : Hapus fakta")
    print("  !riwayat      : Lihat riwayat chat")
    print("  !bantuan      : Lihat semua perintah")
    print("  keluar        : Tutup program")
    print("=" * 50)
    
    while True:
        user_input = input("\n🧑 Anda: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() == "keluar":
            print("👋 Sampai jumpa!")
            break
        
        # Cek perintah khusus dulu (!lihat, !hapus, !riwayat, !bantuan)
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
            
            # Simpan ke file
            filepath = simpan_ringkasan(teks, ringkasan)
            print(f"\n💾 Ringkasan disimpan di: {filepath}")
            
            simpan_chat("ARIA", ringkasan)
        
        # Catat fakta
        elif user_input.lower().startswith("catat:"):
            simpan_chat("USER", user_input)
            fakta = user_input[6:].strip()
            
            if fakta:
                # Coba tebak kategori dengan kata kunci sederhana
                if any(k in fakta.lower() for k in ["proyek", "website", "aplikasi", "coding"]):
                    kategori = "proyek"
                elif any(k in fakta.lower() for k in ["suka", "tidak suka", "preferensi", "kebiasaan"]):
                    kategori = "preferensi"
                elif any(k in fakta.lower() for k in ["kontak", "telepon", "email", "alamat"]):
                    kategori = "kontak"
                else:
                    kategori = "umum"
                
                simpan_fakta(kategori, fakta)
                print(f"\n✅ Tersimpan: [{kategori}] {fakta}")
            else:
                print("\n⚠️ Format: Catat: [informasi]. Contoh: Catat: Saya sedang membuat website topup")
        
        # Chat biasa
        else:
            simpan_chat("USER", user_input)
            print("\n⏳ Berpikir...")
            
            # Sertakan fakta sebagai konteks
            fakta = lihat_semua_fakta()
            jawaban = chat_biasa(user_input, riwayat_fakta=fakta)
            
            print(f"\n🤖 Aria: {jawaban}")
            simpan_chat("ARIA", jawaban)

if __name__ == "__main__":
    main()