"""5.2: round-trip / idempotency tests for canonical-artifact writers."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import process_footnotes as pf  # noqa: E402
import synthesize_bermuda_ledger as sbl  # noqa: E402


def test_process_manuscript_is_idempotent():
    """Re-processing already-converted footnotes is a no-op (GFM refs are gone)."""
    md = ("# Chapter 1: Opening\n\nA sentence with a note[^a].\n\n"
          "## Notes\n\n[^a]: the definition.\n")
    once = pf.process_manuscript(md)
    twice = pf.process_manuscript(once)
    assert twice == once


def test_synthesize_refuses_to_clobber_existing_ledger(tmp_path):
    """synthesize is idempotent: a populated ledger is left untouched on re-run."""
    ws = tmp_path / "ws"
    (ws / "thesis").mkdir(parents=True)
    (ws / "thesis" / "bermuda-manual.yaml").write_text("title: bermuda\n", encoding="utf-8")
    (ws / "claims").mkdir(parents=True)
    ledger = ws / "claims" / "ledger.jsonl"
    ledger.write_text('{"claim_id": "clm-2026-000001"}\n', encoding="utf-8")
    before = ledger.read_text(encoding="utf-8")
    rc = sbl.synthesize(ws)
    assert rc == 0
    assert ledger.read_text(encoding="utf-8") == before
