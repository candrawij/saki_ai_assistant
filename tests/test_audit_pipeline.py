#!/usr/bin/env python
"""
Test script untuk Saki Audit Pipeline v1.0
Verifikasi timing, token counting, dan audit reporting
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import time
import logging
from src.audit_pipeline import (
    start_audit_request,
    count_tokens,
    count_messages_tokens,
    search_memory,
    search_reflections,
    search_documents,
    search_chroma,
    build_prompt,
    generate_audit_report
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_token_counting():
    """Test token counting functionality"""
    print("\n" + "="*70)
    print("🧪 TEST 1: Token Counting")
    print("="*70)
    
    test_cases = [
        "Hello world",
        "Saya adalah seorang mahasiswa yang sedang belajar Python dan JavaScript",
        "ChatGPT adalah sebuah model bahasa besar yang dikembangkan oleh OpenAI",
        """Saki adalah asisten AI pribadi yang membantu user untuk merangkum dokumen, 
        menjawab pertanyaan, dan mengingat informasi penting dengan menggunakan 
        kombinasi dari database SQLite untuk menyimpan fakta dan ChromaDB untuk 
        semantic search pada dokumen."""
    ]
    
    for text in test_cases:
        tokens = count_tokens(text)
        chars = len(text)
        print(f"✓ Text: '{text[:60]}...'")
        print(f"  Characters: {chars} | Tokens: {tokens} | Ratio: {chars/tokens:.2f} chars/token\n")

def test_audit_metrics():
    """Test audit metrics collection"""
    print("\n" + "="*70)
    print("🧪 TEST 2: Audit Metrics")
    print("="*70)
    
    metrics = start_audit_request()
    print(f"✓ Audit request started: {metrics.request_id}\n")
    
    # Simulate operations
    operations = [
        ("search_memory", 0.050),
        ("search_chroma", 0.250),
        ("build_prompt", 0.030),
        ("ollama_chat", 2.500),
    ]
    
    for op_name, duration in operations:
        metrics.mark_start(op_name)
        time.sleep(duration)
        actual = metrics.mark_end(op_name)
        tokens = int(duration * 1000)  # Simulated token count
        metrics.set_token_count(op_name, tokens)
        print(f"✓ {op_name:20s}: {actual:.3f}s (expected {duration:.3f}s) | {tokens} tokens")
    
    print("\n📊 Audit Summary:")
    summary = metrics.get_summary()
    for key, value in summary.items():
        if key != "timings" and key != "token_counts":
            print(f"  {key}: {value}")
    
    print("\n  Timings:")
    for op, duration in summary['timings'].items():
        print(f"    {op:20s}: {duration:.3f}s")
    
    print("\n  Token Counts:")
    for op, count in summary['token_counts'].items():
        print(f"    {op:20s}: {count}")

def test_search_wrappers():
    """Test search function wrappers"""
    print("\n" + "="*70)
    print("🧪 TEST 3: Search Function Wrappers")
    print("="*70)
    
    metrics = start_audit_request()
    
    print("\n1️⃣  search_memory():")
    try:
        facts = search_memory()
        print(f"   ✓ Retrieved {len(facts)} facts\n")
    except Exception as e:
        print(f"   ⚠️  {type(e).__name__}: {str(e)}\n")
    
    print("2️⃣  search_reflections():")
    try:
        reflections = search_reflections()
        print(f"   ✓ Retrieved {len(reflections)} reflections\n")
    except Exception as e:
        print(f"   ⚠️  {type(e).__name__}: {str(e)}\n")
    
    print("3️⃣  search_documents():")
    try:
        docs = search_documents()
        print(f"   ✓ Retrieved {len(docs)} documents\n")
    except Exception as e:
        print(f"   ⚠️  {type(e).__name__}: {str(e)}\n")
    
    print("4️⃣  search_chroma('test query'):")
    try:
        results = search_chroma("test query", n_results=3)
        print(f"   ✓ Found {len(results)} results\n")
    except Exception as e:
        print(f"   ⚠️  {type(e).__name__}: {str(e)}\n")

def test_prompt_building():
    """Test prompt building with token counting"""
    print("\n" + "="*70)
    print("🧪 TEST 4: Prompt Building & Token Counting")
    print("="*70)
    
    metrics = start_audit_request()
    
    system_prompt = "Kamu adalah asisten AI yang helpful dan honest."
    
    messages = [
        {"role": "user", "content": "Apa itu machine learning?"},
        {"role": "assistant", "content": "Machine learning adalah..."},
        {"role": "user", "content": "Berikan contoh kasusnya"}
    ]
    
    print(f"\n📝 System Prompt: {system_prompt}")
    print(f"   Tokens: {count_tokens(system_prompt)}\n")
    
    print(f"📨 Messages ({len(messages)}):")
    total_tokens = 0
    for i, msg in enumerate(messages):
        tokens = count_tokens(msg['content'])
        total_tokens += tokens
        print(f"  {i+1}. [{msg['role']}] ({tokens} tokens): {msg['content'][:50]}...")
    
    print(f"\n   Total message tokens: {total_tokens}")
    
    # Build full prompt
    prompt_audit = build_prompt(system_prompt, messages)
    
    print(f"\n✅ Prompt Build Complete:")
    print(f"   ├─ Total messages: {len(prompt_audit['messages'])}")
    print(f"   ├─ Character count: {prompt_audit['char_count']}")
    print(f"   ├─ Token count: {prompt_audit['token_count']}")
    print(f"   └─ Char/Token ratio: {prompt_audit['char_count']/prompt_audit['token_count']:.2f}")

def test_audit_report():
    """Test audit report generation"""
    print("\n" + "="*70)
    print("🧪 TEST 5: Audit Report Generation")
    print("="*70)
    
    metrics = start_audit_request()
    
    # Simulate some operations
    print("\nSimulating operations...")
    for i in range(3):
        op_name = f"operation_{i+1}"
        metrics.mark_start(op_name)
        time.sleep(0.1)
        metrics.mark_end(op_name)
        metrics.set_token_count(op_name, 100 * (i+1))
    
    print("\n📊 Generating audit report...")
    report = generate_audit_report(metrics)
    print(report)

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🔍 SAKI AUDIT PIPELINE v1.0 - TEST SUITE")
    print("="*70)
    
    try:
        test_token_counting()
        test_audit_metrics()
        test_search_wrappers()
        test_prompt_building()
        test_audit_report()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED")
        print("="*70)
        print("\n📝 Log output dapat dilihat di: logs/saki.log")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
