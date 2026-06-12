"""
Performance Profiler — Cari bottleneck di Saki
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def profile_boot():
    """Profile waktu boot Saki."""
    print("=" * 60)
    print("📊 BOOT PROFILE")
    print("=" * 60)
    
    timings = {}
    
    # 1. Database init
    t0 = time.time()
    from src.database import init_db, lihat_semua_fakta
    init_db()
    timings["DB Init"] = time.time() - t0
    
    # 2. ChromaDB init
    t0 = time.time()
    from src.database import init_chroma
    try:
        init_chroma()
        timings["ChromaDB Init"] = time.time() - t0
    except:
        timings["ChromaDB Init"] = "ERROR"
    
    # 3. Load facts
    t0 = time.time()
    facts = lihat_semua_fakta()
    timings[f"Load Facts ({len(facts)} items)"] = time.time() - t0
    
    # 4. Load reflections
    t0 = time.time()
    from src.database import lihat_semua_reflections
    reflections = lihat_semua_reflections()
    timings[f"Load Reflections ({len(reflections)} items)"] = time.time() - t0
    
    # 5. Load documents
    t0 = time.time()
    from src.database import lihat_semua_dokumen
    docs = lihat_semua_dokumen()
    timings[f"Load Documents ({len(docs)} items)"] = time.time() - t0
    
    # Print results
    total = 0
    for name, elapsed in timings.items():
        if isinstance(elapsed, str):
            print(f"  {name}: {elapsed}")
        else:
            print(f"  {name}: {elapsed*1000:.0f}ms")
            total += elapsed
    
    print(f"\n  TOTAL BOOT: {total*1000:.0f}ms")
    print()


def profile_chat():
    """Profile satu chat lengkap dengan context breakdown."""
    print("=" * 60)
    print("📊 CHAT PROFILE")
    print("=" * 60)
    
    from src.database import lihat_semua_fakta, cari_dokumen_semantik
    import ollama
    
    test_message = "Halo Saki, apa kabar?"
    timings = {}
    token_counts = {}
    
    # 1. Load facts
    t0 = time.time()
    facts = lihat_semua_fakta()
    timings["Load Facts"] = time.time() - t0
    facts_text = "\n".join([f"- [{f[1]}] {f[2]}" for f in facts if f[4] >= 0.5])
    token_counts["Facts"] = len(facts_text.split()) * 1.3  # Estimasi
    
    # 2. Semantic search
    t0 = time.time()
    docs = cari_dokumen_semantik(test_message, n_results=3)
    timings["Semantic Search"] = time.time() - t0
    docs_text = ""
    for doc in docs:
        docs_text += f"📄 {doc[1]}\n{doc[4][:300] if doc[4] else ''}\n\n"
    token_counts["Documents"] = len(docs_text.split()) * 1.3
    
    # 3. Build system prompt
    t0 = time.time()
    from src.ai import SYSTEM_PROMPT
    system_tokens = len(SYSTEM_PROMPT.split()) * 1.3
    token_counts["System"] = system_tokens
    timings["System Prompt"] = time.time() - t0
    
    # 4. Total context
    total_tokens = sum(token_counts.values())
    token_counts["User Message"] = len(test_message.split()) * 1.3
    total_tokens += token_counts["User Message"]
    
    # 5. Ollama chat (TEST ONLY - skip kalau gak mau nunggu)
    print("\n⚡ Mengirim ke Ollama...")
    t0 = time.time()
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"Info user:\n{facts_text[:500]}"},
            {"role": "user", "content": test_message}
        ]
        response = ollama.chat(model="qwen3:4b", messages=messages)
        response_text = response["message"]["content"]
        response_tokens = len(response_text.split()) * 1.3
        elapsed = time.time() - t0
        timings["Ollama Chat"] = elapsed
        token_counts["Response"] = response_tokens
        
        tps = response_tokens / elapsed if elapsed > 0 else 0
        print(f"  Response: {response_tokens:.0f} tokens in {elapsed:.1f}s")
        print(f"  TPS: {tps:.1f} tokens/sec")
    except Exception as e:
        timings["Ollama Chat"] = f"ERROR: {e}"
    
    # Print breakdown
    print(f"\n📝 CONTEXT BREAKDOWN:")
    print(f"  System:     {token_counts['System']:.0f} tokens")
    print(f"  Facts:      {token_counts['Facts']:.0f} tokens ({token_counts['Facts']/total_tokens*100:.0f}%)")
    if 'Documents' in token_counts:
        print(f"  Documents:  {token_counts['Documents']:.0f} tokens ({token_counts['Documents']/total_tokens*100:.0f}%)")
    print(f"  User:       {token_counts['User Message']:.0f} tokens")
    print(f"  ─────────────────────")
    print(f"  TOTAL:      {total_tokens:.0f} tokens")
    
    print(f"\n⏱️  TIMINGS:")
    for name, elapsed in timings.items():
        if isinstance(elapsed, str):
            print(f"  {name}: {elapsed}")
        else:
            print(f"  {name}: {elapsed*1000:.0f}ms")
    
    # Diagnosis
    print(f"\n💡 DIAGNOSIS:")
    if total_tokens > 4000:
        print(f"  ⚠️  Context BESAR ({total_tokens:.0f} tokens) — pertimbangkan:")
        if token_counts.get('Facts', 0) > 1500:
            print(f"     - Kurangi fakta yang dikirim (pakai MIN_CONFIDENCE_THRESHOLD lebih tinggi)")
        if token_counts.get('Documents', 0) > 2000:
            print(f"     - Kurangi n_results di semantic search")
    elif total_tokens > 2000:
        print(f"  ✅ Context OK ({total_tokens:.0f} tokens)")
    else:
        print(f"  ✅ Context ringan ({total_tokens:.0f} tokens)")
    
    if 'Ollama Chat' in timings and isinstance(timings['Ollama Chat'], (int, float)):
        if timings['Ollama Chat'] > 5:
            print(f"  ⚠️  Model response lambat ({timings['Ollama Chat']:.1f}s) — pertimbangkan model lebih kecil")
        else:
            print(f"  ✅ Response cepat ({timings['Ollama Chat']:.1f}s)")
    
    print()


if __name__ == "__main__":
    print("🔍 SAKI PERFORMANCE PROFILER")
    print()
    
    profile_boot()
    profile_chat()
    
    print("=" * 60)
    print("Selesai!")