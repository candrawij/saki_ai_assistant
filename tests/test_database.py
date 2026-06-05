import os
import importlib

import saki_database

def test_init_and_save_fact(tmp_path, monkeypatch):
    # Use a temporary DB file for tests
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(saki_database, "DB_FILE", str(db_path))

    # Initialize DB and save a fact
    saki_database.init_db()
    ok, err = saki_database.simpan_fakta("testcat", "isi fakta unit test", "test", 0.9, 7)
    assert ok, f"simpan_fakta failed: {err}"

    facts = saki_database.lihat_semua_fakta()
    assert any("isi fakta unit test" in f[2] for f in facts)
