import pytest
pytestmark = pytest.mark.windows_canary
import json
from pathlib import Path
from scripts.concept_ledger import build_concept_ledger
from scripts.build_linkage import build_linkage, seam_status, STOPWORDS, _load_concepts
from scripts.dispatch_halmos_review import _concepts_by_chapter


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


def test_seam_status_unknown_when_either_side_empty():
    assert seam_status("", "x") == ("unknown", [])
    assert seam_status("x", "") == ("unknown", [])


def test_first_chapter_seam_unknown_no_broken_flag(tmp_path):
    ws, seed = _ws(tmp_path, {
        "ch-01": "# C1\nIntelligence is not enough; Settlement makes value real.\n",
    })
    build_concept_ledger(ws, seed_path=seed)
    link = build_linkage(ws, "ch-01")
    assert link["seam"]["status"] == "unknown"
    assert not any(f["check"] == "broken-seam" for f in link["flags"])


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


def test_missing_draft_raises_clear_error(tmp_path):
    ws = tmp_path / "ws"
    (ws / "halmos").mkdir(parents=True)
    with pytest.raises(FileNotFoundError) as exc:
        build_linkage(ws, "ch-07")
    msg = str(exc.value)
    assert "ch-07" in msg and "draft" in msg
    assert not msg.startswith("[Errno")


def _write_concepts(ws, lines):
    d = ws / "halmos"; d.mkdir(parents=True, exist_ok=True)
    (d / "concepts.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_load_concepts_skips_malformed_lines(tmp_path):
    ws = tmp_path / "ws"
    good_a = json.dumps({"concept": "Settlement", "slug": "settlement", "introduced_in": "ch-06"})
    good_b = json.dumps({"concept": "Airgap", "slug": "airgap", "introduced_in": "ch-07"})
    _write_concepts(ws, [good_a, "{not valid json", "   ", good_b, ""])
    recs = _load_concepts(ws)
    slugs = {r["slug"] for r in recs}
    assert slugs == {"settlement", "airgap"}


def test_concepts_by_chapter_skips_malformed_lines(tmp_path):
    ws = tmp_path / "ws"
    good_a = json.dumps({"concept": "Settlement", "slug": "settlement",
                         "gloss": "g", "introduced_in": "ch-06"})
    good_b = json.dumps({"concept": "Airgap", "slug": "airgap",
                         "gloss": "g", "introduced_in": "ch-07"})
    _write_concepts(ws, [good_a, "garbage line", "  ", good_b])
    by = _concepts_by_chapter(ws)
    assert set(by) == {"ch-06", "ch-07"}
    assert by["ch-06"][0]["slug"] == "settlement"
