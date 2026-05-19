from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts._edn_reader import Keyword
from scripts._io import write_edn_file
from scripts.verdict_to_qa import translate

_KW_VERSION = Keyword("version")
_KW_VERDICT = Keyword("verdict")
_KW_CORE = Keyword("core")
_KW_REASON = Keyword("reason")


def test_sat_emits_empty_defects(fixtures_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "verification-defects.json"
    translate(fixtures_dir / "verdict_sat.edn", out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["verdict"] == "sat"
    assert payload["core"] == []


def test_unsat_passes_core_through(fixtures_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "verification-defects.json"
    translate(fixtures_dir / "verdict_unsat.edn", out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["verdict"] == "unsat"
    assert "clm-2026-000008" in payload["core"]
    assert payload["explanation"]


def test_missing_input_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        translate(tmp_path / "nonexistent.edn", tmp_path / "out.json")


def test_unknown_verdict_is_logged_not_gated(tmp_path: Path) -> None:
    inp = tmp_path / "unknown.edn"
    write_edn_file(inp, {
        _KW_VERSION: 1,
        _KW_VERDICT: Keyword("unknown"),
        _KW_CORE: [],
        _KW_REASON: "smt timeout",
    })
    out = tmp_path / "verification-defects.json"
    translate(inp, out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["verdict"] == "unknown"
    assert payload["core"] == []


def test_semantic_neighbours_empty_when_no_npz(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """REQ-RETRIEVAL-044: missing semantic-index.npz -> field is [],
    NOT a hard error.
    """
    out = tmp_path / "verification-defects.json"
    translate(fixtures_dir / "verdict_unsat.edn", out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["semantic_neighbours"] == []


def test_semantic_neighbours_populated_from_npz(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """REQ-RETRIEVAL-044: when .npz sits next to verdict.edn, each
    defect (core claim) gets a top_k list of neighbours.
    """
    pytest.importorskip("sentence_transformers")
    from scripts._semantic_index import SemanticIndex

    # Place a verdict + .npz side-by-side under tmp_path.
    work = tmp_path / "work"
    work.mkdir()
    verdict_src = (fixtures_dir / "verdict_unsat.edn").read_text(
        encoding="utf-8"
    )
    (work / "verdict.edn").write_text(verdict_src, encoding="utf-8")
    idx = SemanticIndex(cache_path=work / "semantic-index.npz")
    # Embed the core claims plus a few others.
    idx.embed_claim(
        claim_id="clm-2026-000008",
        text="ledger says 9 parishes in Bermuda",
    )
    idx.embed_claim(
        claim_id="prose-ch-02-001",
        text="chapter 2 prose claims 8 parishes",
    )
    idx.embed_claim(
        claim_id="clm-2026-000009",
        text="another parish-count claim from the ledger",
    )
    idx.embed_claim(
        claim_id="clm-2026-000010",
        text="unrelated population census from 1970",
    )
    idx.save()

    out = tmp_path / "verification-defects.json"
    translate(work / "verdict.edn", out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert len(payload["semantic_neighbours"]) == 2
    by_id = {
        n["defect_claim_id"]: n for n in payload["semantic_neighbours"]
    }
    # Each defect carries up to 3 OTHER claims (self excluded).
    for entry in payload["semantic_neighbours"]:
        ids = [t["claim"] for t in entry["top_k"]]
        assert entry["defect_claim_id"] not in ids
        assert len(ids) <= 3
