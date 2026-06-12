"""Debug Relationship Extraction"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai import get_router
from src.model_router import TaskType
from src.database import lihat_semua_fakta

fakta = lihat_semua_fakta()[:10]
fakta_text = '\n'.join([f'[#{f[0]}] [{f[1]}] {f[2]}' for f in fakta])

prompt = f"""Temukan PASANGAN fakta yang SALING TERKAIT.

{fakta_text}

Output HARUS JSON array:
[{{"source_id": 1, "target_id": 3, "relation_type": "related", "confidence": 0.9}}]
Jika tidak ada, jawab: []"""

router = get_router()
result = router.chat(
    messages=[
        {'role': 'system', 'content': 'Jawab HANYA JSON array. Contoh: [{"source_id":1,"target_id":2}]'},
        {'role': 'user', 'content': prompt}
    ],
    task_type=TaskType.RELATIONSHIP
)
raw = result['content']
print('RAW RESPONSE:')
print(repr(raw[:500]))
print()
print('Model:', result['model'])
print('Tokens:', result['tokens'])