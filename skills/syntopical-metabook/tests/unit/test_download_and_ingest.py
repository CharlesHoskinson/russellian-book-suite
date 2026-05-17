from pathlib import Path
from types import SimpleNamespace
from scripts.acquire.rank_candidates import ScoredCandidate
from scripts.acquire.download_and_ingest import download_and_ingest, IngestOutcome

def test_dedup_skips_already_ingested(tmp_path, monkeypatch):
    cand = ScoredCandidate("arxiv:x", 0.82)
    # Stub scrapling-fetch download to return a fake DownloadResult
    fake_dl = SimpleNamespace(path=tmp_path / "incoming" / "x.pdf",
                              sha256="abc", bytes=100, content_type="application/pdf")
    monkeypatch.setattr("scripts.acquire.download_and_ingest._download_pdf",
                        lambda url, dest: fake_dl)
    monkeypatch.setattr("scripts.acquire.download_and_ingest._resolve_pdf_url",
                        lambda cand_id: f"https://x/{cand_id}.pdf")
    monkeypatch.setattr("scripts.acquire.download_and_ingest._is_source_ingested",
                        lambda sha, root: True)  # dedup hit
    outcomes = download_and_ingest([cand], workspace_root=tmp_path)
    assert outcomes[0].status == "already_present"

def test_successful_download_and_ingest(tmp_path, monkeypatch):
    cand = ScoredCandidate("arxiv:y", 0.85)
    fake_dl = SimpleNamespace(path=tmp_path / "incoming" / "y.pdf",
                              sha256="def", bytes=200, content_type="application/pdf")
    monkeypatch.setattr("scripts.acquire.download_and_ingest._resolve_pdf_url",
                        lambda cand_id: f"https://x/{cand_id}.pdf")
    monkeypatch.setattr("scripts.acquire.download_and_ingest._download_pdf",
                        lambda url, dest: fake_dl)
    monkeypatch.setattr("scripts.acquire.download_and_ingest._is_source_ingested",
                        lambda sha, root: False)
    monkeypatch.setattr("scripts.acquire.download_and_ingest._ingest_pdf",
                        lambda src, root: SimpleNamespace(
                            source_id="src-y", sha256="def", claims_extracted=0,
                            wiki_pages_touched=[], status="ingested"))
    outcomes = download_and_ingest([cand], workspace_root=tmp_path)
    assert outcomes[0].status == "ingested"
    assert outcomes[0].sha256 == "def"
