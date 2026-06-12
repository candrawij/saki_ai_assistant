"""Test Reflection Fix"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai import generate_reflection

print("=" * 50)
print("Testing Reflection with Markdown Parser")
print("=" * 50)
print()

insights, error = generate_reflection()

if error:
    print(f"ERROR: {error}")
else:
    print(f"OK: {len(insights)} insights generated!")
    print()
    for i, ins in enumerate(insights):
        title = ins.get("title", "?")
        sources = ins.get("source_ids", [])
        print(f"  {i+1}. {title}")
        print(f"     Sources: {sources}")
        print()