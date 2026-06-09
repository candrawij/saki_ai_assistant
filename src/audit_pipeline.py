"""
Saki Audit Pipeline v1.0
Timing measurements, token counting, dan performance monitoring untuk AI pipeline.

Fitur:
- Wrap semua search operations dengan timing
- Token counting sebelum kirim ke Qwen
- Audit logging untuk setiap step
- Performance metrics collection
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import logging
from typing import Optional, List, Tuple, Dict, Any
import json
from datetime import datetime

# Token counting
try:
    from tokenizers import Tokenizer
    TOKENIZER = Tokenizer.from_pretrained("Xenova/qwen2-tokenizer")
except:
    TOKENIZER = None

logger = logging.getLogger("saki.audit")

# ========== AUDIT METRICS STORAGE ==========
class AuditMetrics:
    """Simpan metrics untuk satu request."""
    def __init__(self):
        self.timestamps = {}
        self.timings = {}
        self.token_counts = {}
        self.request_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]
        self.start_time = time.time()
    
    def mark_start(self, operation: str):
        """Mark mulai operasi."""
        self.timestamps[f"{operation}_start"] = time.time()
    
    def mark_end(self, operation: str):
        """Mark selesai operasi dan hitung durasi."""
        end_time = time.time()
        start_key = f"{operation}_start"
        if start_key in self.timestamps:
            duration = end_time - self.timestamps[start_key]
            self.timings[operation] = duration
            return duration
        return None
    
    def set_token_count(self, operation: str, count: int):
        """Simpan token count untuk operasi."""
        self.token_counts[operation] = count
    
    def get_summary(self) -> Dict:
        """Get ringkasan audit metrics."""
        total_time = time.time() - self.start_time
        return {
            "request_id": self.request_id,
            "timings": self.timings,
            "token_counts": self.token_counts,
            "total_time": total_time,
            "timestamp": datetime.now().isoformat()
        }
    
    def log_summary(self):
        """Log ringkasan audit."""
        summary = self.get_summary()
        logger.info(f"🔍 AUDIT REQUEST #{summary['request_id']}")
        for op, duration in summary['timings'].items():
            tokens = summary['token_counts'].get(op, 'N/A')
            logger.info(f"  ├─ {op:20s}: {duration:7.3f}s | tokens: {tokens}")
        logger.info(f"  └─ TOTAL: {summary['total_time']:.3f}s")
        return summary

# ========== GLOBAL METRICS ==========
current_metrics = None

def start_audit_request() -> AuditMetrics:
    """Mulai audit request baru."""
    global current_metrics
    current_metrics = AuditMetrics()
    return current_metrics

def get_current_metrics() -> Optional[AuditMetrics]:
    """Get metrics untuk request current."""
    global current_metrics
    return current_metrics

# ========== TOKEN COUNTING ==========
def count_tokens(text: str) -> int:
    """Hitung jumlah tokens dalam text."""
    if not text:
        return 0
    
    if TOKENIZER:
        try:
            encoding = TOKENIZER.encode(text)
            return len(encoding.ids)
        except Exception as e:
            logger.warning(f"Tokenizer error: {str(e)}, falling back to char count")
    
    # Fallback: rough estimation based on characters
    # Qwen uses roughly 1 token per 4 characters
    return max(1, len(text) // 4)

def count_messages_tokens(messages: List[Dict]) -> int:
    """Hitung total tokens dalam message list."""
    total = 0
    for msg in messages:
        total += count_tokens(msg.get("content", ""))
    return total

# ========== WRAPPER FUNCTIONS DENGAN TIMING ==========

def search_memory() -> List[Tuple]:
    """
    Wrap lihat_semua_fakta() dengan timing.
    Fetch semua facts/memory dari database.
    """
    from src.database import lihat_semua_fakta
    
    metrics = get_current_metrics()
    if metrics:
        metrics.mark_start("search_memory")
    
    try:
        start = time.time()
        result = lihat_semua_fakta()
        duration = time.time() - start
        
        if metrics:
            metrics.mark_end("search_memory")
            metrics.set_token_count("search_memory", len(str(result)))
        
        logger.info(f"⏱️  search_memory: {duration:.3f}s | items: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"❌ search_memory failed: {str(e)}", exc_info=True)
        if metrics:
            metrics.mark_end("search_memory")
        return []

def search_reflections() -> List[Tuple]:
    """
    Wrap lihat_semua_reflections() dengan timing.
    Fetch semua reflections/insights dari database.
    """
    from src.database import lihat_semua_reflections
    
    metrics = get_current_metrics()
    if metrics:
        metrics.mark_start("search_reflections")
    
    try:
        start = time.time()
        result = lihat_semua_reflections()
        duration = time.time() - start
        
        if metrics:
            metrics.mark_end("search_reflections")
            metrics.set_token_count("search_reflections", len(str(result)))
        
        logger.info(f"⏱️  search_reflections: {duration:.3f}s | items: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"❌ search_reflections failed: {str(e)}", exc_info=True)
        if metrics:
            metrics.mark_end("search_reflections")
        return []

def search_timeline() -> List[Dict]:
    """
    Wrap generate_timeline() dengan timing.
    Generate timeline data: bulan → minggu → hari.
    """
    from src.ai import generate_timeline
    
    metrics = get_current_metrics()
    if metrics:
        metrics.mark_start("search_timeline")
    
    try:
        start = time.time()
        result = generate_timeline()
        duration = time.time() - start
        
        if metrics:
            metrics.mark_end("search_timeline")
            metrics.set_token_count("search_timeline", len(json.dumps(result)))
        
        logger.info(f"⏱️  search_timeline: {duration:.3f}s | months: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"❌ search_timeline failed: {str(e)}", exc_info=True)
        if metrics:
            metrics.mark_end("search_timeline")
        return []

def search_documents() -> List[Tuple]:
    """
    Wrap lihat_semua_dokumen() dengan timing.
    Fetch semua documents dari database.
    """
    from src.database import lihat_semua_dokumen
    
    metrics = get_current_metrics()
    if metrics:
        metrics.mark_start("search_documents")
    
    try:
        start = time.time()
        result = lihat_semua_dokumen()
        duration = time.time() - start
        
        if metrics:
            metrics.mark_end("search_documents")
            metrics.set_token_count("search_documents", len(str(result)))
        
        logger.info(f"⏱️  search_documents: {duration:.3f}s | items: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"❌ search_documents failed: {str(e)}", exc_info=True)
        if metrics:
            metrics.mark_end("search_documents")
        return []

def search_chroma(query: str, n_results: int = 3) -> List[Tuple]:
    """
    Wrap cari_dokumen_semantik() dengan timing.
    Semantic search dalam documents menggunakan ChromaDB.
    """
    from src.database import cari_dokumen_semantik
    
    metrics = get_current_metrics()
    if metrics:
        metrics.mark_start("search_chroma")
    
    try:
        start = time.time()
        result = cari_dokumen_semantik(query, n_results)
        duration = time.time() - start
        
        if metrics:
            metrics.mark_end("search_chroma")
            metrics.set_token_count("search_chroma", len(str(result)))
        
        logger.info(f"⏱️  search_chroma: {duration:.3f}s | query: '{query[:50]}...' | results: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"❌ search_chroma failed: {str(e)}", exc_info=True)
        if metrics:
            metrics.mark_end("search_chroma")
        return []

def build_prompt(system_prompt: str, messages: List[Dict]) -> Dict:
    """
    Build dan audit prompt sebelum kirim ke Qwen.
    
    Returns:
        Dict dengan 'messages', 'prompt_text', 'token_count'
    """
    metrics = get_current_metrics()
    if metrics:
        metrics.mark_start("build_prompt")
    
    try:
        # Tambah system prompt jika belum ada
        full_messages = messages.copy()
        if not any(m.get("role") == "system" for m in full_messages):
            full_messages.insert(0, {"role": "system", "content": system_prompt})
        
        # Hitung tokens
        total_tokens = count_messages_tokens(full_messages)
        prompt_text = "\n".join([f"[{m.get('role')}]\n{m.get('content', '')}" for m in full_messages])
        
        if metrics:
            metrics.mark_end("build_prompt")
            metrics.set_token_count("build_prompt", total_tokens)
        
        # Audit log
        logger.info(f"⏱️  build_prompt completed")
        logger.info(f"📊 PROMPT AUDIT:")
        logger.info(f"   ├─ Total messages: {len(full_messages)}")
        logger.info(f"   ├─ Character count: {len(prompt_text)}")
        logger.info(f"   ├─ Token count: {total_tokens}")
        logger.info(f"   └─ Prompt length: {len(prompt_text)}")
        
        # Print untuk visibility
        print(f"\n{'='*60}")
        print(f"🔍 PROMPT AUDIT BEFORE SENDING TO QWEN")
        print(f"{'='*60}")
        print(f"Prompt length: {len(prompt_text)} characters")
        print(f"Token count: {total_tokens}")
        print(f"Message count: {len(full_messages)}")
        print(f"{'='*60}\n")
        
        return {
            "messages": full_messages,
            "prompt_text": prompt_text,
            "token_count": total_tokens,
            "char_count": len(prompt_text)
        }
    except Exception as e:
        logger.error(f"❌ build_prompt failed: {str(e)}", exc_info=True)
        if metrics:
            metrics.mark_end("build_prompt")
        return {
            "messages": messages,
            "prompt_text": "",
            "token_count": 0,
            "char_count": 0
        }

def audit_ollama_chat(model: str, messages: List[Dict], audit_name: str = "ollama.chat") -> Dict:
    """
    Wrap ollama.chat() call dengan timing dan audit logging.
    Log token count dan performance sebelum dan sesudah.
    """
    import ollama
    
    metrics = get_current_metrics()
    if metrics:
        metrics.mark_start(audit_name)
    
    try:
        # Pre-flight audit
        input_tokens = count_messages_tokens(messages)
        logger.info(f"📤 SENDING TO {model.upper()}")
        logger.info(f"   ├─ Input tokens: {input_tokens}")
        logger.info(f"   ├─ Messages: {len(messages)}")
        
        print(f"\n📤 SENDING TO QWEN:")
        print(f"   Input tokens: {input_tokens}")
        print()
        
        # Call Qwen
        start = time.time()
        response = ollama.chat(model=model, messages=messages)
        duration = time.time() - start
        
        # Post-flight audit
        output_text = response.get("message", {}).get("content", "")
        output_tokens = count_tokens(output_text)
        
        logger.info(f"📥 RECEIVED FROM {model.upper()}")
        logger.info(f"   ├─ Output tokens: {output_tokens}")
        logger.info(f"   ├─ Response time: {duration:.3f}s")
        logger.info(f"   ├─ Output length: {len(output_text)} chars")
        logger.info(f"   └─ Tokens/sec: {output_tokens/duration:.1f}")
        
        if metrics:
            metrics.mark_end(audit_name)
            metrics.set_token_count(f"{audit_name}_input", input_tokens)
            metrics.set_token_count(f"{audit_name}_output", output_tokens)
        
        print(f"📥 RESPONSE:")
        print(f"   Output tokens: {output_tokens}")
        print(f"   Response time: {duration:.3f}s")
        print(f"   Throughput: {output_tokens/duration:.1f} tokens/sec\n")
        
        return response
    except Exception as e:
        logger.error(f"❌ {audit_name} failed: {str(e)}", exc_info=True)
        if metrics:
            metrics.mark_end(audit_name)
        raise

# ========== AUDIT REPORT ==========
def generate_audit_report(metrics: AuditMetrics = None) -> str:
    """Generate audit report untuk request."""
    if metrics is None:
        metrics = get_current_metrics()
    
    if metrics is None:
        return "No metrics available"
    
    summary = metrics.get_summary()
    
    # Format report
    report = "\n" + "="*70 + "\n"
    report += f"🔍 SAKI AUDIT REPORT #{summary['request_id']}\n"
    report += "="*70 + "\n"
    
    # Timings
    report += "\n⏱️  TIMINGS:\n"
    for op, duration in sorted(summary['timings'].items(), key=lambda x: x[1], reverse=True):
        tokens = summary['token_counts'].get(op, 'N/A')
        bar = "█" * int(duration * 50)
        report += f"  {op:25s} {duration:7.3f}s {bar}\n"
    
    # Token counts
    report += "\n📊 TOKEN COUNTS:\n"
    for op, count in sorted(summary['token_counts'].items(), key=lambda x: x[1] if isinstance(x[1], int) else 0, reverse=True):
        if isinstance(count, int):
            report += f"  {op:25s} {count:8,d} tokens\n"
    
    report += f"\n⏱️  TOTAL TIME: {summary['total_time']:.3f}s\n"
    report += "="*70 + "\n"
    
    return report
