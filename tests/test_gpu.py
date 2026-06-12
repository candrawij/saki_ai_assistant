"""Test GPU performance"""
import ollama
import time

print("=" * 50)
print("Testing qwen3:4b SENDIRIAN (tanpa model lain)...")
print("=" * 50)
print()

start = time.time()
r = ollama.chat(
    model='qwen3:4b',
    messages=[{'role': 'user', 'content': 'Halo, apa kabar?'}],
    keep_alive=60
)
elapsed = time.time() - start
tokens = len(r['message']['content'].split()) * 1.3
response_text = r['message']['content'][:100]

print(f"Response: {response_text}")
print(f"Time: {elapsed:.1f}s")
print(f"Tokens: {tokens:.0f}")
print(f"TPS: {tokens/elapsed:.1f}")
print()

print("=" * 50)
print("Testing qwen3:4b REASONING...")
print("=" * 50)
print()

start = time.time()
r = ollama.chat(
    model='qwen3:4b',
    messages=[{
        'role': 'user',
        'content': 'Analisis: apakah ini fakta penting? Jawab JSON saja. Pesan: Saya sedang mengerjakan skripsi tentang machine learning.'
    }],
    keep_alive=60
)
elapsed = time.time() - start
tokens = len(r['message']['content'].split()) * 1.3
response_text = r['message']['content'][:200]

print(f"Response: {response_text}")
print(f"Time: {elapsed:.1f}s")
print(f"TPS: {tokens/elapsed:.1f}")