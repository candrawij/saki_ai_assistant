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
        self.context_composition = {}  # Breakdown dari prompt composition
        self.response_metrics = {}      # Response tokens dan inference time
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
    
    def set_context_composition(self, composition: Dict[str, int]):
        """Simpan breakdown context composition."""
        self.context_composition = composition
    
    def set_response_metrics(self, response_tokens: int, inference_time: float):
        """Simpan response metrics untuk TPS calculation."""
        self.response_metrics = {
            "response_tokens": response_tokens,
            "inference_time": inference_time,
            "tps": response_tokens / inference_time if inference_time > 0 else 0
        }
    
    def get_summary(self) -> Dict:
        """Get ringkasan audit metrics."""
        total_time = time.time() - self.start_time
        return {
            "request_id": self.request_id,
            "timings": self.timings,
            "token_counts": self.token_counts,
            "context_composition": self.context_composition,
            "response_metrics": self.response_metrics,
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
    Dengan context composition breakdown.
    
    Returns:
        Dict dengan 'messages', 'prompt_text', 'token_count', 'composition'
    """
    metrics = get_current_metrics()
    if metrics:
        metrics.mark_start("build_prompt")
    
    try:
        # Tambah system prompt jika belum ada
        full_messages = messages.copy()
        if not any(m.get("role") == "system" for m in full_messages):
            full_messages.insert(0, {"role": "system", "content": system_prompt})
        
        # === CONTEXT COMPOSITION BREAKDOWN ===
        composition = {}
        total_tokens = 0
        
        # 1. System Prompt
        system_tokens = count_tokens(system_prompt)
        composition["System Prompt"] = system_tokens
        total_tokens += system_tokens
        logger.debug(f"System Prompt tokens: {system_tokens}")
        
        # 2. Analyze other messages untuk breakdown
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            tokens = count_tokens(content)
            
            if role == "system":
                # Skip system prompt (sudah dihitung)
                if content != system_prompt:
                    if "Memory" in content or "Info tentang user" in content:
                        composition["Memory"] = composition.get("Memory", 0) + tokens
                    elif "Reflection" in content or "insight" in content.lower():
                        composition["Reflection"] = composition.get("Reflection", 0) + tokens
                    elif "Timeline" in content or "timeline" in content.lower():
                        composition["Timeline"] = composition.get("Timeline", 0) + tokens
                    elif "Dokumen" in content or "Document" in content:
                        composition["Documents"] = composition.get("Documents", 0) + tokens
                    else:
                        composition["Context"] = composition.get("Context", 0) + tokens
            elif role == "user":
                composition["Question"] = composition.get("Question", 0) + tokens
            elif role == "assistant":
                composition["History"] = composition.get("History", 0) + tokens
        
        # Calculate total tokens
        total_tokens = count_messages_tokens(full_messages)
        prompt_text = "\n".join([f"[{m.get('role')}]\n{m.get('content', '')}" for m in full_messages])
        
        if metrics:
            metrics.mark_end("build_prompt")
            metrics.set_token_count("build_prompt", total_tokens)
            metrics.set_context_composition(composition)
        
        # Audit log - Detailed breakdown
        logger.info(f"⏱️  build_prompt completed")
        logger.info(f"📊 PROMPT COMPOSITION BREAKDOWN:")
        for component, tokens in sorted(composition.items(), key=lambda x: x[1], reverse=True):
            percentage = (tokens / total_tokens * 100) if total_tokens > 0 else 0
            bar = "█" * int(percentage / 5)
            logger.info(f"   ├─ {component:20s}: {tokens:5d} tokens ({percentage:5.1f}%) {bar}")
        logger.info(f"   └─ TOTAL:           {total_tokens:5d} tokens")
        
        # Print untuk visibility
        print(f"\n{'='*70}")
        print(f"🔍 PROMPT COMPOSITION BREAKDOWN")
        print(f"{'='*70}")
        for component, tokens in sorted(composition.items(), key=lambda x: x[1], reverse=True):
            percentage = (tokens / total_tokens * 100) if total_tokens > 0 else 0
            print(f"{component:20s}: {tokens:5d} tokens ({percentage:5.1f}%)")
        print(f"{'-'*70}")
        print(f"{'TOTAL':20s}: {total_tokens:5d} tokens")
        print(f"{'='*70}\n")
        
        return {
            "messages": full_messages,
            "prompt_text": prompt_text,
            "token_count": total_tokens,
            "char_count": len(prompt_text),
            "composition": composition
        }
    except Exception as e:
        logger.error(f"❌ build_prompt failed: {str(e)}", exc_info=True)
        if metrics:
            metrics.mark_end("build_prompt")
        return {
            "messages": messages,
            "prompt_text": "",
            "token_count": 0,
            "char_count": 0,
            "composition": {}
        }

def audit_ollama_chat(model: str, messages: List[Dict], audit_name: str = "ollama.chat") -> Dict:
    """
    Wrap ollama.chat() call dengan timing dan audit logging.
    Log token count, performance, dan response metrics (TPS).
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
        
        print(f"\n{'='*70}")
        print(f"📤 SENDING TO QWEN")
        print(f"{'='*70}")
        print(f"Prompt Tokens: {input_tokens}")
        print()
        
        # Call Qwen
        start_time = time.time()
        response = ollama.chat(model=model, messages=messages)
        inference_time = time.time() - start_time
        
        # Post-flight audit
        output_text = response.get("message", {}).get("content", "")
        response_tokens = count_tokens(output_text)
        tps = response_tokens / inference_time if inference_time > 0 else 0
        
        # Save response metrics untuk audit report
        if metrics:
            metrics.set_response_metrics(response_tokens, inference_time)
        
        logger.info(f"📥 RECEIVED FROM {model.upper()}")
        logger.info(f"   ├─ Response Tokens: {response_tokens}")
        logger.info(f"   ├─ Inference Time: {inference_time:.3f}s")
        logger.info(f"   ├─ Output length: {len(output_text)} chars")
        logger.info(f"   ├─ TPS (Tokens/sec): {tps:.2f}")
        logger.info(f"   └─ Total tokens (in+out): {input_tokens + response_tokens}")
        
        if metrics:
            metrics.mark_end(audit_name)
            metrics.set_token_count(f"{audit_name}_input", input_tokens)
            metrics.set_token_count(f"{audit_name}_output", response_tokens)
        
        # Detailed response metrics
        print(f"{'='*70}")
        print(f"📥 RESPONSE METRICS")
        print(f"{'='*70}")
        print(f"Response Tokens:     {response_tokens:6d}")
        print(f"Inference Time:      {inference_time:6.3f}s")
        print(f"TPS (Tokens/sec):    {tps:6.2f}")
        print(f"Total Tokens:        {input_tokens + response_tokens:6d}")
        print(f"{'='*70}\n")
        
        return response
    except Exception as e:
        logger.error(f"❌ {audit_name} failed: {str(e)}", exc_info=True)
        if metrics:
            metrics.mark_end(audit_name)
        raise

# ========== AUDIT REPORT ==========
def generate_audit_report(metrics: AuditMetrics = None) -> str:
    """Generate comprehensive audit report dengan context composition dan response metrics."""
    if metrics is None:
        metrics = get_current_metrics()
    
    if metrics is None:
        return "No metrics available"
    
    summary = metrics.get_summary()
    
    # Format report
    report = "\n" + "="*80 + "\n"
    report += f"🔍 SAKI AUDIT REPORT #{summary['request_id']}\n"
    report += "="*80 + "\n"
    
    # === CONTEXT COMPOSITION ===
    composition = summary.get('context_composition', {})
    if composition:
        total_prompt_tokens = sum(composition.values())
        report += "\n📝 PROMPT COMPOSITION:\n"
        for component, tokens in sorted(composition.items(), key=lambda x: x[1], reverse=True):
            percentage = (tokens / total_prompt_tokens * 100) if total_prompt_tokens > 0 else 0
            bar = "█" * int(percentage / 5)
            report += f"  {component:20s}: {tokens:5d} tokens ({percentage:5.1f}%) {bar}\n"
        report += f"  {'-'*75}\n"
        report += f"  {'TOTAL PROMPT':20s}: {total_prompt_tokens:5d} tokens\n"
    
    # === TIMINGS ===
    report += "\n⏱️  OPERATION TIMINGS:\n"
    for op, duration in sorted(summary['timings'].items(), key=lambda x: x[1], reverse=True):
        tokens = summary['token_counts'].get(op, 'N/A')
        bar = "█" * int(duration * 50)
        report += f"  {op:25s} {duration:7.3f}s {bar}\n"
    
    # === RESPONSE METRICS ===
    response_metrics = summary.get('response_metrics', {})
    if response_metrics:
        response_tokens = response_metrics.get('response_tokens', 0)
        inference_time = response_metrics.get('inference_time', 0)
        tps = response_metrics.get('tps', 0)
        
        report += "\n📊 RESPONSE METRICS:\n"
        report += f"  {'Response Tokens':25s}: {response_tokens:6d}\n"
        report += f"  {'Inference Time':25s}: {inference_time:6.3f}s\n"
        report += f"  {'TPS (Tokens/sec)':25s}: {tps:6.2f}\n"
        
        # Performance analysis
        report += "\n💡 PERFORMANCE ANALYSIS:\n"
        if tps < 20:
            report += f"  ⚠️  Low TPS ({tps:.2f}): Model might be slow or context too large\n"
        elif tps > 100:
            report += f"  ✅ High TPS ({tps:.2f}): Excellent inference speed\n"
        else:
            report += f"  ✓ Normal TPS ({tps:.2f}): Good inference speed\n"
    
    # === TOKEN COUNTS SUMMARY ===
    report += "\n📈 TOKEN COUNTS SUMMARY:\n"
    token_counts = summary['token_counts']
    input_tokens = token_counts.get('ollama.chat_main_input', token_counts.get('ollama.chat_input', 0))
    output_tokens = token_counts.get('ollama.chat_main_output', token_counts.get('ollama.chat_output', 0))
    
    if input_tokens and output_tokens:
        total_tokens = input_tokens + output_tokens
        report += f"  {'Input Tokens':25s}: {input_tokens:8d}\n"
        report += f"  {'Output Tokens':25s}: {output_tokens:8d}\n"
        report += f"  {'Total Tokens':25s}: {total_tokens:8d}\n"
    
    # === TIMING SUMMARY ===
    report += f"\n⏱️  TOTAL REQUEST TIME: {summary['total_time']:.3f}s\n"
    report += "="*80 + "\n"
    
    return report
