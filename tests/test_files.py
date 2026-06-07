import os
import sys
import pytest
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import saki_database
from saki_files import proses_upload, ekstrak_teks_dari_csv

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

    import ollama
    def fake_chat(*args, **kwargs):
        return {"message": {"content": "Ringkasan dari dokumen."}}
    monkeypatch.setattr(ollama, "chat", fake_chat)

    uploaded = DummyUpload("test.txt", b"Ini adalah isi file untuk test.")
    doc_id, summary = proses_upload(uploaded)
    assert doc_id is not None
    assert isinstance(summary, str) and len(summary) > 0


class TestCsvExtraction:
    def test_extract_csv_small(self):
        """Test CSV kecil."""
        import tempfile
        csv_content = "Nama,Usia,Kota\nAndi,25,Jakarta\nBudi,30,Bandung"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            result = ekstrak_teks_dari_csv(temp_path)
            assert result is not None
            assert "Nama" in result
            assert "Andi" in result
            assert "Budi" in result
        finally:
            os.unlink(temp_path)
    
    def test_extract_csv_large(self):
        """Test CSV dengan banyak baris."""
        import tempfile
        lines = ["ID,Nama,Nilai"]
        for i in range(1, 501):
            lines.append(f"{i},Siswa{i},{80 + (i % 20)}")
        csv_content = "\n".join(lines)
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            result = ekstrak_teks_dari_csv(temp_path)
            assert result is not None
            result_lines = result.split('\n')
            assert len(result_lines) >= 100
            assert "Siswa1" in result
            assert "Siswa500" in result
        finally:
            os.unlink(temp_path)

class TestCsvUpload:
    def test_csv_statistics(self, tmp_path, monkeypatch):
        """Test upload CSV besar — pastikan ringkasan statistik berfungsi."""
        import saki_database
        
        db_path = tmp_path / "test.db"
        monkeypatch.setattr(saki_database, "DB_FILE", str(db_path))
        monkeypatch.setattr(saki_database, "DOCUMENTS_FOLDER", str(tmp_path))
        monkeypatch.setattr(saki_database, "CHROMA_FOLDER", str(tmp_path / "chroma"))
        saki_database.init_db()
        
        # Buat CSV 500 baris
        lines = ["ID,Nama,Nilai"]
        for i in range(1, 501):
            lines.append(f"{i},Siswa{i},{80 + (i % 20)}")
        csv_content = "\n".join(lines)
        
        # Mock ollama.chat
        import ollama
        def fake_chat(*args, **kwargs):
            # Cek prompt mengandung statistik
            prompt = kwargs.get('messages', [{}])[-1].get('content', '')
            assert 'Jumlah total baris' in prompt, "Prompt harus mengandung statistik"
            assert '10 baris pertama' in prompt, "Prompt harus mengandung 10 baris pertama"
            return {"message": {"content": "Ringkasan: File CSV dengan 500 baris data."}}
        monkeypatch.setattr(ollama, "chat", fake_chat)
        
        # Mock ChromaDB
        def fake_add(*args, **kwargs):
            return True
        monkeypatch.setattr(saki_database, "tambah_ke_chroma", fake_add)
        
        # Upload
        uploaded = DummyUpload("test_large.csv", csv_content.encode('utf-8'))
        doc_id, summary = proses_upload(uploaded)
        
        assert doc_id is not None
        assert "500" in summary or "Ringkasan" in summary

class TestExcelExtraction:
    def test_extract_xlsx(self):
        """Test ekstraksi Excel basic."""
        try:
            import openpyxl
        except ImportError:
            pytest.skip("openpyxl not installed")
        
        import tempfile
        from saki_files import ekstrak_teks_dari_xlsx
        
        # Buat file Excel sederhana
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Nama", "Usia"])
        ws.append(["Andi", 25])
        ws.append(["Budi", 30])
        
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            wb.save(f.name)
            temp_path = f.name
        
        try:
            result = ekstrak_teks_dari_xlsx(temp_path)
            assert result is not None
            assert "Nama" in result
            assert "Andi" in result
        finally:
            os.unlink(temp_path)