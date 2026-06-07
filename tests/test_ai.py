import sys
from pathlib import Path

# Ensure project root is on sys.path so tests can import local modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import saki_ai
import ollama

def test_auto_rate_importance(monkeypatch):
    def fake_chat(*args, **kwargs):
        return {"message": {"content": "8"}}
    monkeypatch.setattr(ollama, "chat", fake_chat)
    score = saki_ai.auto_rate_importance("Saya bisa Python", "skill")
    assert isinstance(score, int)
    assert 1 <= score <= 10
