import streamlit as st
import ollama
import datetime
import os
import sqlite3
import json
import chromadb
from chromadb.utils import embedding_functions
from PyPDF2 import PdfReader
from docx import Document
import tempfile
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ========== KONFIGURASI ==========
MODEL = "qwen3:4b"  # SESUAIKAN
NAMA_AI = "Saki"
SAVE_FOLDER = "ringkasan"
DB_FILE = "saki_memory.db"
EXPORT_FOLDER = "exports"
DOCUMENTS_FOLDER = "documents"
CHROMA_FOLDER = "chroma_db"
AUTO_EXTRACT_THRESHOLD = 0.7

# Password admin (dari .env atau default)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "saki2024")

SYSTEM_PROMPT = f"""Kamu adalah asisten AI pribadi bernama {NAMA_AI}.
Kamu membantu merangkum dokumen, menjawab pertanyaan, dan mengingat informasi penting.
Kamu menjawab dalam Bahasa Indonesia yang natural, hangat, dan langsung ke inti.
Saat merangkum, gunakan format:
## Ringkasan
[3-5 poin utama]

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
    
    c.execute('''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL,
        file_type TEXT NOT NULL,
        summary TEXT,
        full_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Auto-migration
    c.execute("PRAGMA table_info(facts)")
    columns = [col[1] for col in c.fetchall()]
    if 'source' not in columns:
        c.execute("ALTER TABLE facts ADD COLUMN source TEXT DEFAULT 'manual'")
    if 'confidence' not in columns:
        c.execute("ALTER TABLE facts ADD COLUMN confidence REAL DEFAULT 1.0")
    # V4.5: Kolom baru untuk Memory Intelligence
    if 'importance' not in columns:
        c.execute("ALTER TABLE facts ADD COLUMN importance INTEGER DEFAULT 5")
    if 'access_count' not in columns:
        c.execute("ALTER TABLE facts ADD COLUMN access_count INTEGER DEFAULT 0")
    if 'last_accessed' not in columns:
        c.execute("ALTER TABLE facts ADD COLUMN last_accessed TIMESTAMP DEFAULT NULL")
    
    conn.commit()
    conn.close()

# ========== FUNGSI DATABASE (sama seperti V3) ==========
def simpan_chat(role, content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO conversations (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

def simpan_fakta(category, content, source="manual", confidence=1.0, importance=5):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO facts (category, content, source, confidence, importance) VALUES (?, ?, ?, ?, ?)",
              (category, content, source, confidence, importance))
    conn.commit()
    conn.close()

def lihat_semua_fakta():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, category, content, source, confidence, importance, access_count, last_accessed, created_at FROM facts WHERE deleted = 0 ORDER BY importance DESC, id DESC")
    results = c.fetchall()
    conn.close()
    return results

def lihat_fakta_by_id(fact_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, category, content, source, confidence, importance, access_count, last_accessed, created_at FROM facts WHERE id = ? AND deleted = 0", (fact_id,))
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

def simpan_dokumen(filename, filepath, file_type, full_text, summary):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO documents (filename, filepath, file_type, full_text, summary) VALUES (?, ?, ?, ?, ?)",
              (filename, filepath, file_type, full_text, summary))
    doc_id = c.lastrowid
    conn.commit()
    conn.close()
    return doc_id

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
    except:
        return False

def cari_dokumen_semantik(query, n_results=3):
    try:
        collection = init_chroma()
        results = collection.query(query_texts=[query], n_results=n_results)
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
    except:
        return []

# ========== EKSTRAKSI FILE ==========
def ekstrak_teks_dari_pdf(filepath):
    try:
        reader = PdfReader(filepath)
        return "\n".join([page.extract_text() for page in reader.pages])
    except:
        return None

def ekstrak_teks_dari_docx(filepath):
    try:
        doc = Document(filepath)
        return "\n".join([para.text for para in doc.paragraphs])
    except:
        return None

def ekstrak_teks_dari_txt(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return None

def proses_upload(uploaded_file):
    filename = uploaded_file.name
    ext = os.path.splitext(filename)[1].lower()
    
    # Simpan ke temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    
    if ext == ".pdf":
        teks = ekstrak_teks_dari_pdf(tmp_path)
        file_type = "PDF"
    elif ext == ".docx":
        teks = ekstrak_teks_dari_docx(tmp_path)
        file_type = "DOCX"
    elif ext in [".txt", ".md"]:
        teks = ekstrak_teks_dari_txt(tmp_path)
        file_type = "TXT"
    else:
        os.unlink(tmp_path)
        return None, f"Format {ext} tidak didukung."
    
    if not teks:
        os.unlink(tmp_path)
        return None, "Gagal mengekstrak teks."
    
    # Ringkas
    teks_ringkas = teks[:4000]
    prompt = f"Ringkas dokumen berikut:\n\nJudul: {filename}\n\n{teks_ringkas}"
    response = ollama.chat(model=MODEL, messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ])
    ringkasan = response["message"]["content"]
    
    # Simpan file
    os.makedirs(DOCUMENTS_FOLDER, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_filename = f"{timestamp}_{filename}"
    saved_path = os.path.join(DOCUMENTS_FOLDER, saved_filename)
    
    with open(tmp_path, "rb") as src:
        with open(saved_path, "wb") as dst:
            dst.write(src.read())
    
    os.unlink(tmp_path)
    
    doc_id = simpan_dokumen(filename, saved_path, file_type, teks, ringkasan)
    tambah_ke_chroma(doc_id, teks, filename)
    
    return doc_id, ringkasan

# ========== AUTO-EXTRACTION ==========
def auto_ekstrak_fakta(pesan_user):
    if len(pesan_user.split()) < 3:
        return None
    
    prompt = f"""Analisis pesan berikut. Apakah mengandung FAKTA PENTING tentang user yang layak dicatat?
Fakta penting: proyek, preferensi, kontak, deadline, skill, pekerjaan, pendidikan.
BUKAN fakta: pertanyaan umum, obrolan ringan, opini.

PESAN: "{pesan_user}"

Jawab JSON saja:
{{"is_fact": true/false, "confidence": 0.0-1.0, "fact": "fakta ringkas", "category": "proyek/preferensi/kontak/jadwal/akun/umum"}}"""

    try:
        response = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": "Jawab HANYA JSON. Tidak boleh teks lain."},
            {"role": "user", "content": prompt}
        ])
        hasil = response["message"]["content"].strip()
        if hasil.startswith("```"): hasil = hasil.split("\n", 1)[1].rstrip("```")
        data = json.loads(hasil)
        if data.get("is_fact") and data.get("confidence", 0) >= AUTO_EXTRACT_THRESHOLD:
            return {"fact": data["fact"], "category": data.get("category", "umum"), "confidence": data["confidence"]}
    except:
        pass
    return None

# ========== FUNGSI AI ==========
# ========== FUNGSI MEMORY INTELLIGENCE (V4.5) ==========
def track_access(fact_id):
    """Catat akses ke fakta: increment counter + update timestamp."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "UPDATE facts SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
        (fact_id,)
    )
    conn.commit()
    conn.close()

def update_importance(fact_id, importance):
    """Update importance score (1-10)."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE facts SET importance = ? WHERE id = ?", (importance, fact_id))
    conn.commit()
    conn.close()

def auto_rate_importance(content, category):
    """AI menilai importance dari sebuah fakta (1-10)."""
    prompt = f"""Nilai seberapa PENTING fakta ini untuk diingat jangka panjang. Skor 1-10.

1-3: Sepele (hobi sesaat, info umum)
4-6: Cukup penting (preferensi, info kerja)
7-9: Penting (proyek aktif, deadline, kontak)
10: Sangat penting (informasi kritis, identitas)

FAKTA: "{content}"
KATEGORI: {category}

Jawab JSON saja: {{"importance": angka, "reason": "alasan singkat"}}"""

    try:
        response = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": "Jawab HANYA JSON."},
            {"role": "user", "content": prompt}
        ])
        hasil = response["message"]["content"].strip()
        if hasil.startswith("```"):
            hasil = hasil.split("\n", 1)[1].rstrip("```")
        data = json.loads(hasil)
        return data.get("importance", 5)
    except:
        return 5  # Default

def deteksi_duplikat_semantik():
    """Gunakan AI untuk mendeteksi fakta yang kemungkinan duplikat."""
    fakta = lihat_semua_fakta()
    
    if len(fakta) < 2:
        return []
    
    # Ambil semua konten
    fakta_list = "\n".join([f"[#{f[0]}] [{f[1]}] {f[2]}" for f in fakta])
    
    prompt = f"""Analisis daftar fakta berikut. Temukan pasangan fakta yang kemungkinan adalah TOPIK YANG SAMA (duplikat atau sangat mirip).

{fakta_list}

Jawab JSON array:
[{{"id1": id_fakta_pertama, "id2": id_fakta_kedua, "reason": "alasan kenapa mirip", "suggestion": "saran merge"}}]

HANYA tampilkan pasangan yang benar-benar mirip. Jika tidak ada, jawab []."""

    try:
        response = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": "Jawab HANYA JSON array."},
            {"role": "user", "content": prompt}
        ])
        hasil = response["message"]["content"].strip()
        if hasil.startswith("```"):
            hasil = hasil.split("\n", 1)[1].rstrip("```")
        return json.loads(hasil)
    except:
        return []

def merge_fakta_dengan_ai(fakta_list):
    """Merge beberapa fakta menjadi satu dengan AI."""
    konten = "\n".join([f"[{f[1]}] {f[2]}" for f in fakta_list])
    prompt = f"""Gabung fakta-fakta berikut menjadi satu deskripsi yang komprehensif:

{konten}

Jawab dengan teks gabungan saja, tanpa JSON."""
    
    try:
        response = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": "Gabung dan ringkas informasi dengan baik."},
            {"role": "user", "content": prompt}
        ])
        return response["message"]["content"].strip()
    except:
        return konten

# ========== FUNGSI AI ==========
def ringkas_teks(teks):
    response = ollama.chat(model=MODEL, messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Ringkas teks berikut:\n\n{teks}"}
    ])
    return response["message"]["content"]

def chat_saki(pesan, riwayat_chat=None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Tambah fakta sebagai konteks
    fakta = lihat_semua_fakta()
    if fakta:
        fakta_text = "\n".join([f"- [{f[1]}] {f[2]}" for f in fakta if f[4] >= 0.5])
        if fakta_text:
            messages.append({"role": "system", "content": f"Info tentang user:\n{fakta_text}"})
        # Track akses untuk fakta dengan importance >= 5
        for f in fakta:
            if f[5] >= 5:
                track_access(f[0])
    
    # Tambah riwayat chat
    if riwayat_chat:
        for msg in riwayat_chat[-10:]:  # 10 pesan terakhir
            messages.append(msg)
    
    messages.append({"role": "user", "content": pesan})
    response = ollama.chat(model=MODEL, messages=messages)
    return response["message"]["content"]

# ========== STREAMLIT UI ==========
st.set_page_config(
    page_title=f"{NAMA_AI} - AI Pribadi",
    page_icon="🤖",
    layout="wide"
)

# ========== AUTENTIKASI ==========
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Sidebar untuk auth
with st.sidebar:
    if not st.session_state.authenticated:
        st.title(f"🔐 Login {NAMA_AI}")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if password == ADMIN_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Password salah!")
        st.stop()
    else:
        st.title(f"🤖 {NAMA_AI} v4.0")
        st.caption("AI Pribadi — Server Lokal")
        
        # Menu
        menu = st.radio("Menu", ["💬 Chat", "📝 Ringkasan", "📚 Memory", "📄 Dokumen", "🧠 Intelligence", "⚙️ Pengaturan"])
        
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.chat_history = []
            st.rerun()

# ========== HALAMAN UTAMA ==========
if st.session_state.authenticated:
    init_db()
    
    # ===== CHAT =====
    if menu == "💬 Chat":
        st.title("💬 Chat dengan Saki")
        st.caption("Saki otomatis mencatat fakta penting dari obrolan 🤖")
        
        # Tampilkan riwayat chat
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # Input chat
        if prompt := st.chat_input("Ketik pesan..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            simpan_chat("USER", prompt)
            
            with st.spinner("Berpikir..."):
                jawaban = chat_saki(prompt, st.session_state.chat_history)
                st.session_state.chat_history.append({"role": "assistant", "content": jawaban})
                simpan_chat(NAMA_AI.upper(), jawaban)
                
                # Auto-ekstrak
                hasil = auto_ekstrak_fakta(prompt)
                if hasil:
                    existing = cek_fakta_duplikat(hasil["fact"])
                    if not existing:
                        importance = auto_rate_importance(hasil["fact"], hasil["category"])
                        simpan_fakta(hasil["category"], hasil["fact"], "auto", hasil["confidence"], importance)
            
            st.rerun()
    
    # ===== RINGKASAN =====
    elif menu == "📝 Ringkasan":
        st.title("📝 Ringkasan Teks")
        
        tab1, tab2 = st.tabs(["Teks Langsung", "Upload File"])
        
        with tab1:
            teks = st.text_area("Masukkan teks yang ingin diringkas:", height=200)
            if st.button("Ringkas Teks", key="ringkas_teks"):
                if teks.strip():
                    with st.spinner("Meringkas..."):
                        hasil = ringkas_teks(teks)
                        st.markdown(hasil)
                        
                        # Simpan
                        os.makedirs(SAVE_FOLDER, exist_ok=True)
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        filepath = f"{SAVE_FOLDER}/ringkasan_{timestamp}.txt"
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(f"{hasil}\n\n=== TEKS ASLI ===\n{teks[:500]}...")
                        st.success(f"Disimpan: {filepath}")
        
        with tab2:
            uploaded = st.file_uploader("Upload file (PDF, DOCX, TXT, MD)", type=["pdf", "docx", "txt", "md"])
            if uploaded and st.button("Upload & Ringkas"):
                with st.spinner("Memproses..."):
                    doc_id, ringkasan = proses_upload(uploaded)
                    if doc_id:
                        st.success(f"Upload berhasil! ID: #{doc_id}")
                        st.markdown(ringkasan)
                    else:
                        st.error(ringkasan)
    
    # ===== MEMORY =====
    elif menu == "📚 Memory":
        st.title("📚 Memory Control Center")
        
        fakta = lihat_semua_fakta()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Fakta", len(fakta))
        with col2:
            st.metric("Manual 👤", sum(1 for f in fakta if f[3] == "manual"))
        with col3:
            st.metric("Auto 🤖", sum(1 for f in fakta if f[3] == "auto"))
        
        st.divider()
        
        # Filter
        filter_mode = st.selectbox("Filter", ["Semua", "Manual", "Auto"])
        if filter_mode == "Manual":
            fakta = [f for f in fakta if f[3] == "manual"]
        elif filter_mode == "Auto":
            fakta = [f for f in fakta if f[3] == "auto"]
        
        for f in fakta:
            source_icon = "🤖" if f[3] == "auto" else "👤"
            conf_str = f" [{f[4]:.0%}]" if f[4] < 1.0 else ""
            importance_indicator = "⭐" * min(f[5], 5)  # Max 5 stars untuk tampilan
            
            with st.expander(f"{source_icon} {importance_indicator} [#{f[0]}] [{f[1]}] {f[2][:80]}...{conf_str}"):
                st.write(f"**Kategori:** {f[1]}")
                st.write(f"**Isi:** {f[2]}")
                st.write(f"**Sumber:** {'Auto' if f[3] == 'auto' else 'Manual'}")
                st.write(f"**Confidence:** {f[4]:.0%}")
                st.write(f"**Importance:** {f[5]}/10")
                st.write(f"**Diakses:** {f[6]} kali")
                st.write(f"**Terakhir diakses:** {f[7] if f[7] else 'Belum pernah'}")
                st.write(f"**Dibuat:** {f[8]}")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button(f"✏️ Edit #{f[0]}", key=f"edit_{f[0]}"):
                        st.session_state[f"edit_mode_{f[0]}"] = True
                
                if st.session_state.get(f"edit_mode_{f[0]}"):
                    baru = st.text_input("Edit:", value=f[2], key=f"input_{f[0]}")
                    if st.button("Simpan", key=f"save_{f[0]}"):
                        edit_fakta(f[0], baru)
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("UPDATE facts SET source = 'manual', confidence = 1.0 WHERE id = ?", (f[0],))
                        conn.commit()
                        conn.close()
                        st.session_state[f"edit_mode_{f[0]}"] = False
                        st.rerun()
                
                with col_b:
                    if st.button(f"🗑️ Hapus #{f[0]}", key=f"hapus_{f[0]}"):
                        hapus_fakta(f[0])
                        st.rerun()
    
    # ===== DOKUMEN =====
    elif menu == "📄 Dokumen":
        st.title("📄 Knowledge Base")
        
        tab1, tab2 = st.tabs(["Upload", "Daftar Dokumen"])
        
        with tab1:
            uploaded = st.file_uploader("Upload dokumen", type=["pdf", "docx", "txt", "md"], key="doc_upload")
            if uploaded and st.button("Upload"):
                with st.spinner("Memproses dokumen..."):
                    doc_id, ringkasan = proses_upload(uploaded)
                    if doc_id:
                        st.success(f"Berhasil! ID: #{doc_id}")
                        st.markdown(ringkasan)
                    else:
                        st.error(ringkasan)
        
        with tab2:
            docs = lihat_semua_dokumen()
            
            cari = st.text_input("🔍 Cari dokumen...")
            if cari:
                # Filter by keyword
                docs = [d for d in docs if cari.lower() in d[1].lower() or (d[3] and cari.lower() in d[3].lower())]
            
            for d in docs:
                with st.expander(f"📄 [#{d[0]}] {d[1]} ({d[2]})"):
                    st.write(f"**Upload:** {d[4]}")
                    if d[3]:
                        st.write("**Ringkasan:**")
                        st.write(d[3])
                    
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button(f"📖 Baca #{d[0]}", key=f"baca_{d[0]}"):
                            doc = lihat_dokumen_by_id(d[0])
                            if doc:
                                st.session_state[f"show_doc_{d[0]}"] = True
                    
                    with col_b:
                        pertanyaan = st.text_input("Tanya:", key=f"tanya_{d[0]}")
                        if st.button(f"❓ Tanya #{d[0]}", key=f"btn_tanya_{d[0]}"):
                            if pertanyaan:
                                doc = lihat_dokumen_by_id(d[0])
                                if doc:
                                    prompt = f"DOKUMEN: {doc[1]}\n\nISI:\n{doc[5][:3000]}\n\nPERTANYAAN: {pertanyaan}"
                                    response = ollama.chat(model=MODEL, messages=[
                                        {"role": "system", "content": "Jawab berdasarkan dokumen."},
                                        {"role": "user", "content": prompt}
                                    ])
                                    st.info(response["message"]["content"])
                    
                    with col_c:
                        if st.button(f"🗑️ Hapus #{d[0]}", key=f"hapusdoc_{d[0]}"):
                            try:
                                collection = init_chroma()
                                all_ids = collection.get()['ids']
                                ids_to_delete = [i for i in all_ids if i.startswith(f"{d[0]}_")]
                                if ids_to_delete:
                                    collection.delete(ids=ids_to_delete)
                            except:
                                pass
                            hapus_dokumen(d[0])
                            if os.path.exists(d[2]):
                                os.remove(d[2])
                            st.rerun()
                    
                    if st.session_state.get(f"show_doc_{d[0]}"):
                        doc = lihat_dokumen_by_id(d[0])
                        if doc:
                            st.text_area("Isi Dokumen:", doc[5], height=300)
                            if st.button("Tutup", key=f"close_{d[0]}"):
                                st.session_state[f"show_doc_{d[0]}"] = False
                                st.rerun()
    
    # ===== INTELLIGENCE (V4.5) =====
    elif menu == "🧠 Intelligence":
        st.title("🧠 Memory Intelligence")
        st.caption("Saki menganalisis kualitas dan kesehatan memory")
        
        fakta = lihat_semua_fakta()
        
        # === HEALTH DASHBOARD ===
        st.subheader("📊 Memory Health Dashboard")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Fakta", len(fakta))
        with col2:
            high_importance = sum(1 for f in fakta if f[5] >= 7)
            st.metric("🔥 High Importance (7+)", high_importance)
        with col3:
            low_importance = sum(1 for f in fakta if f[5] <= 3)
            st.metric("💤 Low Importance (≤3)", low_importance)
        with col4:
            never_accessed = sum(1 for f in fakta if f[6] == 0)
            st.metric("📭 Never Accessed", never_accessed)
        
        st.divider()
        
        # === PERINGATAN ===
        st.subheader("⚠️ Peringatan")
        
        # Fakta tidak pernah diakses > 30 hari
        old_unused = [f for f in fakta if f[7] is None or (datetime.datetime.now() - datetime.datetime.strptime(f[7], "%Y-%m-%d %H:%M:%S")).days > 30]
        if old_unused:
            with st.expander(f"💤 {len(old_unused)} fakta tidak pernah diakses > 30 hari"):
                for f in old_unused:
                    st.write(f"- [#{f[0]}] {f[2][:100]}")
        
        # Fakta low importance banyak
        if low_importance > len(fakta) * 0.3:
            st.warning(f"⚠️ {low_importance} fakta memiliki importance rendah. Pertimbangkan untuk membersihkan.")
        
        st.divider()
        
        # === DUPLICATE DETECTION ===
        st.subheader("🔍 Duplicate Detection")
        
        if st.button("🔎 Cari Duplikat (AI Analysis)"):
            with st.spinner("Menganalisis kemiripan fakta..."):
                duplikat = deteksi_duplikat_semantik()
                
                if duplikat:
                    for d in duplikat:
                        st.warning(f"**#{d['id1']}** ↔ **#{d['id2']}**")
                        st.write(f"Alasan: {d['reason']}")
                        st.write(f"Saran: {d['suggestion']}")
                        
                        if st.button(f"Merge #{d['id1']} + #{d['id2']}", key=f"merge_{d['id1']}_{d['id2']}"):
                            f1 = lihat_fakta_by_id(d['id1'])
                            f2 = lihat_fakta_by_id(d['id2'])
                            if f1 and f2:
                                hasil = merge_fakta_dengan_ai([f1, f2])
                                kategori = f1[1]
                                new_importance = max(f1[5], f2[5])
                                simpan_fakta(kategori, hasil, "manual", 1.0, new_importance)
                                hapus_fakta(d['id1'])
                                hapus_fakta(d['id2'])
                                st.success(f"Berhasil merge! Fakta baru tersimpan.")
                                st.rerun()
                        st.divider()
                else:
                    st.success("✅ Tidak ada duplikat terdeteksi!")
        
        st.divider()
        
        # === FAKTA TERURUT IMPORTANCE ===
        st.subheader("📋 Fakta Berdasarkan Importance")
        
        # Sortir
        sort_by = st.selectbox("Urutkan", ["Importance (tinggi ke rendah)", "Akses terbanyak", "Terbaru", "Terlama tidak diakses"])
        
        if sort_by == "Importance (tinggi ke rendah)":
            sorted_facts = sorted(fakta, key=lambda x: x[5], reverse=True)
        elif sort_by == "Akses terbanyak":
            sorted_facts = sorted(fakta, key=lambda x: x[6], reverse=True)
        elif sort_by == "Terbaru":
            sorted_facts = sorted(fakta, key=lambda x: x[8], reverse=True)
        else:
            sorted_facts = sorted(fakta, key=lambda x: x[7] if x[7] else "2000-01-01")
        
        for f in sorted_facts[:30]:  # Maks 30
            importance_bar = "█" * f[5] + "░" * (10 - f[5])
            
            with st.expander(f"⭐ {f[5]}/10 | [#{f[0]}] [{f[1]}] {f[2][:80]}..."):
                st.write(f"**Konten:** {f[2]}")
                st.write(f"**Kategori:** {f[1]}")
                st.write(f"**Importance:** {importance_bar} ({f[5]}/10)")
                st.write(f"**Diakses:** {f[6]} kali")
                st.write(f"**Terakhir diakses:** {f[7] if f[7] else 'Belum pernah'}")
                st.write(f"**Dibuat:** {f[8]}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_score = st.slider("Importance", 1, 10, f[5], key=f"imp_{f[0]}")
                    if new_score != f[5]:
                        if st.button(f"Update #{f[0]}", key=f"upd_{f[0]}"):
                            update_importance(f[0], new_score)
                            st.rerun()
                with col2:
                    if st.button(f"✏️ Edit #{f[0]}", key=f"edit_intel_{f[0]}"):
                        st.session_state[f"edit_intel_{f[0]}"] = True
                with col3:
                    if st.button(f"🗑️ Hapus #{f[0]}", key=f"hapus_intel_{f[0]}"):
                        hapus_fakta(f[0])
                        st.rerun()
                
                if st.session_state.get(f"edit_intel_{f[0]}"):
                    baru = st.text_area("Edit:", value=f[2], key=f"input_intel_{f[0]}")
                    if st.button("Simpan", key=f"save_intel_{f[0]}"):
                        edit_fakta(f[0], baru)
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("UPDATE facts SET source = 'manual', confidence = 1.0 WHERE id = ?", (f[0],))
                        conn.commit()
                        conn.close()
                        st.session_state[f"edit_intel_{f[0]}"] = False
                        st.rerun()
    
    # ===== PENGATURAN =====
    elif menu == "⚙️ Pengaturan":
        st.title("⚙️ Pengaturan")
        
        st.subheader("📊 Status Server")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Model AI:** {MODEL}")
            st.info(f"**Database:** {DB_FILE}")
        with col2:
            st.info(f"**Dokumen:** {DOCUMENTS_FOLDER}/")
            st.info(f"**ChromaDB:** {CHROMA_FOLDER}/")
        
        st.divider()
        
        st.subheader("📤 Ekspor Memory")
        if st.button("Ekspor ke JSON & Markdown"):
            fakta = lihat_semua_fakta()
            if fakta:
                os.makedirs(EXPORT_FOLDER, exist_ok=True)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                
                json_data = [{"id": f[0], "category": f[1], "content": f[2], "source": f[3], "confidence": f[4], "importance": f[5], "access_count": f[6], "last_accessed": f[7], "created_at": f[8]} for f in fakta]
                
                json_path = f"{EXPORT_FOLDER}/memory_{timestamp}.json"
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                
                st.success(f"Ekspor berhasil: {json_path}")
                st.download_button("📥 Download JSON", json.dumps(json_data, indent=2, ensure_ascii=False), f"memory_{timestamp}.json", "application/json")
        
        st.divider()
        
        st.subheader("📥 Impor Memory")
        imported_file = st.file_uploader("Upload file JSON", type=["json"])
        if imported_file and st.button("Impor"):
            try:
                data = json.loads(imported_file.read())
                imported, skipped = 0, 0
                for item in data:
                    content = item.get("content", "")
                    category = item.get("category", "umum")
                    existing = cek_fakta_duplikat(content)
                    if existing:
                        skipped += 1
                    else:
                        simpan_fakta(category, content, item.get("source", "imported"), item.get("confidence", 1.0))
                        imported += 1
                st.success(f"Impor: {imported} baru, {skipped} duplikat")
            except:
                st.error("File tidak valid!")
        
        st.divider()
        st.caption(f"🤖 {NAMA_AI} v4.0 — Server Pribadi | Streamlit + Ollama")

# ========== FOOTER ==========
st.sidebar.divider()
st.sidebar.caption(f"🤖 {NAMA_AI} v4.0 — Server Pribadi")
st.sidebar.caption("Jalankan dengan: streamlit run saki_server.py")