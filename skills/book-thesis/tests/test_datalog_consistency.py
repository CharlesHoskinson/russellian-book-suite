"""Tests for datalog_consistency.py.

Three round-trip cases:
  - direct contradiction (two claims, same subject, different value)
  - orphan paragraph (claim supports a node unreachable from :Thesis)
  - clean pass (well-formed thesis + non-conflicting verified claims)

Each test builds a minimal workspace under tmp_path, copies the shared thesis
TTL fixture into ``.knowledge/``, writes a custom ``claims/ledger.jsonl``, and
asserts on the resulting ``qa/datalog-defects.json``.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compile_thesis import compile_thesis  # noqa: E402
from datalog_consistency import run  # noqa: E402

FIXTURE_TTL = Path(__file__).parent / "fixtures" / "datalog_thesis.ttl"


def _make_workspace(tmp_path: Path, claims: list[dict]) -> Path:
    """Lay out a workspace with the shared thesis TTL and the given claim ledger.

    Thesis TTL lives at ``.knowledge/thesis-triples.ttl`` — the canonical path
    that ``compile_thesis.py`` writes to and every book-thesis script reads.
    Claims live at ``claims/ledger.jsonl`` — the canonical book-knowledge layout.
    """
    knowledge = tmp_path / ".knowledge"
    knowledge.mkdir(parents=True)
    shutil.copy(FIXTURE_TTL, knowledge / "thesis-triples.ttl")
    claims_dir = tmp_path / "claims"
    claims_dir.mkdir(parents=True)
    with (claims_dir / "ledger.jsonl").open("w", encoding="utf-8") as fh:
        for rec in claims:
            fh.write(json.dumps(rec) + "\n")
    return tmp_path


def _load_payload(workspace: Path) -> dict:
    return json.loads((workspace / "qa" / "datalog-defects.json").read_text(encoding="utf-8"))


def test_authored_invariant_fires_on_violating_claim(tmp_path: Path) -> None:
    """An author-declared invariant (formal: claims(P, subj, V), V != lit) is
    compiled by compile_thesis and enforced by datalog_consistency: a verified
    claim whose subject=subj asserts a value != lit raises a D11
    invariant_violation. Compiles the thesis YAML end-to-end (no hand-written
    TTL) so the schema's "Compiled to Datalog rules" promise is exercised."""
    (tmp_path / "thesis").mkdir()
    (tmp_path / "thesis" / "inv.yaml").write_text(
        "book_id: inv\n"
        "thesis:\n"
        "  statement: Invariant test thesis.\n"
        "  polarity: descriptive\n"
        "sub_arguments:\n"
        "  - id: only-leg\n"
        "    parent: thesis\n"
        "    statement: The only leg.\n"
        "    advanced_by_chapters: [ch-01]\n"
        "invariants:\n"
        "  - id: parish-count\n"
        "    rule: Bermuda has nine parishes.\n"
        "    formal: |\n"
        "      contradicts(P, parish_count_canonical) :-\n"
        "        claims(P, parish_count, N), N != 9.\n",
        encoding="utf-8",
    )
    compile_thesis(tmp_path, "inv")
    (tmp_path / "claims").mkdir()
    (tmp_path / "claims" / "ledger.jsonl").write_text(
        json.dumps({"claim_id": "clm-bad", "status": "verified",
                    "subject": "parish_count", "value": 7}) + "\n"
        + json.dumps({"claim_id": "clm-ok", "status": "verified",
                      "subject": "parish_count", "value": 9}) + "\n",
        encoding="utf-8",
    )
    report = run(tmp_path)
    payload = _load_payload(tmp_path)
    viol = [d for d in payload["defects"] if d["rule"] == "invariant_violation"]
    assert any("clm-bad" in d["facts"] and "parish-count" in d["facts"] for d in viol), payload["defects"]
    # The conforming claim (value == 9) must NOT trip the invariant.
    assert not any("clm-ok" in d["facts"] for d in viol)
    assert all(d["class"] == "D11" for d in viol)
    assert report.gate_failed()


def test_sub_arg_with_no_advancing_chapter_is_not_d12(tmp_path: Path) -> None:
    """The datalog chapter-advances check is a DISTINCT defect from lint_supports'
    paragraph-supports D12. A sub-argument advanced by no chapter is reported as
    a D11 invariant (rule sub_arg_no_chapter), never as class D12 — D12 is owned
    by lint_supports / book-qa (paragraph-supports semantics)."""
    # Build a thesis TTL where third-leg has no :advancedBy edge.
    knowledge = tmp_path / ".knowledge"
    knowledge.mkdir(parents=True)
    ttl = FIXTURE_TTL.read_text(encoding="utf-8") + (
        '\n:third-leg a :SubArgument ;\n'
        '    :supports :Thesis ;\n'
        '    :statement "Third leg, no chapter advances it." .\n'
    )
    (knowledge / "thesis-triples.ttl").write_text(ttl, encoding="utf-8")
    (tmp_path / "claims").mkdir()
    (tmp_path / "claims" / "ledger.jsonl").write_text("", encoding="utf-8")

    run(tmp_path)
    payload = _load_payload(tmp_path)
    # No defect should carry class D12 from the datalog tool.
    assert all(d["class"] != "D12" for d in payload["defects"]), payload["defects"]
    no_chapter = [d for d in payload["defects"] if d["rule"] == "sub_arg_no_chapter"]
    assert any(d["facts"] == ["third-leg"] for d in no_chapter), payload["defects"]
    assert all(d["class"] == "D11" for d in no_chapter)


def test_detects_direct_contradiction(tmp_path: Path) -> None:
    """Two verified claims share a subject but assert different values."""
    ws = _make_workspace(tmp_path, [
        {"claim_id": "clm-a", "status": "verified", "subject": "parish_count",
         "value": 9, "supports_nodes": ["first-leg"]},
        {"claim_id": "clm-b", "status": "verified", "subject": "parish_count",
         "value": 10, "supports_nodes": ["second-leg"]},
    ])
    report = run(ws)
    payload = _load_payload(ws)
    assert payload["summary"]["contradictions"] >= 1
    rules = {d["rule"] for d in payload["defects"] if d["class"] == "D10"}
    assert "direct_contradiction" in rules
    pair = next(d["facts"] for d in payload["defects"] if d["rule"] == "direct_contradiction")
    assert set(pair) == {"clm-a", "clm-b"}
    assert report.gate_failed()


def test_detects_orphan(tmp_path: Path) -> None:
    """Claim supports a node that exists nowhere in the thesis tree."""
    ws = _make_workspace(tmp_path, [
        {"claim_id": "clm-good", "status": "verified", "subject": "source-alpha",
         "value": "ok", "supports_nodes": ["first-leg"]},
        {"claim_id": "clm-lost", "status": "verified", "subject": "source-beta",
         "value": "ok", "supports_nodes": ["floating-leg"]},
    ])
    run(ws)
    payload = _load_payload(ws)
    orphans = [d for d in payload["defects"] if d["rule"] == "orphan_paragraph"]
    assert any("clm-lost" in d["facts"] for d in orphans)
    # The good claim should not be flagged as orphan.
    assert not any("clm-good" in d["facts"] for d in orphans)
    # Unreachable supports invariant should fire on the lost claim.
    invariants = [d for d in payload["defects"] if d["rule"] == "unreachable_supports"]
    assert any("clm-lost" in d["facts"] for d in invariants)


def test_detects_transitive_contradiction(tmp_path: Path) -> None:
    """Headline Layer-4 capability: A implies B, B directly contradicts C, so A
    transitively contradicts C. Exercises the implies-driven branch of the
    transitive_contradiction rule and the dedup against direct contradictions."""
    ws = _make_workspace(tmp_path, [
        # B and C directly contradict (same subject, different value).
        {"claim_id": "clm-b", "status": "verified", "subject": "bmd_usd_rate",
         "value": 1.0, "supports_nodes": ["first-leg"]},
        {"claim_id": "clm-c", "status": "verified", "subject": "bmd_usd_rate",
         "value": 1.5, "supports_nodes": ["second-leg"]},
        # A implies B, so A transitively contradicts C.
        {"claim_id": "clm-a", "status": "verified", "subject": "peg_policy",
         "value": "fixed", "implies": ["clm-b"], "supports_nodes": ["first-leg"]},
    ])
    report = run(ws)
    payload = _load_payload(ws)
    d10 = {d["rule"] for d in payload["defects"] if d["class"] == "D10"}
    assert "transitive_contradiction" in d10
    # The transitive edge A<->C must be present and distinct from the direct B<->C.
    trans = [d["facts"] for d in payload["defects"]
             if d["rule"] == "transitive_contradiction"]
    assert any(set(f) == {"clm-a", "clm-c"} for f in trans)
    # Dedup: the direct B<->C pair must NOT be re-emitted as transitive.
    assert not any(set(f) == {"clm-b", "clm-c"} for f in trans)
    assert report.gate_failed()


def test_real_shape_claims_are_not_orphans(tmp_path: Path) -> None:
    """Verified claims with no supports edge (the real ledger shape) must not
    be reported as orphan paragraphs. Only manuscript paragraphs that *do*
    declare a supports edge are subject to the reachability check."""
    ws = _make_workspace(tmp_path, [
        {"claim_id": "clm-2026-000010", "status": "verified",
         "canonical_text": "A real ledger claim with no supports edge.",
         "claim_type": "fact", "confidence": 0.9,
         "supports_chapters": ["ch-01"]},
        {"claim_id": "clm-2026-000011", "status": "verified",
         "canonical_text": "Another real ledger claim, no supports edge.",
         "claim_type": "fact", "confidence": 0.9,
         "supports_chapters": ["ch-02"]},
    ])
    report = run(ws)
    payload = _load_payload(ws)
    assert payload["summary"]["orphans"] == 0, payload["defects"]
    assert not report.gate_failed()


def test_detects_missing_evidence(tmp_path: Path) -> None:
    """A required-evidence slot named by a sub-argument but never met by any
    claim's subject is reported as a D11 missing-evidence invariant violation.
    The fixture declares source-alpha (first-leg) and source-beta (second-leg);
    here only source-alpha is met, so second-leg's slot is unmet."""
    ws = _make_workspace(tmp_path, [
        {"claim_id": "clm-a", "status": "verified", "subject": "source-alpha",
         "value": "ok", "supports_nodes": ["first-leg"]},
    ])
    report = run(ws)
    payload = _load_payload(ws)
    missing = [d for d in payload["defects"] if d["rule"] == "missing_evidence"]
    assert any(d["facts"] == ["second-leg", "source-beta"] for d in missing), payload["defects"]
    assert all(d["class"] == "D11" for d in missing)
    # source-alpha is met, so first-leg's slot must NOT be flagged.
    assert not any("source-alpha" in d["facts"] for d in missing)
    assert report.gate_failed()


def test_clean_pass(tmp_path: Path) -> None:
    """Well-formed claim set + thesis tree should produce zero gate-failing defects."""
    ws = _make_workspace(tmp_path, [
        {"claim_id": "clm-x", "status": "verified", "subject": "source-alpha",
         "value": "ok", "supports_nodes": ["first-leg"], "supports_chapters": ["ch-01"]},
        {"claim_id": "clm-y", "status": "verified", "subject": "source-beta",
         "value": "ok", "supports_nodes": ["second-leg"], "supports_chapters": ["ch-02"]},
    ])
    report = run(ws)
    payload = _load_payload(ws)
    assert payload["summary"]["contradictions"] == 0
    assert payload["summary"]["invariant_violations"] == 0
    assert payload["summary"]["orphans"] == 0
    assert not report.gate_failed()


# H-05 (3.1/3.2): structured subject/value come from a thesis-side projection,
# NOT from non-schema fields on the claim record (the schema is
# additionalProperties:false, so subject/value/implies cannot live on a claim).
def _valid_claim(cid: str, text: str) -> dict:
    return {"claim_id": cid, "canonical_text": text, "status": "verified",
            "claim_type": "fact", "confidence": 0.9,
            "source_spans": [{"doc_id": "d", "locator_text": "loc1"}],
            "created_at": "2026-05-11T00:00:00Z"}


def _write_claim_facts(workspace: Path, mapping: dict) -> None:
    import yaml
    thesis_dir = workspace / "thesis"
    thesis_dir.mkdir(parents=True, exist_ok=True)
    (thesis_dir / "claim-facts.yaml").write_text(
        yaml.safe_dump({"claim_facts": mapping}), encoding="utf-8")


def test_schema_valid_claims_trip_d10_via_projection(tmp_path: Path) -> None:
    """A schema-valid record carrying no subject/value must still trip D10 when a
    claim-facts projection supplies the structured (subject, value)."""
    ws = _make_workspace(tmp_path, [
        _valid_claim("clm-a", "Bermuda has nine parishes."),
        _valid_claim("clm-b", "Bermuda has ten parishes."),
    ])
    _write_claim_facts(ws, {
        "clm-a": {"subject": "parish_count", "value": 9},
        "clm-b": {"subject": "parish_count", "value": 10},
    })
    run(ws)
    payload = _load_payload(ws)
    assert payload["summary"]["contradictions"] >= 1
    d10 = {d["rule"] for d in payload["defects"] if d["class"] == "D10"}
    assert "direct_contradiction" in d10


def test_projection_claims_are_schema_valid(tmp_path: Path) -> None:
    """3.2: the records driving the projection-based D10 test carry only
    schema-allowed keys (claim-record.schema.json is additionalProperties:false)
    and all required keys — i.e. no subject/value/implies smuggled onto the record."""
    schema = json.loads(
        (ROOT.parent / "book-knowledge" / "assets" / "claim-record.schema.json")
        .read_text(encoding="utf-8"))
    allowed = set(schema["properties"])
    required = set(schema["required"])
    assert schema.get("additionalProperties") is False
    for c in (_valid_claim("clm-a", "Bermuda has nine parishes."),
              _valid_claim("clm-b", "Bermuda has ten parishes.")):
        extra = set(c) - allowed
        assert not extra, f"non-schema keys on claim record: {extra}"
        assert required <= set(c), f"missing required keys: {required - set(c)}"
