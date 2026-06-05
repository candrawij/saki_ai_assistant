import os

import saki_database
from saki_files import proses_upload

class DummyUpload:
    def __init__(self, name, content_bytes):
        self.name = name
        self._content = content_bytes
    def read(self):
        return self._content


def test_proses_upload_txt(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(saki_database, "DB_FILE", str(db_path))
    saki_database.init_db()

    # Patch ollama.chat to return a simple summary
    import ollama
    def fake_chat(*args, **kwargs):
        return {"message": {"content": "Ringkasan dari dokumen."}}
    monkeypatch.setattr(ollama, "chat", fake_chat)

    uploaded = DummyUpload("test.txt", b"Ini adalah isi file untuk test.")
    doc_id, summary = proses_upload(uploaded)
    assert doc_id is not None
    assert isinstance(summary, str) and len(summary) > 0
