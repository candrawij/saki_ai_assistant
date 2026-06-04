# 🚀 IMPROVEMENT GUIDE - Implementation Examples

Panduan ini menyediakan kode siap pakai untuk fix issue-issue dalam audit.

---

## FIX #1: Proper Exception Handling

### ❌ BEFORE (Bad)
```python
def ekstrak_teks_dari_pdf(filepath):
    try:
        reader = PdfReader(filepath)
        return "\n".join([page.extract_text() for page in reader.pages])
    except:  # <-- SILENT FAIL
        return None
```

### ✅ AFTER (Good)
```python
import logging
logger = logging.getLogger(__name__)

def ekstrak_teks_dari_pdf(filepath: str) -> Optional[str]:
    try:
        reader = PdfReader(filepath)
        text = "\n".join([page.extract_text() for page in reader.pages])
        if not text or text.strip() == "":
            logger.warning(f"PDF extract returned empty: {filepath}")
            return None
        logger.info(f"Successfully extracted PDF: {filepath} ({len(text)} chars)")
        return text
    except FileNotFoundError:
        logger.error(f"PDF file not found: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Error extracting PDF {filepath}: {type(e).__name__}: {str(e)}", exc_info=True)
        return None
```

---

## FIX #2: Input Validation

### ❌ BEFORE (Bad)
```python
def simpan_fakta(category, content, source="manual", confidence=1.0, importance=5):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO facts (category, content, source, confidence, importance) VALUES (?, ?, ?, ?, ?)",
              (category, content, source, confidence, importance))
    conn.commit()
    conn.close()
```

### ✅ AFTER (Good)
```python
from typing import Optional

def validate_fakta(category: str, content: str, confidence: float, importance: int) -> tuple[bool, Optional[str]]:
    """Validate fakta inputs. Return (is_valid, error_message)"""
    
    if not isinstance(content, str):
        return False, "Content harus string"
    
    content = content.strip()
    if not content:
        return False, "Content tidak boleh kosong"
    
    if len(content) > 10000:
        return False, "Content terlalu panjang (max 10000 karakter)"
    
    if len(content) < 5:
        return False, "Content terlalu pendek (min 5 karakter)"
    
    category = category.strip() or "umum"
    if len(category) > 100:
        return False, "Kategori terlalu panjang"
    
    if not isinstance(confidence, (int, float)):
        return False, "Confidence harus angka"
    
    if not 0.0 <= confidence <= 1.0:
        return False, "Confidence harus 0-1"
    
    if not isinstance(importance, int):
        return False, "Importance harus integer"
    
    if not 1 <= importance <= 10:
        return False, "Importance harus 1-10"
    
    return True, None

def simpan_fakta(category: str, content: str, source: str = "manual", 
                 confidence: float = 1.0, importance: int = 5) -> tuple[bool, Optional[str]]:
    # Validate
    is_valid, error = validate_fakta(category, content, confidence, importance)
    if not is_valid:
        logger.warning(f"Invalid fakta: {error}")
        return False, error
    
    # Sanitize
    content = content.strip()[:10000]
    category = category.strip() or "umum"
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO facts (category, content, source, confidence, importance) VALUES (?, ?, ?, ?, ?)",
                (category, content, source, confidence, importance)
            )
            conn.commit()
            logger.info(f"Saved fakta: {category} - {content[:50]}... (imp={importance})")
            return True, None
    except Exception as e:
        logger.error(f"Error saving fakta: {str(e)}", exc_info=True)
        return False, f"Gagal menyimpan fakta: {type(e).__name__}"
```

---

## FIX #3: Database Connection Manager

### ❌ BEFORE (Bad)
```python
def simpan_fakta(...):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(...)
    conn.commit()
    conn.close()
```

### ✅ AFTER (Good)
```python
from contextlib import contextmanager
from typing import Generator

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager untuk database connections"""
    conn = sqlite3.connect(
        DB_FILE, 
        check_same_thread=False,  # Untuk Streamlit
        timeout=10.0               # Wait up to 10s kalo db locked
    )
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    
    # Enable WAL mode untuk better concurrent access
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {str(e)}", exc_info=True)
        raise
    finally:
        conn.close()

# Usage:
def simpan_fakta(...):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(...)
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to save fakta: {str(e)}")
        raise
```

---

## FIX #4: Logging Setup

### ❌ BEFORE (Bad)
```python
# No logging at all!
```

### ✅ AFTER (Good)
```python
import logging
import logging.handlers
from pathlib import Path

def setup_logging():
    """Setup logging configuration"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("saki")
    logger.setLevel(logging.DEBUG)
    
    # Console handler (INFO level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    
    # File handler (DEBUG level) - rotating
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "saki.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5                # Keep 5 backups
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_format)
    
    # Error file handler (ERROR level)
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "saki_errors.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_format)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    
    return logger

# At startup:
logger = setup_logging()
logger.info("Saki server started")
```

---

## FIX #5: Ollama Retry Logic

### ❌ BEFORE (Bad)
```python
def ringkas_teks(teks):
    response = ollama.chat(model=MODEL, messages=[...])
    return response["message"]["content"]
    # Crash if Ollama down!
```

### ✅ AFTER (Good)
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
    before_sleep=lambda retry_state: logger.warning(
        f"Ollama request failed, retrying attempt {retry_state.attempt_number}..."
    )
)
def ringkas_teks_with_retry(teks: str) -> str:
    try:
        response = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Ringkas teks berikut:\n\n{teks}"}
        ])
        return response["message"]["content"]
    except requests.ConnectionError:
        logger.error("Ollama server tidak aktif (ConnectionError)")
        raise
    except requests.Timeout:
        logger.error("Ollama server timeout")
        raise
    except Exception as e:
        logger.error(f"Unexpected Ollama error: {type(e).__name__}: {str(e)}")
        raise

def ringkas_teks(teks: str) -> str:
    try:
        return ringkas_teks_with_retry(teks)
    except Exception:
        logger.error("Failed to summarize text after retries")
        return "Maaf, AI server sedang tidak aktif. Coba lagi beberapa saat..."
```

---

## FIX #6: Temp File Cleanup

### ❌ BEFORE (Bad)
```python
def proses_upload(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    
    # ... process ...
    os.unlink(tmp_path)  # Only on success path!
```

### ✅ AFTER (Good)
```python
def proses_upload(uploaded_file) -> tuple[Optional[int], str]:
    tmp_path = None
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        
        logger.info(f"Processing upload: {uploaded_file.name}")
        
        # Extract text
        if ext == ".pdf":
            teks = ekstrak_teks_dari_pdf(tmp_path)
            file_type = "PDF"
        # ... other formats ...
        
        if not teks:
            return None, "Gagal mengekstrak teks"
        
        # Process further...
        logger.info(f"Upload processed successfully: {uploaded_file.name}")
        return doc_id, ringkasan
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        return None, "File tidak ditemukan"
    except Exception as e:
        logger.error(f"Error processing upload: {type(e).__name__}: {str(e)}", exc_info=True)
        return None, f"Gagal: {type(e).__name__}"
    finally:
        # Always cleanup
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                logger.debug(f"Cleaned up temp file: {tmp_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {tmp_path}: {str(e)}")
```

---

## FIX #7: Type Hints

### ❌ BEFORE (Bad)
```python
def lihat_fakta_by_id(fact_id):
    ...
    return result
```

### ✅ AFTER (Good)
```python
from typing import Optional, Tuple, List

def lihat_fakta_by_id(fact_id: int) -> Optional[Tuple]:
    """Get fact by ID. Returns tuple of (id, category, content, ...) or None"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, category, content, source, confidence, importance, access_count, last_accessed, created_at "
                "FROM facts WHERE id = ? AND deleted = 0",
                (fact_id,)
            )
            result = c.fetchone()
            return result
    except Exception as e:
        logger.error(f"Error fetching fact {fact_id}: {str(e)}", exc_info=True)
        return None

def lihat_semua_fakta() -> List[Tuple]:
    """Get all facts. Returns list of fact tuples"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(...)
            results = c.fetchall()
            return results
    except Exception as e:
        logger.error(f"Error fetching all facts: {str(e)}", exc_info=True)
        return []
```

---

## FIX #8: Constants Instead of Magic Numbers

### ❌ BEFORE (Bad)
```python
chunks = [full_text[i:i+1000] for i in range(...)]  # What's 1000?
teks_ringkas = teks[:4000]  # Why 4000?
fakta_text = ... if f[4] >= 0.5  # What's 0.5?
sorted_facts[...][:30]  # Why 30?
```

### ✅ AFTER (Good)
```python
from enum import Enum

# ========== CONSTANTS ==========
# Text processing
TEXT_CHUNK_SIZE = 1000  # Characters per chunk for embedding
SUMMARY_MAX_LENGTH = 4000  # Max chars to summarize
MAX_FACTS_IN_MEMORY = 30  # Max facts to display

# Thresholds
MIN_CONFIDENCE_THRESHOLD = 0.5  # Min confidence to include fact in context
MIN_IMPORTANCE_FOR_TRACKING = 5  # Only track access for importance >= this
MIN_IMPORTANCE_CRITICAL = 7  # High importance threshold
MAX_IMPORTANCE_CRITICAL = 10  # Critical importance threshold
MIN_IMPORTANCE_LOW = 1
MAX_IMPORTANCE_LOW = 3
DAYS_UNUSED_WARNING = 30  # Warn if unused for this many days

# Limits
MAX_CONTENT_LENGTH = 10000  # Max chars for fact content
MIN_CONTENT_LENGTH = 5  # Min chars for fact content
MAX_CATEGORY_LENGTH = 100
MAX_FACTS_FOR_AI_ANALYSIS = 100  # Limit for duplicate detection

# File processing
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md'}
TEMP_FILE_TIMEOUT = 3600  # Delete temp files after 1 hour

# Usage:
chunks = [full_text[i:i+TEXT_CHUNK_SIZE] for i in range(0, len(full_text), TEXT_CHUNK_SIZE)]
teks_ringkas = teks[:SUMMARY_MAX_LENGTH]
sorted_facts = sorted_facts[:MAX_FACTS_IN_MEMORY]
```

---

## FIX #9: Rate Limiting

### ❌ BEFORE (Bad)
```python
# Anyone can spam auto-extraction or AI calls
```

### ✅ AFTER (Good)
```python
from datetime import datetime, timedelta
from collections import defaultdict

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for this key"""
        now = datetime.now()
        
        # Clean old requests
        cutoff = now - timedelta(seconds=self.window_seconds)
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > cutoff
        ]
        
        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(now)
            return True
        
        logger.warning(f"Rate limit exceeded for {key}")
        return False
    
    def get_retry_after(self, key: str) -> int:
        """Get seconds until next allowed request"""
        if not self.requests[key]:
            return 0
        oldest = self.requests[key][0]
        retry_at = oldest + timedelta(seconds=self.window_seconds)
        wait_seconds = (retry_at - datetime.now()).total_seconds()
        return max(0, int(wait_seconds) + 1)

# Create limiters
extract_limiter = RateLimiter(max_requests=5, window_seconds=60)  # 5 per minute
ai_rate_limiter = RateLimiter(max_requests=3, window_seconds=60)  # 3 per minute

# Usage in chat:
def chat_saki(pesan: str, riwayat_chat=None) -> str:
    user_id = st.session_state.get("user_id", "anonymous")
    
    if not ai_rate_limiter.is_allowed(user_id):
        wait = ai_rate_limiter.get_retry_after(user_id)
        st.error(f"Rate limit exceeded. Try again in {wait}s")
        return ""
    
    # ... process chat ...
```

---

## IMPLEMENTATION PRIORITY

```
Priority 1 (Do Now):
1. Fix bare except blocks -> Proper exception handling
2. Add logging system
3. Add input validation
4. Implement DB context manager

Priority 2 (This Week):
5. Add Ollama retry logic
6. Fix temp file cleanup
7. Add type hints
8. Extract constants

Priority 3 (Next):
9. Rate limiting
10. Unit tests
```

---

**Catatan:** Kode-kode di atas bersifat exemplary. Sesuaikan dengan kebutuhan spesifik project Anda.
