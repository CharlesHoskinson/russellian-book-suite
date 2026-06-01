import pytest
pytestmark = pytest.mark.windows_canary
import json
from pathlib import Path
from scripts.concept_ledger import build_concept_ledger
from scripts.build_linkage import build_linkage, seam_status, STOPWORDS


def _ws(tmp_path, chapters):
    ws = tmp_path / "ws"
    for cid, body in chapters.items():
        d = ws / "chapters" / "drafts" / cid
        d.mkdir(parents=True)
        (d / "draft.md").write_text(body, encoding="utf-8")
    seed = ws / "references"; seed.mkdir(parents=True, exist_ok=True)
    (seed / "seed-concepts.txt").write_text(
        "Authority Airgap | the airgap\nSettlement\n", encoding="utf-8")
    return ws, seed / "seed-concepts.txt"


def test_seam_status_clean_when_overlap(tmp_path):
    status, overlap = seam_status(
        "the question turns to the Bounded Polis.",
        "The previous chapter left the Bounded Polis question open.")
    assert status == "clean"
    assert "bounded" in overlap or "polis" in overlap


def test_seam_status_broken_when_no_overlap():
    status, overlap = seam_status("a sentence about settlement and value.",
                                  "An unrelated opening about weather and traffic.")
    assert status == "broken"


def test_inventory_and_broken_seam(tmp_path):
    ws, seed = _ws(tmp_path, {
        "ch-06": "# C6\nSettlement makes value real and final.\n",
        "ch-07": "# C7\nCall it the Authority Airgap; it separates power.\n",
    })
    build_concept_ledger(ws, seed_path=seed)
    link = build_linkage(ws, "ch-07")
    assert "authority-airgap" in link["references"] or "authority-airgap" in link["introduces"]
    assert link["seam"]["status"] == "broken"
    assert any(f["check"] == "broken-seam" and f["severity"] == "critical" for f in link["flags"])
    p = ws / "halmos" / "linkage" / "ch-07.json"
    assert json.loads(p.read_text(encoding="utf-8"))["chapter_id"] == "ch-07"
