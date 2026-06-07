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
from typing import Optional, Tuple, List, Generator, Dict
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
import re

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

        c.execute('''CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            relation_type TEXT DEFAULT 'related',
            confidence REAL DEFAULT 0.7,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES facts(id),
            FOREIGN KEY (target_id) REFERENCES facts(id)
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS proactive_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'active',
            related_fact_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            dismissed_at TIMESTAMP
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
            'reflected': "INTEGER DEFAULT 0",
            'status': "TEXT DEFAULT 'active'"
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
            c.execute("SELECT id, category, content, source, confidence, importance, access_count, last_accessed, created_at, status FROM facts WHERE deleted = 0 ORDER BY importance DESC, id DESC")
            return c.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch facts: {str(e)}", exc_info=True)
        return []

def lihat_fakta_by_id(fact_id: int) -> Optional[Tuple]:
    """Ambil satu fakta by ID."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, category, content, source, confidence, importance, access_count, last_accessed, created_at, status FROM facts WHERE id = ? AND deleted = 0", (fact_id,))
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
    
def get_chat_history_for_timeline() -> List[Tuple]:
    """Ambil ringkasan chat per hari untuk timeline."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT DATE(timestamp) as chat_date, 
                       COUNT(*) as message_count,
                       GROUP_CONCAT(DISTINCT substr(content, 1, 100)) as previews
                FROM conversations 
                GROUP BY DATE(timestamp) 
                ORDER BY chat_date ASC
            """)
            return c.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch chat history for timeline: {str(e)}", exc_info=True)
        return []

def get_reflections_for_timeline() -> List[Tuple]:
    """Ambil insight per bulan untuk timeline."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, title, content, category, created_at 
                FROM reflections 
                ORDER BY created_at ASC
            """)
            return c.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch reflections for timeline: {str(e)}", exc_info=True)
        return []

def get_all_timeline_data() -> Dict:
    """Ambil semua data untuk timeline: fakta, insight, chat."""
    return {
        "facts": get_facts_for_timeline(),
        "reflections": get_reflections_for_timeline(),
        "chats": get_chat_history_for_timeline()
    }

# ========== PROACTIVE ASSISTANT (V8) ==========
def cek_proyek_mengendap(hari: int = 30) -> List[Dict]:
    """Cari fakta proyek yang tidak diakses > N hari."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, content, access_count, last_accessed, created_at
                FROM facts 
                WHERE deleted = 0 AND status = 'active' 
                AND category IN ('proyek', 'pekerjaan', 'pendidikan')
                ORDER BY last_accessed ASC
            """)
            rows = c.fetchall()

            result = []
            now = datetime.datetime.now()
            for r in rows:
                # Hitung days_since di Python
                last = r[3] if r[3] else r[4]  # last_accessed atau created_at
                if last:
                    try:
                        dt = datetime.datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
                        days = (now - dt).days
                        if days > hari:
                            result.append({
                                "id": r[0], "content": r[1], "access_count": r[2],
                                "last_accessed": r[3], "days": days
                            })
                    except:
                        continue
            return result

    except Exception as e:
        logger.error(f"Failed to check stale projects: {str(e)}", exc_info=True)
        return []

def cek_deadline_mendekat(hari: int = 14) -> List[Dict]:
    """Cari fakta jadwal yang mendekat."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, content, created_at
                FROM facts 
                WHERE deleted = 0 AND status = 'active' 
                AND category IN ('jadwal', 'deadline')
            """)
            rows = c.fetchall()
            
            result = []
            for r in rows:
                # Coba ekstrak tanggal dari konten
                content = r[1]
                # Cari pola tanggal (contoh: "30 Juni", "Juli 2026", "deadline 15/07")
                # Untuk sekarang, cek fakta yang mengandung kata "deadline"
                if 'deadline' in content.lower() or 'selesai' in content.lower():
                    result.append({
                        "id": r[0], "content": content, 
                        "created_at": r[2], "days": 14  # Default 14 hari
                    })
            return result
    except Exception as e:
        logger.error(f"Failed to check deadlines: {str(e)}", exc_info=True)
        return []

def simpan_alert(alert_type: str, message: str, priority: str = "medium", related_fact_id: int = None) -> Optional[int]:
    """Simpan alert proaktif."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            # Cek duplikat (alert sama yang masih active)
            c.execute("SELECT id FROM proactive_alerts WHERE alert_type = ? AND related_fact_id = ? AND status = 'active'",
                      (alert_type, related_fact_id))
            if c.fetchone():
                return None
            
            c.execute("INSERT INTO proactive_alerts (alert_type, message, priority, related_fact_id) VALUES (?, ?, ?, ?)",
                      (alert_type, message, priority, related_fact_id))
            conn.commit()
            return c.lastrowid
    except Exception as e:
        logger.error(f"Failed to save alert: {str(e)}", exc_info=True)
        return None

def lihat_active_alerts() -> List[Dict]:
    """Ambil alert yang masih active."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, alert_type, message, priority, related_fact_id, created_at FROM proactive_alerts WHERE status = 'active' ORDER BY priority DESC, created_at DESC")
            rows = c.fetchall()
            return [
                {"id": r[0], "type": r[1], "message": r[2], "priority": r[3], 
                 "fact_id": r[4], "created_at": r[5]}
                for r in rows
            ]
    except Exception as e:
        logger.error(f"Failed to fetch alerts: {str(e)}", exc_info=True)
        return []

def dismiss_alert(alert_id: int) -> bool:
    """Tandai alert sebagai dismissed."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("UPDATE proactive_alerts SET status = 'dismissed', dismissed_at = CURRENT_TIMESTAMP WHERE id = ?", (alert_id,))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to dismiss alert {alert_id}: {str(e)}", exc_info=True)
        return False

def ignore_alert(alert_id: int) -> bool:
    """Tandai alert sebagai ignored (permanen)."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("UPDATE proactive_alerts SET status = 'ignored', dismissed_at = CURRENT_TIMESTAMP WHERE id = ?", (alert_id,))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to ignore alert {alert_id}: {str(e)}", exc_info=True)
        return False

def update_fact_status(fact_id: int, status: str) -> bool:
    """Update status fakta: 'active', 'done', 'archived'."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("UPDATE facts SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, fact_id))
            conn.commit()
        logger.info(f"Updated fact #{fact_id} status to '{status}'")
        return True
    except Exception as e:
        logger.error(f"Failed to update fact status: {str(e)}", exc_info=True)
        return False

def get_tasks_by_status(status: str = 'active') -> List[Tuple]:
    """Ambil fakta berdasarkan status."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, category, content, importance, created_at FROM facts WHERE deleted = 0 AND status = ? ORDER BY importance DESC", (status,))
            return c.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch tasks: {str(e)}", exc_info=True)
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
    
def get_daily_stats(date_str: str = None) -> Dict:
    """Statistik harian: fakta baru, insight baru, chat count."""
    if date_str is None:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            # Fakta baru hari ini
            c.execute("SELECT COUNT(*) FROM facts WHERE DATE(created_at) = ? AND deleted = 0", (date_str,))
            new_facts = c.fetchone()[0]
            
            # Insight baru hari ini
            c.execute("SELECT COUNT(*) FROM reflections WHERE DATE(created_at) = ?", (date_str,))
            new_insights = c.fetchone()[0]
            
            # Chat hari ini
            c.execute("SELECT COUNT(*) FROM conversations WHERE DATE(timestamp) = ?", (date_str,))
            chat_count = c.fetchone()[0]
            
            # Total fakta
            c.execute("SELECT COUNT(*) FROM facts WHERE deleted = 0")
            total_facts = c.fetchone()[0]
            
            # Total insight
            c.execute("SELECT COUNT(*) FROM reflections")
            total_insights = c.fetchone()[0]
            
        return {
            "date": date_str,
            "new_facts": new_facts,
            "new_insights": new_insights,
            "chat_count": chat_count,
            "total_facts": total_facts,
            "total_insights": total_insights
        }
    except Exception as e:
        logger.error(f"Failed to get daily stats: {str(e)}", exc_info=True)
        return {}

def get_weekly_stats() -> Dict:
    """Statistik mingguan."""
    today = datetime.datetime.now()
    week_start = (today - datetime.timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            # Fakta minggu ini
            c.execute("SELECT COUNT(*) FROM facts WHERE DATE(created_at) >= ? AND deleted = 0", (week_start,))
            week_facts = c.fetchone()[0]
            
            # Insight minggu ini
            c.execute("SELECT COUNT(*) FROM reflections WHERE DATE(created_at) >= ?", (week_start,))
            week_insights = c.fetchone()[0]
            
            # Chat minggu ini
            c.execute("SELECT COUNT(*) FROM conversations WHERE DATE(timestamp) >= ?", (week_start,))
            week_chats = c.fetchone()[0]
            
            # Top categories
            c.execute("""
                SELECT category, COUNT(*) as cnt 
                FROM facts 
                WHERE DATE(created_at) >= ? AND deleted = 0 
                GROUP BY category 
                ORDER BY cnt DESC 
                LIMIT 5
            """, (week_start,))
            top_categories = c.fetchall()
            
        return {
            "week_start": week_start,
            "week_facts": week_facts,
            "week_insights": week_insights,
            "week_chats": week_chats,
            "top_categories": top_categories
        }
    except Exception as e:
        logger.error(f"Failed to get weekly stats: {str(e)}", exc_info=True)
        return {}
    
def simpan_relationship(source_id: int, target_id: int, relation_type: str = "related", confidence: float = 0.7) -> Optional[int]:
    """Simpan hubungan antar fakta."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            # Cek duplikat
            c.execute("SELECT id FROM relationships WHERE (source_id = ? AND target_id = ?) OR (source_id = ? AND target_id = ?)",
                      (source_id, target_id, target_id, source_id))
            if c.fetchone():
                return None
            
            c.execute("INSERT INTO relationships (source_id, target_id, relation_type, confidence) VALUES (?, ?, ?, ?)",
                      (source_id, target_id, relation_type, confidence))
            conn.commit()
            return c.lastrowid
    except Exception as e:
        logger.error(f"Failed to save relationship: {str(e)}", exc_info=True)
        return None

def lihat_semua_relationships() -> List[Dict]:
    """Ambil semua relationships dengan info fakta. Return list of dicts."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT r.id, r.source_id, r.target_id, r.relation_type, r.confidence,
                       f1.content as source_content, f1.category as source_cat,
                       f2.content as target_content, f2.category as target_cat
                FROM relationships r
                JOIN facts f1 ON r.source_id = f1.id
                JOIN facts f2 ON r.target_id = f2.id
                WHERE f1.deleted = 0 AND f2.deleted = 0
                ORDER BY r.confidence DESC
            """)
            rows = c.fetchall()
            
            # Convert to list of dicts untuk akses yang lebih aman
            result = []
            for row in rows:
                result.append({
                    "id": row[0],
                    "source_id": row[1],
                    "target_id": row[2],
                    "relation_type": row[3],
                    "confidence": row[4],
                    "source_content": row[5],
                    "source_cat": row[6],
                    "target_content": row[7],
                    "target_cat": row[8]
                })
            return result
    except Exception as e:
        logger.error(f"Failed to fetch relationships: {str(e)}", exc_info=True)
        return []

def hapus_relationship(rel_id: int) -> bool:
    """Hapus relationship."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM relationships WHERE id = ?", (rel_id,))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to delete relationship {rel_id}: {str(e)}", exc_info=True)
        return False

def hapus_semua_relationships() -> bool:
    """Hapus semua relationships (untuk regenerate)."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM relationships")
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to clear relationships: {str(e)}", exc_info=True)
        return False