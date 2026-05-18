import hashlib
import pytest
from scripts.download import download_pdf, DownloadResult
from scripts.exceptions import NotAPdf

def test_download_pdf_writes_file_and_checksums(monkeypatch, tmp_path):
    payload = b"%PDF-1.7\n..." + b"\x00" * 1024
    class FakeStream:
        headers = {"content-type": "application/pdf"}
        def iter_bytes(self, chunk_size=8192):
            yield payload
        def __enter__(self): return self
        def __exit__(self, *a): pass
    class FakeSession:
        def stream(self, url): return FakeStream()
    monkeypatch.setattr("scripts.download._session_for_stream", lambda: FakeSession())
    dest = tmp_path / "p.pdf"
    r = download_pdf("https://x/p.pdf", dest)
    assert isinstance(r, DownloadResult)
    assert r.bytes == len(payload)
    assert r.sha256 == hashlib.sha256(payload).hexdigest()
    assert r.content_type == "application/pdf"
    assert dest.read_bytes() == payload

def test_download_pdf_rejects_non_pdf(monkeypatch, tmp_path):
    class FakeStream:
        headers = {"content-type": "text/html"}
        def iter_bytes(self, chunk_size=8192): yield b"<html/>"
        def __enter__(self): return self
        def __exit__(self, *a): pass
    class FakeSession:
        def stream(self, url): return FakeStream()
    monkeypatch.setattr("scripts.download._session_for_stream", lambda: FakeSession())
    dest = tmp_path / "p.pdf"
    with pytest.raises(NotAPdf):
        download_pdf("https://x/p.pdf", dest)
    assert not dest.exists(), "partial file must be deleted on NotAPdf"
