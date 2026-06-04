"""
Saki Database Module
Semua fungsi database: SQLite, ChromaDB, context manager, validasi
"""

import sqlite3
import json
import os
import datetime
import logging
from contextlib import contextmanager
from typing import Optional, Tuple, List, Generator
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger("saki")

# ========== KONFIGURASI DATABASE ==========
from dotenv import load_dotenv

load_dotenv()


# Base folder untuk semua data
DATA_FOLDER = Path(os.getenv("DATA_FOLDER", "data"))

# Pastikan folder data ada
DATA_FOLDER.mkdir(exist_ok=True)

DB_FILE = str(DATA_FOLDER / os.getenv("DB_NAME", "saki_memory.db"))
CHROMA_FOLDER = str(DATA_FOLDER / os.getenv("CHROMA_FOLDER", "chroma_db"))
DOCUMENTS_FOLDER = str(DATA_FOLDER / os.getenv("DOCUMENTS_FOLDER", "documents"))
EXPORT_FOLDER = str(DATA_FOLDER / os.getenv("EXPORT_FOLDER", "exports"))
SAVE_FOLDER = str(DATA_FOLDER / os.getenv("SAVE_FOLDER", "ringkasan"))
LOGS_FOLDER = Path(os.getenv("LOGS_FOLDER", "logs"))


# ========== KONSTANTA ==========
MAX_CONTENT_LENGTH = 10000
MIN_CONTENT_LENGTH = 3
MAX_CATEGORY_LENGTH = 50

# ========== DB CONTEXT MANAGER ==========
@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager untuk database connections"""
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

# ========== INISIALISASI ==========
def init_db():
    """Inisialisasi database. Auto-migration untuk kolom baru."""
    try:
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
        
        c.execute('''CREATE TABLE IF NOT EXISTS reflections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            source_facts TEXT,
            category TEXT DEFAULT 'insight',
            importance INTEGER DEFAULT 9,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Auto-migration
        c.execute("PRAGMA table_info(facts)")
        columns = [col[1] for col in c.fetchall()]
        
        migrations = {
            'source': "TEXT DEFAULT 'manual'",
            'confidence': "REAL DEFAULT 1.0",
            'importance': "INTEGER DEFAULT 5",
            'access_count': "INTEGER DEFAULT 0",
            'last_accessed': "TIMESTAMP DEFAULT NULL",
            'reflected': "INTEGER DEFAULT 0"
        }
        
        for col_name, col_def in migrations.items():
            if col_name not in columns:
                c.execute(f"ALTER TABLE facts ADD COLUMN {col_name} {col_def}")
                logger.info(f"Migration: added column '{col_name}' to facts")
        
        conn.commit()
        conn.close()
        logger.debug("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
        raise

# ========== VALIDASI ==========
def validate_fakta(category: str, content: str, confidence: float, importance: int) -> Tuple[bool, Optional[str]]:
    """Validate fakta inputs."""
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
    
    if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
        return False, "Confidence harus antara 0.0 - 1.0"
    if not isinstance(importance, int) or not 1 <= importance <= 10:
        return False, "Importance harus antara 1 - 10"
    
    return True, None

# ========== FACTS CRUD ==========
def simpan_chat(role: str, content: str) -> bool:
    """Simpan pesan chat ke database."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO conversations (role, content) VALUES (?, ?)", (role, content))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to save chat: {str(e)}", exc_info=True)
        return False

def simpan_fakta(category: str, content: str, source: str = "manual",
                 confidence: float = 1.0, importance: int = 5) -> Tuple[bool, Optional[str]]:
    """Simpan fakta baru dengan validasi."""
    is_valid, error = validate_fakta(category, content, confidence, importance)
    if not is_valid:
        logger.warning(f"Validation failed: {error}")
        return False, error
    
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
            logger.info(f"Saved fact: [{category}] {content[:50]}... (imp={importance})")
            return True, None
    except Exception as e:
        logger.error(f"Failed to save fact: {str(e)}", exc_info=True)
        return False, f"Gagal menyimpan: {type(e).__name__}"

def lihat_semua_fakta() -> List[Tuple]:
    """Ambil semua fakta yang tidak dihapus."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, category, content, source, confidence, importance, access_count, last_accessed, created_at FROM facts WHERE deleted = 0 ORDER BY importance DESC, id DESC")
            return c.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch facts: {str(e)}", exc_info=True)
        return []

def lihat_fakta_by_id(fact_id: int) -> Optional[Tuple]:
    """Ambil satu fakta by ID."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, category, content, source, confidence, importance, access_count, last_accessed, created_at FROM facts WHERE id = ? AND deleted = 0", (fact_id,))
            return c.fetchone()
    except Exception as e:
        logger.error(f"Failed to fetch fact {fact_id}: {str(e)}", exc_info=True)
        return None

def edit_fakta(fact_id: int, content: str) -> bool:
    """Edit konten fakta."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("UPDATE facts SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (content, fact_id))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to edit fact {fact_id}: {str(e)}", exc_info=True)
        return False

def hapus_fakta(fact_id: int) -> bool:
    """Soft delete fakta."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("UPDATE facts SET deleted = 1 WHERE id = ?", (fact_id,))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to delete fact {fact_id}: {str(e)}", exc_info=True)
        return False

def cek_fakta_duplikat(content: str) -> Optional[int]:
    """Cek apakah konten fakta sudah ada."""
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
        logger.error(f"Failed to check duplicates: {str(e)}", exc_info=True)
        return None

def track_access(fact_id: int):
    """Catat akses ke fakta."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("UPDATE facts SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP WHERE id = ?", (fact_id,))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to track access for fact {fact_id}: {str(e)}", exc_info=True)

def update_importance(fact_id: int, importance: int):
    """Update importance score."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("UPDATE facts SET importance = ? WHERE id = ?", (importance, fact_id))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to update importance for fact {fact_id}: {str(e)}", exc_info=True)

# ========== REFLECTIONS CRUD (V5) ==========
def simpan_reflection(title: str, content: str, source_facts: List[int], category: str = "insight", importance: int = 9) -> Optional[int]:
    """Simpan hasil reflection."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO reflections (title, content, source_facts, category, importance) VALUES (?, ?, ?, ?, ?)",
                (title, content, json.dumps(source_facts), category, importance)
            )
            reflection_id = c.lastrowid
            conn.commit()
            logger.info(f"Saved reflection: [{category}] {title}")
            return reflection_id
    except Exception as e:
        logger.error(f"Failed to save reflection: {str(e)}", exc_info=True)
        return None

def lihat_semua_reflections() -> List[Tuple]:
    """Ambil semua reflections."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, title, content, source_facts, category, importance, created_at FROM reflections ORDER BY created_at DESC")
            return c.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch reflections: {str(e)}", exc_info=True)
        return []

def lihat_reflection_by_id(reflection_id: int) -> Optional[Tuple]:
    """Ambil satu reflection by ID."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, title, content, source_facts, category, importance, created_at FROM reflections WHERE id = ?", (reflection_id,))
            return c.fetchone()
    except Exception as e:
        logger.error(f"Failed to fetch reflection {reflection_id}: {str(e)}", exc_info=True)
        return None

def hapus_reflection(reflection_id: int) -> bool:
    """Hapus reflection."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM reflections WHERE id = ?", (reflection_id,))
            conn.commit()
        logger.info(f"Deleted reflection #{reflection_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete reflection {reflection_id}: {str(e)}", exc_info=True)
        return False

def tandai_fakta_reflected(fact_ids: List[int]) -> bool:
    """Tandai fakta sebagai sudah di-reflect."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.executemany("UPDATE facts SET reflected = 1 WHERE id = ?", [(fid,) for fid in fact_ids])
            conn.commit()
        logger.info(f"Marked {len(fact_ids)} facts as reflected")
        return True
    except Exception as e:
        logger.error(f"Failed to mark facts as reflected: {str(e)}", exc_info=True)
        return False

def ambil_fakta_belum_reflected() -> List[Tuple]:
    """Ambil fakta yang belum di-reflect."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, category, content FROM facts WHERE deleted = 0 AND reflected = 0 ORDER BY id")
            return c.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch unreflected facts: {str(e)}", exc_info=True)
        return []

def get_reflection_stats() -> dict:
    """Statistik reflection."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM reflections")
            total = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM facts WHERE deleted = 0 AND reflected = 0")
            unreflected = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM facts WHERE deleted = 0 AND reflected = 1")
            reflected = c.fetchone()[0]
        return {"total_reflections": total, "unreflected_facts": unreflected, "reflected_facts": reflected}
    except Exception as e:
        logger.error(f"Failed to get reflection stats: {str(e)}", exc_info=True)
        return {"total_reflections": 0, "unreflected_facts": 0, "reflected_facts": 0}

def edit_reflection(reflection_id: int, title: str, content: str) -> bool:
    """Edit reflection."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("UPDATE reflections SET title = ?, content = ? WHERE id = ?", (title, content, reflection_id))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to edit reflection {reflection_id}: {str(e)}", exc_info=True)
        return False

# ========== DOCUMENTS CRUD ==========
def simpan_dokumen(filename: str, filepath: str, file_type: str, full_text: str, summary: str) -> Optional[int]:
    """Simpan dokumen ke database."""
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

def lihat_semua_dokumen() -> List[Tuple]:
    """Ambil semua dokumen."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, filename, file_type, summary, created_at FROM documents ORDER BY created_at DESC")
            return c.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch documents: {str(e)}", exc_info=True)
        return []

def lihat_dokumen_by_id(doc_id: int) -> Optional[Tuple]:
    """Ambil satu dokumen by ID."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, filename, filepath, file_type, summary, full_text, created_at FROM documents WHERE id = ?", (doc_id,))
            return c.fetchone()
    except Exception as e:
        logger.error(f"Failed to fetch document {doc_id}: {str(e)}", exc_info=True)
        return None

def hapus_dokumen(doc_id: int) -> bool:
    """Hapus dokumen."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to delete document {doc_id}: {str(e)}", exc_info=True)
        return False

def get_facts_for_timeline() -> List[Tuple]:
    """Ambil semua fakta dengan timestamp untuk timeline."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, category, content, created_at FROM facts WHERE deleted = 0 ORDER BY created_at ASC")
            return c.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch timeline facts: {str(e)}", exc_info=True)
        return []

# ========== CHROMA DB ==========
def init_chroma():
    """Inisialisasi ChromaDB."""
    os.makedirs(CHROMA_FOLDER, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_FOLDER)
    ollama_ef = embedding_functions.OllamaEmbeddingFunction(
        url="http://localhost:11434/api/embeddings",
        model_name="nomic-embed-text"
    )
    collection = client.get_or_create_collection(name="documents", embedding_function=ollama_ef)
    return collection

def tambah_ke_chroma(doc_id: int, full_text: str, filename: str) -> bool:
    """Tambahkan dokumen ke ChromaDB."""
    try:
        collection = init_chroma()
        collection.delete(ids=[str(doc_id)])
        chunks = [full_text[i:i+1000] for i in range(0, len(full_text), 1000)]
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            collection.add(documents=[chunk], metadatas=[{"doc_id": doc_id, "filename": filename, "chunk": i}], ids=[chunk_id])
        return True
    except Exception as e:
        logger.error(f"ChromaDB add failed for doc {doc_id}: {str(e)}", exc_info=True)
        return False

def cari_dokumen_semantik(query: str, n_results: int = 3) -> List[Tuple]:
    """Cari dokumen dengan semantic search."""
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
        logger.error(f"Semantic search failed: {str(e)}", exc_info=True)
        return []