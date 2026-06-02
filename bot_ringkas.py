import ollama
import datetime
import os

# ========== KONFIGURASI ==========
MODEL = "qwen3:4b"  # ganti ke "qwen2.5:3b" kalau qwen3 belum ada
SAVE_FOLDER = "ringkasan"
SYSTEM_PROMPT = """Kamu adalah asisten AI pribadi bernama Aria.
Kamu membantu merangkum dokumen, menjawab pertanyaan, dan mengingat informasi penting.
Kamu menjawab dalam Bahasa Indonesia yang natural, hangat, dan langsung ke inti.
Saat merangkum, gunakan format:
## Ringkasan
[3-5 poin utama dalam bahasa Indonesia yang jelas]

## Kata Kunci
[keyword1, keyword2, keyword3]"""

# ========== FUNGSI UTAMA ==========
def ringkas_teks(teks):
    """Meringkas teks panjang menjadi poin-poin utama."""
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
    """Simpan ringkasan ke file .txt dengan timestamp."""
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SAVE_FOLDER}/ringkasan_{timestamp}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"=== RINGKASAN ===\n{ringkasan}\n\n")
        f.write(f"=== TEKS ASLI ===\n{teks_asal[:500]}...\n")
        f.write(f"\nDisimpan: {datetime.datetime.now()}")
    
    return filename

def chat_biasa(pesan):
    """Chat biasa tanpa peringkasan."""
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": pesan}
        ]
    )
    return response["message"]["content"]

# ========== LOOP UTAMA ==========
def main():
    print("=" * 50)
    print("🤖 Aria - AI Pribadi Anda")
    print("=" * 50)
    print("Perintah:")
    print("  ringkas  : Memulai mode peringkasan teks")
    print("  keluar   : Menutup program")
    print("  [apa saja] : Chat biasa")
    print("=" * 50)
    
    while True:
        user_input = input("\n🧑 Anda: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() == "keluar":
            print("👋 Sampai jumpa!")
            break
        
        elif user_input.lower() == "ringkas":
            print("\n📝 Mode Ringkasan (ketik 'SELESAI' di baris baru untuk memproses):")
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
            
            # Simpan
            filepath = simpan_ringkasan(teks, ringkasan)
            print(f"\n💾 Ringkasan disimpan di: {filepath}")
        
        else:
            # Chat biasa
            print("\n⏳ Berpikir...")
            jawaban = chat_biasa(user_input)
            print(f"\n🤖 Aria: {jawaban}")

if __name__ == "__main__":
    main()