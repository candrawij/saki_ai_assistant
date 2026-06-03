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
import re

# ========== TAMBAHAN V4.5.1: LOGGING & UTILITIES ==========
import logging
import logging.handlers
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Tuple, List, Generator

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

# Setup logging
def setup_logging():
    """Setup logging configuration - hanya dipanggil sekali"""
    logger = logging.getLogger("saki")
    
    # Cegah duplikat handler
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # File handler (DEBUG, rotating)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "saki.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "saki_errors.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_format)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    
    # Jangan propagate ke root logger (hindari duplikat dari Streamlit)
    logger.propagate = False
    
    return logger

# Inisialisasi logger
logger = setup_logging()
logger.info("Logging system initialized")

# ========== KONSTANTA (Magic Numbers) ==========
# Text processing
TEXT_CHUNK_SIZE = 1000
SUMMARY_MAX_LENGTH = 4000
MAX_FACTS_DISPLAY = 30

# Thresholds
MIN_CONFIDENCE_THRESHOLD = 0.5
MIN_IMPORTANCE_FOR_TRACKING = 5
DAYS_UNUSED_WARNING = 30

# Limits
MAX_CONTENT_LENGTH = 10000
MIN_CONTENT_LENGTH = 3
MAX_CATEGORY_LENGTH = 50

# ========== DB CONTEXT MANAGER ==========
@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager untuk database connections - handle open/close otomatis"""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {str(e)}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()

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
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO conversations (role, content) VALUES (?, ?)", (role, content))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to save chat: {str(e)}", exc_info=True)
        return False

# ========== INPUT VALIDATION ==========
def validate_fakta(category: str, content: str, confidence: float, importance: int) -> Tuple[bool, Optional[str]]:
    """Validate fakta inputs. Return (is_valid, error_message)"""
    
    if not isinstance(content, str):
        return False, "Content harus berupa string"
    
    content = content.strip()
    if not content:
        return False, "Content tidak boleh kosong"
    
    if len(content) > MAX_CONTENT_LENGTH:
        return False, f"Content terlalu panjang (max {MAX_CONTENT_LENGTH} karakter)"
    
    if len(content) < MIN_CONTENT_LENGTH:
        return False, f"Content terlalu pendek (min {MIN_CONTENT_LENGTH} karakter)"
    
    category = (category or "").strip() or "umum"
    if len(category) > MAX_CATEGORY_LENGTH:
        return False, f"Kategori terlalu panjang (max {MAX_CATEGORY_LENGTH} karakter)"
    
    if not isinstance(confidence, (int, float)):
        return False, "Confidence harus berupa angka"
    
    if not 0.0 <= confidence <= 1.0:
        return False, "Confidence harus antara 0.0 - 1.0"
    
    if not isinstance(importance, int):
        return False, "Importance harus berupa integer"
    
    if not 1 <= importance <= 10:
        return False, "Importance harus antara 1 - 10"
    
    return True, None

def simpan_fakta(category: str, content: str, source: str = "manual", 
                 confidence: float = 1.0, importance: int = 5) -> Tuple[bool, Optional[str]]:
    """Simpan fakta baru dengan validasi. Return (success, error_message)"""
    
    # Validate
    is_valid, error = validate_fakta(category, content, confidence, importance)
    if not is_valid:
        logger.warning(f"Validation failed: {error} | content='{(content or '')[:50]}...'")
        return False, error
    
    # Sanitize
    content = content.strip()[:MAX_CONTENT_LENGTH]
    category = (category or "").strip() or "umum"
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO facts (category, content, source, confidence, importance) VALUES (?, ?, ?, ?, ?)",
                (category, content, source, confidence, importance)
            )
            conn.commit()
            logger.info(f"Saved fact: [{category}] {content[:50]}... (imp={importance}, src={source})")
            return True, None
    except Exception as e:
        logger.error(f"Failed to save fact: {str(e)}", exc_info=True)
        return False, f"Gagal menyimpan: {type(e).__name__}"

def lihat_semua_fakta():
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, category, content, source, confidence, importance, access_count, last_accessed, created_at FROM facts WHERE deleted = 0 ORDER BY importance DESC, id DESC")
            results = c.fetchall()
        return results
    except Exception as e:
        logger.error(f"Failed to fetch facts: {str(e)}", exc_info=True)
        return []

def lihat_fakta_by_id(fact_id):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, category, content, source, confidence, importance, access_count, last_accessed, created_at FROM facts WHERE id = ? AND deleted = 0", (fact_id,))
            result = c.fetchone()
        return result
    except Exception as e:
        logger.error(f"Failed to fetch fact by id {fact_id}: {str(e)}", exc_info=True)
        return None

def edit_fakta(fact_id, content):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("UPDATE facts SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (content, fact_id))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to edit fact {fact_id}: {str(e)}", exc_info=True)
        return False

def hapus_fakta(fact_id):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("UPDATE facts SET deleted = 1 WHERE id = ?", (fact_id,))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to delete fact {fact_id}: {str(e)}", exc_info=True)
        return False

def cek_fakta_duplikat(content):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, content FROM facts WHERE deleted = 0")
            semua = c.fetchall()
        for fakta in semua:
            if content.lower() in (fakta[1] or "").lower() or (fakta[1] or "").lower() in content.lower():
                return fakta[0]
        return None
    except Exception as e:
        logger.error(f"Failed to check duplicate facts: {str(e)}", exc_info=True)
        return None

def lihat_semua_dokumen():
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, filename, file_type, summary, created_at FROM documents ORDER BY created_at DESC")
            results = c.fetchall()
        return results
    except Exception as e:
        logger.error(f"Failed to fetch documents: {str(e)}", exc_info=True)
        return []

def lihat_dokumen_by_id(doc_id):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, filename, filepath, file_type, summary, full_text, created_at FROM documents WHERE id = ?", (doc_id,))
            result = c.fetchone()
        return result
    except Exception as e:
        logger.error(f"Failed to fetch document {doc_id}: {str(e)}", exc_info=True)
        return None

def hapus_dokumen(doc_id):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to delete document {doc_id}: {str(e)}", exc_info=True)
        return False

def simpan_dokumen(filename, filepath, file_type, full_text, summary):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO documents (filename, filepath, file_type, full_text, summary) VALUES (?, ?, ?, ?, ?)",
                      (filename, filepath, file_type, full_text, summary))
            doc_id = c.lastrowid
            conn.commit()
        return doc_id
    except Exception as e:
        logger.error(f"Failed to save document: {str(e)}", exc_info=True)
        return None

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
        logger.error(f"tambah_ke_chroma failed for doc {doc_id}: {type(e).__name__}: {str(e)}", exc_info=True)
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
    except Exception as e:
        logger.error(f"cari_dokumen_semantik failed: {type(e).__name__}: {str(e)}", exc_info=True)
        return []

# ========== EKSTRAKSI FILE ==========
def ekstrak_teks_dari_pdf(filepath):
    try:
        reader = PdfReader(filepath)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])
        if not text.strip():
            logger.warning(f"PDF kosong: {filepath}")
            return None
        logger.info(f"Berhasil ekstrak PDF: {os.path.basename(filepath)} ({len(text)} chars)")
        return text.strip()
    except FileNotFoundError:
        logger.error(f"PDF tidak ditemukan: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Gagal ekstrak PDF {os.path.basename(filepath)}: {type(e).__name__}: {str(e)}", exc_info=True)
        return None

def ekstrak_teks_dari_docx(filepath):
    try:
        doc = Document(filepath)
        text = "\n".join([para.text for para in doc.paragraphs])
        if not text.strip():
            logger.warning(f"DOCX kosong: {filepath}")
            return None
        logger.info(f"Berhasil ekstrak DOCX: {os.path.basename(filepath)} ({len(text)} chars)")
        return text.strip()
    except FileNotFoundError:
        logger.error(f"DOCX tidak ditemukan: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Gagal ekstrak DOCX {os.path.basename(filepath)}: {type(e).__name__}: {str(e)}", exc_info=True)
        return None

def ekstrak_teks_dari_txt(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        if not text.strip():
            logger.warning(f"File kosong: {filepath}")
            return None
        logger.info(f"Berhasil baca file: {os.path.basename(filepath)} ({len(text)} chars)")
        return text.strip()
    except UnicodeDecodeError:
        try:
            with open(filepath, "r", encoding="latin-1") as f:
                text = f.read()
            logger.warning(f"File dibaca dengan encoding latin-1: {filepath}")
            return text.strip()
        except Exception as e:
            logger.error(f"Gagal baca file dengan encoding alternatif: {str(e)}", exc_info=True)
            return None
    except FileNotFoundError:
        logger.error(f"File tidak ditemukan: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Gagal baca file {os.path.basename(filepath)}: {type(e).__name__}: {str(e)}", exc_info=True)
        return None

def proses_upload(uploaded_file) -> Tuple[Optional[int], str]:
    """Proses upload file dengan try-finally untuk cleanup"""
    tmp_path = None
    try:
        filename = uploaded_file.name
        ext = os.path.splitext(filename)[1].lower()
        
        # Validasi ekstensi
        if ext not in [".pdf", ".docx", ".txt", ".md"]:
            return None, f"Format {ext} tidak didukung. Gunakan PDF, DOCX, TXT, atau MD."
        
        # Simpan ke temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        
        logger.info(f"Processing upload: {filename}")
        
        # Ekstrak teks
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
            return None, f"Format {ext} tidak didukung."
        
        if not teks:
            logger.warning(f"Ekstraksi teks kosong: {filename}")
            return None, "Gagal mengekstrak teks. File mungkin kosong atau corrupt."
        
        # Ringkas (batasi panjang)
        teks_ringkas = teks[:SUMMARY_MAX_LENGTH]
        prompt = f"Ringkas dokumen berikut:\n\nJudul: {filename}\n\n{teks_ringkas}"
        response = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])
        ringkasan = response["message"]["content"]
        
        # Simpan ke folder documents
        os.makedirs(DOCUMENTS_FOLDER, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_filename = f"{timestamp}_{filename}"
        saved_path = os.path.join(DOCUMENTS_FOLDER, saved_filename)
        
        # Copy dari temp ke permanent
        import shutil
        shutil.copy2(tmp_path, saved_path)
        
        # Simpan ke database
        doc_id = simpan_dokumen(filename, saved_path, file_type, teks, ringkasan)
        if doc_id:
            tambah_ke_chroma(doc_id, teks, filename)
        
        logger.info(f"Upload berhasil: {filename} -> doc_id={doc_id}")
        return doc_id, ringkasan
    except Exception as e:
        logger.error(f"Error processing upload: {type(e).__name__}: {str(e)}", exc_info=True)
        return None, f"Gagal memproses file: {type(e).__name__}"
    finally:
        # SELALU cleanup temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                logger.debug(f"Temp file cleaned: {tmp_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {tmp_path}: {str(e)}")

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
    except Exception as e:
        logger.error(f"Auto-extract failed: {type(e).__name__}: {str(e)}", exc_info=True)
    return None

# ========== FUNGSI AI ==========
# ========== FUNGSI MEMORY INTELLIGENCE (V4.5) ==========
def track_access(fact_id):
    """Catat akses ke fakta: increment counter + update timestamp."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE facts SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                (fact_id,)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to track access for fact {fact_id}: {str(e)}", exc_info=True)

def update_importance(fact_id, importance):
    """Update importance score (1-10)."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("UPDATE facts SET importance = ? WHERE id = ?", (importance, fact_id))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to update importance for fact {fact_id}: {str(e)}", exc_info=True)

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
    except Exception as e:
        logger.error(f"auto_rate_importance failed: {type(e).__name__}: {str(e)}", exc_info=True)
        return 5  # Default

def deteksi_duplikat_semantik():
    """Gunakan AI untuk mendeteksi fakta yang kemungkinan duplikat.

    Mengembalikan list pasangan {"id1":..., "id2":..., "reason":..., "suggestion":...}.
    Fungsi ini menangani respons AI yang tidak valid dengan beberapa fallback parsing.
    """
    fakta = lihat_semua_fakta()
    if len(fakta) < 2:
        return []

    # Bangun prompt dengan bullet list yang ringkas
    fakta_list = "\n".join([f"- [#{f[0]}] [{f[1]}] {f[2]}" for f in fakta])

    prompt = f"""Analisis daftar fakta berikut dan kembalikan PAIR fakta yang kemungkinan duplikat
atau topik sama. Jawab berupa JSON array seperti:
[{{"id1": 1, "id2": 2, "reason": "alasan", "suggestion": "saran merge"}}, ...]

Hanya tampilkan pasangan yang memang sangat mirip. Jika tidak ada, jawab [].

Fakta:
{fakta_list}
"""

    try:
        response = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": "Jawab HANYA JSON array."},
            {"role": "user", "content": prompt}
        ])
        raw = response["message"]["content"].strip()

        # Hapus code fences jika ada
        if raw.startswith("```"):
            try:
                raw = raw.split("\n", 1)[1].rstrip("```")
            except Exception:
                raw = raw.strip('`')

        # Try direct JSON parse
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass

        # Fallback: try to extract first JSON array substring
        m = re.search(r"(\[.*\])", raw, re.S)
        if m:
            try:
                parsed = json.loads(m.group(1))
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                logger.debug("deteksi_duplikat_semantik: failed to parse extracted JSON array", exc_info=True)

        # Last resort: attempt to extract simple pairs with regex
        pairs = []
        for match in re.finditer(r"#(\d+).*?#(\d+)", raw):
            try:
                id1 = int(match.group(1))
                id2 = int(match.group(2))
                pairs.append({"id1": id1, "id2": id2, "reason": "auto-detected", "suggestion": "Merge jika sama"})
            except Exception:
                continue

        if pairs:
            return pairs

        logger.info("deteksi_duplikat_semantik: no duplicates found or unable to parse AI response")
        return []
    except Exception as e:
        logger.error(f"deteksi_duplikat_semantik failed: {type(e).__name__}: {str(e)}", exc_info=True)
        return []

def merge_fakta_dengan_ai(fakta_list):
    """Gabungkan beberapa fakta dengan AI."""
    if not fakta_list:
        return "Tidak ada fakta untuk digabung."

    fakta_text = "\n".join([f"- {f[2]}" for f in fakta_list])
    logger.info(f"Merging {len(fakta_list)} facts: {[f[0] for f in fakta_list]}")

    prompt = f"""Gabungkan fakta-fakta berikut menjadi satu fakta yang padat dan koheren.
Jangan ada informasi yang hilang. Hilangkan pengulangan.
Output hanya fakta gabungannya saja, tanpa penjelasan.

{fakta_text}

Hasil gabungan:"""
    
    try:
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        hasil = response["message"]["content"].strip()
        logger.info(f"Merge result: {hasil[:100]}...")
        return hasil
    except Exception as e:
        logger.error(f"Merge failed: {type(e).__name__}: {str(e)}", exc_info=True)
        return f"[Gagal menggabungkan: {type(e).__name__}]"

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
    # Startup logging — hanya sekali
    if "startup_logged" not in st.session_state:
        st.session_state.startup_logged = False
    
    if not st.session_state.startup_logged:
        logger.info("=" * 50)
        logger.info(f"Saki v4.5.1 starting...")
        logger.info(f"Model: {MODEL}")
        logger.info(f"Database: {DB_FILE}")
        logger.info(f"Documents: {DOCUMENTS_FOLDER}")
        logger.info("=" * 50)
        st.session_state.startup_logged = True
    
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
                        success, error = simpan_fakta(hasil["category"], hasil["fact"], "auto", hasil["confidence"], importance)
                        if not success:
                            logger.warning(f"Auto-save failed: {error}")
            
            st.rerun()
    
    # ===== RINGKASAN =====
    elif menu == "📝 Ringkasan":
        st.title("📝 Ringkasan Teks")
        
        tab1, tab2 = st.tabs(["✏️ Paste Teks", "📤 Upload File"])
        
        with tab1:
            st.caption("Paste teks panjang di sini. Tidak ada batasan panjang.")
            
            # Gunakan text_area dengan height besar
            teks = st.text_area(
                "Masukkan teks yang ingin diringkas:",
                height=350,
                placeholder="Paste teks Anda di sini...",
                key="ringkasan_text"
            )
            
            col1, col2 = st.columns([1, 3])
            with col1:
                ringkas_btn = st.button("🔍 Ringkas Teks", type="primary", use_container_width=True)
            
            if ringkas_btn:
                if not teks or not teks.strip():
                    st.error("⚠️ Teks tidak boleh kosong.")
                else:
                    with st.spinner(f"⏳ {NAMA_AI} sedang meringkas... ({len(teks)} karakter)"):
                        try:
                            hasil = ringkas_teks(teks)
                            st.success("✅ Ringkasan berhasil!")
                            st.markdown("### 📋 Hasil Ringkasan")
                            st.markdown(hasil)
                            
                            # Info
                            with st.expander("📊 Info Ringkasan"):
                                st.write(f"- **Panjang teks asli:** {len(teks)} karakter")
                                st.write(f"- **Panjang ringkasan:** {len(hasil)} karakter")
                                st.write(f"- **Rasio:** {len(hasil)/max(len(teks),1)*100:.1f}%")
                            
                            # Simpan otomatis
                            os.makedirs(SAVE_FOLDER, exist_ok=True)
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            filepath = f"{SAVE_FOLDER}/ringkasan_{timestamp}.txt"
                            with open(filepath, "w", encoding="utf-8") as f:
                                f.write(f"=== RINGKASAN ===\n{hasil}\n\n=== TEKS ASLI ===\n{teks[:1000]}...")
                            st.success(f"💾 Tersimpan: `{filepath}`")
                            
                            logger.info(f"Summarized text: {len(teks)} -> {len(hasil)} chars")
                            
                        except Exception as e:
                            logger.error(f"Summarization failed: {str(e)}", exc_info=True)
                            st.error(f"❌ Gagal meringkas: {type(e).__name__}")
            
            # Tampilkan info panjang teks
            if teks:
                st.caption(f"📊 {len(teks)} karakter | ~{len(teks.split())} kata")
        
        with tab2:
            st.caption("Upload file untuk diringkas otomatis.")
            uploaded = st.file_uploader("Pilih file", type=["pdf", "docx", "txt", "md"], key="ringkasan_upload")
            if uploaded and st.button("📤 Upload & Ringkas", key="ringkasan_upload_btn"):
                with st.spinner("⏳ Memproses file..."):
                    doc_id, ringkasan = proses_upload(uploaded)
                    if doc_id:
                        st.success(f"✅ Upload berhasil! ID Dokumen: #{doc_id}")
                        st.markdown("### 📋 Ringkasan Otomatis")
                        st.markdown(ringkasan)
                    else:
                        st.error(f"❌ Gagal: {ringkasan}")
    
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
        
        # === CATAT FAKTA BARU ===
        st.subheader("✍️ Catat Fakta Baru")
        with st.form("form_catat_fakta", clear_on_submit=True):
            kategori = st.selectbox("Kategori", ["proyek", "preferensi", "kontak", "jadwal", "akun", "skill", "pekerjaan", "pendidikan", "umum"])
            fakta_text = st.text_area("Fakta:", placeholder="Ketik fakta yang ingin dicatat...", height=100)
            submitted = st.form_submit_button("📝 Catat Fakta", use_container_width=True)
            
            if submitted:
                if not fakta_text or not fakta_text.strip():
                    st.error("⚠️ Fakta tidak boleh kosong.")
                else:
                    with st.spinner(f"⏳ {NAMA_AI} menilai importance..."):
                        try:
                            # Hitung importance otomatis
                            importance = auto_rate_importance(fakta_text, kategori)
                            # Simpan
                            success, error = simpan_fakta(kategori, fakta_text, "manual", 1.0, importance)
                            if success:
                                st.success(f"✅ Fakta berhasil dicatat! (Importance: {importance}/10)")
                                logger.info(f"Manual fact recorded: [{kategori}] {fakta_text[:50]}... (imp={importance})")
                            else:
                                st.error(f"❌ Gagal mencatat: {error}")
                                logger.error(f"Failed to record manual fact: {error}")
                        except Exception as e:
                            logger.error(f"Error recording manual fact: {type(e).__name__}: {str(e)}", exc_info=True)
                            st.error(f"❌ Error: {type(e).__name__}")
        
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
                        try:
                            with get_db() as conn:
                                c = conn.cursor()
                                c.execute("UPDATE facts SET source = 'manual', confidence = 1.0 WHERE id = ?", (f[0],))
                                conn.commit()
                        except Exception as e:
                            logger.error(f"Failed to update metadata for fact {f[0]}: {str(e)}", exc_info=True)
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
                            except Exception as e:
                                logger.error(f"Failed cleaning chroma entries for doc {d[0]}: {type(e).__name__}: {str(e)}", exc_info=True)
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
        
        # 1. Fakta yang BELUM PERNAH diakses (baru)
        never_accessed = [f for f in fakta if f[7] is None]
        if never_accessed:
            with st.expander(f"🆕 {len(never_accessed)} fakta baru (belum pernah diakses)"):
                st.caption("Fakta-fakta ini baru dibuat dan belum pernah digunakan dalam percakapan.")
                for f in never_accessed[:10]:
                    st.write(f"- [#{f[0]}] {f[2][:100]}")
        
        # 2. Fakta yang SUDAH LAMA tidak diakses (> 30 hari)
        now = datetime.datetime.now()
        old_unused = []
        for f in fakta:
            if f[7] is not None:
                try:
                    last_access = datetime.datetime.strptime(f[7], "%Y-%m-%d %H:%M:%S")
                    days_since = (now - last_access).days
                    if days_since > DAYS_UNUSED_WARNING:
                        old_unused.append((f, days_since))
                except Exception:
                    pass
        
        if old_unused:
            with st.expander(f"💤 {len(old_unused)} fakta tidak diakses > {DAYS_UNUSED_WARNING} hari"):
                for f, days in old_unused[:10]:
                    st.write(f"- [#{f[0]}] {f[2][:100]} ({days} hari)")
        
        # 3. Fakta dengan importance rendah
        low_importance = [f for f in fakta if f[5] <= 3]
        if len(low_importance) > len(fakta) * 0.3 and len(fakta) > 5:
            st.warning(f"⚠️ {len(low_importance)} fakta memiliki importance rendah (≤3). Pertimbangkan untuk membersihkan.")
        
        st.divider()
        
        # === DUPLICATE DETECTION ===
        st.subheader("🔍 Duplicate Detection")
        
        # Simpan hasil deteksi di session state agar tidak hilang saat re-run
        if "duplicate_results" not in st.session_state:
            st.session_state.duplicate_results = None
        if "merge_message" not in st.session_state:
            st.session_state.merge_message = None
        
        if st.button("🔎 Cari Duplikat (AI Analysis)"):
            with st.spinner("Menganalisis kemiripan fakta..."):
                st.session_state.duplicate_results = deteksi_duplikat_semantik()
                st.session_state.merge_message = None
            st.rerun()
        
        # Tampilkan hasil deteksi dari session state
        if st.session_state.duplicate_results is not None:
            duplikat = st.session_state.duplicate_results
            
            if not duplikat:
                st.success("✅ Tidak ada duplikat terdeteksi!")
            else:
                st.info(f"Ditemukan {len(duplikat)} potensi duplikat:")
                
                for i, d in enumerate(duplikat):
                    with st.container():
                        st.warning(f"**#{d['id1']}** ↔ **#{d['id2']}**")
                        st.write(f"Alasan: {d.get('reason', 'Tidak ada alasan')}")
                        st.write(f"Saran: {d.get('suggestion', 'Merge jika sama')}")
                        
                        # Tombol merge dalam form agar tidak conflict
                        with st.form(key=f"merge_form_{d['id1']}_{d['id2']}_{i}"):
                            submitted = st.form_submit_button(
                                f"🔗 Merge #{d['id1']} + #{d['id2']}",
                                use_container_width=True
                            )
                            
                            if submitted:
                                logger.info(f"User clicked merge: {d['id1']} + {d['id2']}")
                                
                                f1 = lihat_fakta_by_id(d['id1'])
                                f2 = lihat_fakta_by_id(d['id2'])
                                
                                if not f1:
                                    st.session_state.merge_message = f"❌ Fakta #{d['id1']} tidak ditemukan."
                                    logger.error(f"Merge failed: fact {d['id1']} not found")
                                elif not f2:
                                    st.session_state.merge_message = f"❌ Fakta #{d['id2']} tidak ditemukan."
                                    logger.error(f"Merge failed: fact {d['id2']} not found")
                                else:
                                    logger.info(f"Merging: [{f1[1]}] {f1[2][:50]} + [{f2[1]}] {f2[2][:50]}")
                                    
                                    hasil = merge_fakta_dengan_ai([f1, f2])
                                    
                                    if isinstance(hasil, str) and hasil.startswith("[Gagal"):
                                        st.session_state.merge_message = f"❌ {hasil}"
                                        logger.error(f"Merge AI failed: {hasil}")
                                    else:
                                        kategori = f1[1]
                                        # Akses index yang aman
                                        imp1 = f1[5] if len(f1) > 5 else 5
                                        imp2 = f2[5] if len(f2) > 5 else 5
                                        new_importance = max(imp1, imp2)
                                        
                                        logger.info(f"Saving merged fact: [{kategori}] {hasil[:50]}... (imp={new_importance})")
                                        
                                        success, error = simpan_fakta(kategori, hasil, "manual", 1.0, new_importance)
                                        
                                        if success:
                                            hapus_fakta(d['id1'])
                                            hapus_fakta(d['id2'])
                                            logger.info(f"Merge complete: {d['id1']} + {d['id2']} -> new fact saved")
                                            st.session_state.merge_message = f"✅ Berhasil merge! Fakta #{d['id1']} + #{d['id2']} digabung."
                                            # Reset hasil deteksi
                                            st.session_state.duplicate_results = None
                                        else:
                                            logger.error(f"Merge save failed: {error}")
                                            st.session_state.merge_message = f"❌ Gagal menyimpan: {error}"
                                
                                st.rerun()
                        
                        st.divider()
        
        # Tampilkan pesan merge
        if st.session_state.merge_message:
            if "✅" in st.session_state.merge_message:
                st.success(st.session_state.merge_message)
            else:
                st.error(st.session_state.merge_message)
            # Clear setelah ditampilkan
            if st.button("OK"):
                st.session_state.merge_message = None
                st.rerun()

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
                        try:
                            with get_db() as conn:
                                c = conn.cursor()
                                c.execute("UPDATE facts SET source = 'manual', confidence = 1.0 WHERE id = ?", (f[0],))
                                conn.commit()
                        except Exception as e:
                            logger.error(f"Failed to update metadata for fact {f[0]}: {str(e)}", exc_info=True)
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
                        # Rate importance automatically for imported items
                        try:
                            importance = auto_rate_importance(content, category)
                        except Exception as e:
                            logger.error(f"Failed to auto-rate importance for import: {str(e)}", exc_info=True)
                            importance = 5

                        success, error = simpan_fakta(category, content, item.get("source", "imported"), item.get("confidence", 1.0), importance)
                        if not success:
                            skipped += 1
                            logger.warning(f"Imported fact skipped (save failed): {error}")
                        else:
                            imported += 1
                st.success(f"Impor: {imported} baru, {skipped} duplikat")
            except Exception as e:
                logger.error(f"Failed to import memory file: {str(e)}", exc_info=True)
                st.error("File tidak valid!")
        
        st.divider()
        st.caption(f"🤖 {NAMA_AI} v4.0 — Server Pribadi | Streamlit + Ollama")

# ========== FOOTER ==========
st.sidebar.divider()
st.sidebar.caption(f"🤖 {NAMA_AI} v4.0 — Server Pribadi")
st.sidebar.caption("Jalankan dengan: streamlit run saki_server.py")