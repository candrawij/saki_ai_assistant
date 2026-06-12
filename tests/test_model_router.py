"""
Test Model Router
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.model_router import ModelRouter, TaskType

router = ModelRouter()
print('Available models:', router.get_available_models())
print()
print('Routing table:')
for task, tier in router.routing.items():
    print(f'  {task.value:15} -> {router.models[tier]}')
print()

# Test klasifikasi
tests = [
    'halo',
    'buka folder data', 
    'catat: test',
    'ringkas teks panjang',
    'task: deadline besok',
    'progress project',
    'apa kabar?',
]
for msg in tests:
    task = router.classify_task(msg)
    model = router.get_model(task)
    print(f'  "{msg:25}" -> {task.value:12} -> {model}')