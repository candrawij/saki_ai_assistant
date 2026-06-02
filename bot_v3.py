import ollama
import datetime
import os
import sqlite3
import json
import chromadb
from chromadb.utils import embedding_functions
from PyPDF2 import PdfReader
from docx import Document

# ========== KONFIGURASI ==========
MODEL = "qwen3:4b"  # SESUAIKAN DENGAN MODEL ANDA
NAMA_AI = "Saki"
SAVE_FOLDER = "ringkasan"
DB_FILE = "saki_memory.db"
EXPORT_FOLDER = "exports"
DOCUMENTS_FOLDER = "documents"
CHROMA_FOLDER = "chroma_db"
RINGKASAN_RIWAYAT = 300
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
    
    # Tabel documents
    c.execute('''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL,
        file_type TEXT NOT NULL,
        summary TEXT,
        full_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Auto-migration: tambah kolom baru jika belum ada
    c.execute("PRAGMA table_info(facts)")
    columns = [col[1] for col in c.fetchall()]
    
    if 'source' not in columns:
        c.execute("ALTER TABLE facts ADD COLUMN source TEXT DEFAULT 'manual'")
    if 'confidence' not in columns:
        c.execute("ALTER TABLE facts ADD COLUMN confidence REAL DEFAULT 1.0")
    
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

def lihat_semua_fakta():
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

def cek_fakta_duplikat(content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, content FROM facts WHERE deleted = 0")
    semua = c.fetchall()
    conn.close()
    
    for fakta in semua:
        if content.lower() in fakta[1].lower() or fakta[1].lower() in content.lower():
            return fakta[0]
    return None

def lihat_riwayat_chat(limit=20):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT role, content, timestamp FROM conversations ORDER BY id DESC LIMIT ?", (limit,))
    results = c.fetchall()
    conn.close()
    return results

# ========== FUNGSI DOKUMEN ==========
def simpan_dokumen(filename, filepath, file_type, full_text, summary):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO documents (filename, filepath, file_type, full_text, summary) VALUES (?, ?, ?, ?, ?)",
        (filename, filepath, file_type, full_text, summary)
    )
    doc_id = c.lastrowid
    conn.commit()
    conn.close()
    return doc_id

def lihat_semua_dokumen():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, filename, file_type, summary, created_at FROM documents ORDER BY created_at DESC")
    results = c.fetchall()
    conn.close()
    return results

def lihat_dokumen_by_id(doc_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, filename, filepath, file_type, summary, full_text, created_at FROM documents WHERE id = ?", (doc_id,))
    result = c.fetchone()
    conn.close()
    return result

def hapus_dokumen(doc_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()

def cari_dokumen(keyword):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, filename, file_type, summary, created_at FROM documents WHERE filename LIKE ? OR summary LIKE ? ORDER BY created_at DESC", (f'%{keyword}%', f'%{keyword}%'))
    results = c.fetchall()
    conn.close()
    return results

# ========== CHROMA DB ==========
def init_chroma():
    os.makedirs(CHROMA_FOLDER, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_FOLDER)
    
    ollama_ef = embedding_functions.OllamaEmbeddingFunction(
        url="http://localhost:11434/api/embeddings",
        model_name="nomic-embed-text"
    )
    
    collection = client.get_or_create_collection(
        name="documents",
        embedding_function=ollama_ef
    )
    return collection

def tambah_ke_chroma(doc_id, full_text, filename):
    try:
        collection = init_chroma()
        collection.delete(ids=[str(doc_id)])
        
        chunks = [full_text[i:i+1000] for i in range(0, len(full_text), 1000)]
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            collection.add(
                documents=[chunk],
                metadatas=[{"doc_id": doc_id, "filename": filename, "chunk": i}],
                ids=[chunk_id]
            )
        return True
    except Exception as e:
        print(f"   ⚠️ Gagal indexing ke ChromaDB: {e}")
        return False

def cari_dokumen_semantik(query, n_results=3):
    try:
        collection = init_chroma()
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        doc_ids = set()
        if results['metadatas'] and results['metadatas'][0]:
            for meta in results['metadatas'][0]:
                if meta:
                    doc_ids.add(meta['doc_id'])
        
        dokumen = []
        for doc_id in doc_ids:
            doc = lihat_dokumen_by_id(int(doc_id))
            if doc:
                dokumen.append(doc)
        
        return dokumen
    except Exception as e:
        print(f"   ⚠️ Pencarian semantik gagal: {e}")
        return []

def cek_model_embedding():
    try:
        models = ollama.list()
        model_names = [m['name'] for m in models['models']]
        if 'nomic-embed-text:latest' not in model_names:
            return False
        return True
    except:
        return False

# ========== EKSTRAKSI FILE ==========
def ekstrak_teks_dari_pdf(filepath):
    try:
        reader = PdfReader(filepath)
        teks = ""
        for page in reader.pages:
            teks += page.extract_text() + "\n"
        return teks.strip()
    except Exception as e:
        return f"[Error membaca PDF: {e}]"

def ekstrak_teks_dari_docx(filepath):
    try:
        doc = Document(filepath)
        teks = ""
        for para in doc.paragraphs:
            teks += para.text + "\n"
        return teks.strip()
    except Exception as e:
        return f"[Error membaca DOCX: {e}]"

def ekstrak_teks_dari_txt(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        with open(filepath, "r", encoding="latin-1") as f:
            return f.read().strip()

def proses_upload_file(filepath):
    if not os.path.exists(filepath):
        return None, "File tidak ditemukan."
    
    filename = os.path.basename(filepath)
    ext = os.path.splitext(filename)[1].lower()
    
    if ext == ".pdf":
        teks = ekstrak_teks_dari_pdf(filepath)
        file_type = "PDF"
    elif ext == ".docx":
        teks = ekstrak_teks_dari_docx(filepath)
        file_type = "DOCX"
    elif ext in [".txt", ".md", ".markdown"]:
        teks = ekstrak_teks_dari_txt(filepath)
        file_type = "TXT"
    else:
        return None, f"Format {ext} tidak didukung. Gunakan PDF, DOCX, TXT, atau MD."
    
    if not teks or teks.startswith("[Error"):
        return None, f"Gagal mengekstrak teks: {teks}"
    
    teks_untuk_ringkasan = teks[:4000]
    
    prompt = f"Ringkas dokumen berikut:\n\nJudul: {filename}\n\n{teks_untuk_ringkasan}"
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )
    ringkasan = response["message"]["content"]
    
    os.makedirs(DOCUMENTS_FOLDER, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_filename = f"{timestamp}_{filename}"
    saved_path = os.path.join(DOCUMENTS_FOLDER, saved_filename)
    
    with open(filepath, "rb") as src:
        with open(saved_path, "wb") as dst:
            dst.write(src.read())
    
    doc_id = simpan_dokumen(filename, saved_path, file_type, teks, ringkasan)
    tambah_ke_chroma(doc_id, teks, filename)
    
    return doc_id, ringkasan

# ========== AUTO-EXTRACTION ==========
def auto_ekstrak_fakta(pesan_user):
    if pesan_user.startswith("!") or pesan_user.lower() in ["ringkas", "keluar"]:
        return None
    
    if len(pesan_user.split()) < 2:
        return None
    
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
        
        if hasil.startswith("```"):
            hasil = hasil.split("\n", 1)[1]
            if hasil.endswith("```"):
                hasil = hasil[:-3]
        hasil = hasil.strip()
        
        data = json.loads(hasil)
        
        if data.get("is_fact") and data.get("confidence", 0) >= AUTO_EXTRACT_THRESHOLD:
            return {
                "fact": data["fact"],
                "category": data.get("category", "umum"),
                "confidence": data["confidence"]
            }
        
        return None
    
    except:
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
        fakta_text = "\n".join([f"- [{f[1]}] {f[2]}" for f in riwayat_fakta if f[4] >= 0.5])
        if fakta_text:
            messages.append({"role": "system", "content": f"Informasi yang kamu ingat tentang user:\n{fakta_text}"})
    messages.append({"role": "user", "content": pesan})
    response = ollama.chat(model=MODEL, messages=messages)
    return response["message"]["content"]

def tanya_dokumen(doc_id, pertanyaan):
    doc = lihat_dokumen_by_id(doc_id)
    if not doc:
        return f"Dokumen #{doc_id} tidak ditemukan."
    
    teks = doc[5][:3000]
    
    prompt = f"""Berdasarkan dokumen berikut, jawab pertanyaan user.

DOKUMEN: {doc[1]}
ISI:
{teks}

PERTANYAAN: {pertanyaan}

JAWABAN:"""
    
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Kamu adalah asisten yang membantu memahami dokumen. Jawab dalam Bahasa Indonesia."},
            {"role": "user", "content": prompt}
        ]
    )
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
    
    manual = sum(1 for f in fakta_list if f[3] == "manual")
    auto = sum(1 for f in fakta_list if f[3] == "auto")
    print(f"Total: {len(fakta_list)} fakta | 👤 Manual: {manual} | 🤖 Auto: {auto}")
    print(f"Kategori: {len(categories)}")
    
    low_conf = [f for f in fakta_list if f[4] < AUTO_EXTRACT_THRESHOLD and f[4] >= 0.5]
    if low_conf:
        print(f"\n⚠️ {len(low_conf)} fakta auto dengan confidence rendah. Review dengan !edit.")

def tampilkan_dokumen(docs_list, judul="DOKUMEN TERSIMPAN"):
    if not docs_list:
        print(f"\n📭 Tidak ada {judul.lower()}.")
        return
    
    print(f"\n📚 {judul}:")
    print("=" * 60)
    
    for d in docs_list:
        print(f"\n  📄 [#{d[0]}] {d[1]}")
        print(f"     📁 Tipe: {d[2]}")
        print(f"     📅 Upload: {d[4]}")
        if d[3]:
            summary_preview = d[3][:200]
            if len(d[3]) > 200:
                summary_preview += "..."
            print(f"     📝 Ringkasan: {summary_preview}")
    
    print("\n" + "=" * 60)
    print(f"Total: {len(docs_list)} dokumen")

# ========== PERINTAH KHUSUS ==========
def proses_perintah_khusus(user_input):
    
    # !lihat
    if user_input.lower() == "!lihat":
        fakta = lihat_semua_fakta()
        tampilkan_fakta(fakta)
        return True
    
    # !lihatauto
    if user_input.lower() == "!lihatauto":
        fakta = lihat_semua_fakta()
        fakta_auto = [f for f in fakta if f[3] == "auto"]
        tampilkan_fakta(fakta_auto, "FAKTA AUTO (Hasil Ekstraksi Otomatis)")
        return True
    
    # !lihatmanual
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
            print("\n⚠️ Format: !merge [id1] [id2]. Contoh: !merge 1 3")
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
    
    # !upload
    if user_input.lower().startswith("!upload"):
        filepath = user_input[8:].strip()
        if not filepath:
            print("\n⚠️ Format: !upload [path file]. Contoh: !upload C:\\Users\\nama\\dokumen.pdf")
            return True
        
        if not os.path.exists(filepath):
            print(f"\n⚠️ File tidak ditemukan: {filepath}")
            return True
        
        filename = os.path.basename(filepath)
        print(f"\n📤 Mengupload: {filename}")
        print("   ⏳ Mengekstrak teks...")
        
        result = proses_upload_file(filepath)
        
        if result[0] is None:
            print(f"\n❌ Gagal upload: {result[1]}")
        else:
            doc_id, ringkasan = result
            print(f"\n✅ Upload berhasil!")
            print(f"   📄 ID Dokumen: #{doc_id}")
            print(f"   💾 Disimpan di: {DOCUMENTS_FOLDER}/")
            print(f"\n📝 Ringkasan otomatis:")
            print(f"{ringkasan}")
        return True
    
    # !dokumen
    if user_input.lower() == "!dokumen":
        docs = lihat_semua_dokumen()
        tampilkan_dokumen(docs)
        return True
    
    # !caridok
    if user_input.lower().startswith("!caridok"):
        keyword = user_input[9:].strip()
        if not keyword:
            print("\n⚠️ Format: !caridok [kata kunci]. Contoh: !caridok proposal")
        else:
            hasil = cari_dokumen(keyword)
            tampilkan_dokumen(hasil, f"Hasil pencarian dokumen: '{keyword}' (teks)")
            
            print(f"\n🔍 Mencari dengan semantik...")
            hasil_semantik = cari_dokumen_semantik(keyword)
            if hasil_semantik:
                tampilkan_dokumen(hasil_semantik, f"Hasil pencarian semantik: '{keyword}'")
            else:
                print("   (Tidak ada hasil semantik tambahan)")
        return True
    
    # !tanya
    if user_input.lower().startswith("!tanya"):
        parts = user_input.split(maxsplit=2)
        if len(parts) >= 2 and parts[1].isdigit():
            doc_id = int(parts[1])
            
            if len(parts) >= 3:
                pertanyaan = parts[2]
            else:
                pertanyaan = input("   ❓ Pertanyaan tentang dokumen ini: ").strip()
            
            if not pertanyaan:
                print("\n⚠️ Pertanyaan tidak boleh kosong.")
                return True
            
            print(f"\n⏳ Membaca dokumen #{doc_id}...")
            jawaban = tanya_dokumen(doc_id, pertanyaan)
            print(f"\n🤖 {NAMA_AI}: {jawaban}")
        else:
            print("\n⚠️ Format: !tanya [doc_id] [pertanyaan]")
            print("   Contoh: !tanya 1 Apa isi dokumen ini?")
        return True
    
    # !hapusdok
    if user_input.lower().startswith("!hapusdok"):
        parts = user_input.split()
        if len(parts) == 2 and parts[1].isdigit():
            doc_id = int(parts[1])
            doc = lihat_dokumen_by_id(doc_id)
            if not doc:
                print(f"\n⚠️ Dokumen #{doc_id} tidak ditemukan.")
            else:
                print(f"\n🗑️ Hapus Dokumen #{doc_id}: {doc[1]}")
                konfirmasi = input("   Yakin? (y/n): ").strip().lower()
                if konfirmasi == "y":
                    try:
                        collection = init_chroma()
                        all_ids = collection.get()['ids']
                        ids_to_delete = [i for i in all_ids if i.startswith(f"{doc_id}_")]
                        if ids_to_delete:
                            collection.delete(ids=ids_to_delete)
                    except:
                        pass
                    
                    hapus_dokumen(doc_id)
                    
                    if os.path.exists(doc[2]):
                        os.remove(doc[2])
                    
                    print(f"   ✅ Dokumen #{doc_id} dihapus.")
                else:
                    print("   ❌ Batal.")
        else:
            print("\n⚠️ Format: !hapusdok [id]. Contoh: !hapusdok 1")
        return True
    
    # !bantuan
    if user_input.lower() == "!bantuan":
        print(f"""
╔══════════════════════════════════════════════════════╗
║       📋 PERINTAH {NAMA_AI.upper()} v3.0 — Knowledge Base       ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  💬 CHAT & RINGKASAN                                 ║
║  ringkas        Mode meringkas teks panjang           ║
║  Catat: [teks]  Simpan fakta manual                   ║
║  [chat biasa]   {NAMA_AI} auto-ekstrak fakta penting 🤖     ║
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
║  📄 KNOWLEDGE BASE (DOKUMEN)                          ║
║  !upload [path] Upload PDF/DOCX/TXT/MD                ║
║  !dokumen       Lihat semua dokumen                   ║
║  !caridok [key] Cari dokumen (teks & semantik)        ║
║  !tanya [id]    Tanya-jawab tentang dokumen           ║
║  !hapusdok [id] Hapus dokumen                         ║
║                                                      ║
║  📋 LAINNYA                                          ║
║  !riwayat       Lihat riwayat chat terbaru            ║
║  !bantuan       Tampilkan menu ini                    ║
║  keluar         Tutup program                         ║
║                                                      ║
╚══════════════════════════════════════════════════════╝

⚠️ Sebelum pakai fitur dokumen, install model embedding:
   ollama pull nomic-embed-text
        """)
        return True
    
    return False

# ========== KATEGORI OTOMATIS ==========
def tebak_kategori(teks):
    teks_lower = teks.lower()
    if any(k in teks_lower for k in ["proyek", "website", "aplikasi", "coding", "program", "developer", "tugas akhir", "skripsi"]):
        return "proyek"
    elif any(k in teks_lower for k in ["suka", "tidak suka", "preferensi", "kebiasaan", "hobi", "anime", "buku", "film", "musik", "kopi"]):
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
    print(f"🤖 {NAMA_AI} - AI Pribadi Anda (v3.0 — Knowledge Base)")
    print("=" * 60)
    
    if not cek_model_embedding():
        print("⚠️ Model embedding 'nomic-embed-text' belum terinstall.")
        print("   Jalankan: ollama pull nomic-embed-text")
        print("   Fitur pencarian semantik dokumen tidak akan berfungsi.")
        print("-" * 60)
    
    print(f"✨ {NAMA_AI} bisa auto-ekstrak fakta dari chat biasa!")
    print("   🤖 = Auto  |  👤 = Manual")
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
            simpan_chat(NAMA_AI.upper(), ringkasan)
        
        # Catat fakta manual
        elif user_input.lower().startswith("catat:"):
            simpan_chat("USER", user_input)
            fakta = user_input[6:].strip()
            if fakta:
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
        
        # Chat biasa + auto-ekstraksi
        else:
            simpan_chat("USER", user_input)
            print("\n⏳ Berpikir...")
            
            # Auto-ekstrak
            hasil_auto = auto_ekstrak_fakta(user_input)
            
            fakta = lihat_semua_fakta()
            jawaban = chat_biasa(user_input, riwayat_fakta=fakta)
            print(f"\n🤖 {NAMA_AI}: {jawaban}")
            simpan_chat(NAMA_AI.upper(), jawaban)
            
            # Simpan hasil auto-ekstraksi
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