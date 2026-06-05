import saki_ai
import ollama


def test_auto_rate_importance(monkeypatch):
    def fake_chat(*args, **kwargs):
        return {"message": {"content": "8"}}
    monkeypatch.setattr(ollama, "chat", fake_chat)
    score = saki_ai.auto_rate_importance("Saya bisa Python", "skill")
    assert isinstance(score, int)
    assert 1 <= score <= 10
