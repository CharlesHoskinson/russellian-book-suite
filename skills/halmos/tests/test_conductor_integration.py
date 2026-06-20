import pytest
pytestmark = pytest.mark.windows_canary
import json
from pathlib import Path
from scripts.concept_ledger import build_concept_ledger
from scripts.dispatch_halmos_review import build_payload, dispatch_halmos_review, _contract_purpose
from scripts.conductor import run_halmos


def _ws(tmp_path):
    ws = tmp_path / "ws"
    data = {
        "ch-01": "# C1\nIntelligence is not civilization.\n",
        "ch-02": "# C2\nThe previous chapter said intelligence is not civilization; institutions follow.\n",
    }
    for cid, body in data.items():
        d = ws / "chapters" / "drafts" / cid
        d.mkdir(parents=True)
        (d / "draft.md").write_text(body, encoding="utf-8")
    refs = ws / "references"; refs.mkdir(parents=True, exist_ok=True)
    (refs / "seed-concepts.txt").write_text("Institutions\n", encoding="utf-8")
    build_concept_ledger(ws, seed_path=refs / "seed-concepts.txt")
    return ws


def test_build_payload_includes_priors_digest(tmp_path):
    ws = _ws(tmp_path)
    p = build_payload(ws, "ch-02")
    assert p["chapter_id"] == "ch-02"
    assert [x["chapter_id"] for x in p["priors"]] == ["ch-01"]
    assert "draft" in p and "linkage" in p


def _contract(tmp_path, cid, text):
    ws = tmp_path / "ws"
    d = ws / "chapters" / "contracts"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{cid}.yaml").write_text(text, encoding="utf-8")
    return ws


def test_contract_purpose_ignores_nested_key(tmp_path):
    ws = _contract(tmp_path, "ch-01",
        "metadata:\n"
        "  author: x\n"
        "  purpose: nested decoy\n"
        "purpose: the real thesis\n")
    assert _contract_purpose(ws, "ch-01") == "the real thesis"


def test_contract_purpose_folds_block_scalar(tmp_path):
    ws = _contract(tmp_path, "ch-01",
        "purpose: >\n"
        "  first line of the thesis\n"
        "  second line of the thesis\n"
        "audience: reader\n")
    assert _contract_purpose(ws, "ch-01") == \
        "first line of the thesis second line of the thesis"


def test_build_payload_priors_carry_concept_source(tmp_path):
    ws = tmp_path / "ws"
    data = {
        "ch-01": "# C1\nInstitutions carry civilization forward.\n",
        "ch-02": "# C2\nThe institutions endure.\n",
    }
    for cid, body in data.items():
        d = ws / "chapters" / "drafts" / cid; d.mkdir(parents=True)
        (d / "draft.md").write_text(body, encoding="utf-8")
    refs = ws / "references"; refs.mkdir(parents=True, exist_ok=True)
    (refs / "seed-concepts.txt").write_text("Institutions\n", encoding="utf-8")
    build_concept_ledger(ws, seed_path=refs / "seed-concepts.txt")
    p = build_payload(ws, "ch-02")
    prior = next(x for x in p["priors"] if x["chapter_id"] == "ch-01")
    assert prior["introduces"], "expected ch-01 to introduce a concept"
    assert all("source" in i for i in prior["introduces"])
    assert any(i["source"] == "seed" for i in prior["introduces"])


def test_dispatch_requires_dispatcher(tmp_path):
    ws = _ws(tmp_path)
    with pytest.raises(ValueError):
        dispatch_halmos_review(ws, "ch-02", dispatcher=None)


def test_run_halmos_clean_seam_passes(tmp_path):
    ws = tmp_path / "ws3"
    data = {
        "ch-06": "# C6\nSettlement makes value real and final.\n",
        "ch-07": "# C7\nThat settlement of value carries into the airgap.\n",
    }
    for cid, body in data.items():
        d = ws / "chapters" / "drafts" / cid; d.mkdir(parents=True)
        (d / "draft.md").write_text(body, encoding="utf-8")
    refs = ws / "references"; refs.mkdir(parents=True, exist_ok=True)
    (refs / "seed-concepts.txt").write_text("Settlement\n", encoding="utf-8")

    def stub(payload):
        return {"spiral_coherence": "tight", "findings": [], "per_prior_chapter": {}}

    verdict = run_halmos(ws, "ch-07", dispatcher=stub, seed_path=refs / "seed-concepts.txt")
    assert verdict["halmos_critical_count"] == 0
    assert verdict["reviews_complete"] is True


def test_run_halmos_gates_on_broken_seam(tmp_path):
    ws = tmp_path / "ws2"
    data = {
        "ch-06": "# C6\nSettlement makes value real and final.\n",
        "ch-07": "# C7\nCall it the Authority Airgap; it separates power.\n",
    }
    for cid, body in data.items():
        d = ws / "chapters" / "drafts" / cid; d.mkdir(parents=True)
        (d / "draft.md").write_text(body, encoding="utf-8")
    refs = ws / "references"; refs.mkdir(parents=True, exist_ok=True)
    (refs / "seed-concepts.txt").write_text("Authority Airgap | the airgap\nSettlement\n", encoding="utf-8")

    def stub(payload):
        return {"spiral_coherence": "acceptable", "findings": [], "per_prior_chapter": {}}

    verdict = run_halmos(ws, "ch-07", dispatcher=stub, seed_path=refs / "seed-concepts.txt")
    assert verdict["halmos_critical_count"] == 1
    assert verdict["reviews_complete"] is True
