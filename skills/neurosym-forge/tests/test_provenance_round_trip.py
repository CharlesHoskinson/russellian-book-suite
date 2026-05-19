"""REQ-PROV-040..047: ProvenanceSidecar round-trip and validation tests.

These tests cover the PROV-O sidecar that companions
`rules/booklogic/induced-theory.edn`. Byte-stable round-trip is the
contract: write -> read -> write must produce identical bytes (sorted
keys, stable list ordering, no scientific-notation floats).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._provenance import ProvenanceSidecar, ProvenanceSidecarError


def _full_prov_entry(suffix: str = "") -> dict:
    """Return a complete provenance entry with every required and optional key."""
    return {
        ":prov/derived-from-atoms": [f"c-{suffix}-1", f"c-{suffix}-2"],
        ":prov/source-documents": [f"pmid:{suffix}1", f"pmid:{suffix}2"],
        ":prov/contradiction-atoms": [f"c-{suffix}-99"],
        ":prov/proposed-by": {
            ":lineage": ":llm",
            ":model": "claude-haiku-4-5",
            ":provider": ":anthropic",
        },
        ":prov/validated-by": [
            {":backend": ":z3", ":held-out-folds": 5,
             ":sat-rate": 0.89, ":tolerance-fit": 0.043},
            {":backend": ":cozo", ":support-rate": 0.94},
        ],
        ":prov/entrenchment": 0.83,
        ":prov/status": ":active",
        ":prov/llm-repair-calls": 2,
        ":prov/cost-usd": 0.018,
        ":prov/semantic-neighbours": [f"c-{suffix}-203", f"c-{suffix}-411"],
        ":prov/induced-from-corpus":
            "verifiers/adsc-clinical/fixtures/claims_clean.jsonl",
    }


def _minimal_prov_entry() -> dict:
    """Return only the REQ-PROV-041 required keys (no optional fields)."""
    return {
        ":prov/derived-from-atoms": ["c-1", "c-2"],
        ":prov/source-documents": ["pmid:1"],
        ":prov/contradiction-atoms": [],
        ":prov/proposed-by": {
            ":lineage": ":llm",
            ":model": "claude-haiku-4-5",
            ":provider": ":anthropic",
        },
        ":prov/validated-by": [
            {":backend": ":z3", ":held-out-folds": 5, ":sat-rate": 0.91},
        ],
        ":prov/entrenchment": 0.75,
        ":prov/status": ":active",
        ":prov/llm-repair-calls": 1,
        ":prov/cost-usd": 0.012,
    }


# ---------------------------------------------------------------------------
# REQ-PROV-040: API shape
# ---------------------------------------------------------------------------

def test_sidecar_api_shape() -> None:
    """REQ-PROV-040: ProvenanceSidecar exposes the documented method set."""
    s = ProvenanceSidecar()
    assert hasattr(s, "add_rule_provenance")
    assert hasattr(s, "lookup")
    assert hasattr(s, "iter_rules")
    assert hasattr(s, "remove_rule")
    assert hasattr(s, "save")
    assert callable(ProvenanceSidecar.load)


def test_lookup_returns_none_for_unknown() -> None:
    s = ProvenanceSidecar()
    assert s.lookup(":induced/nope") is None


def test_iter_rules_empty() -> None:
    assert list(ProvenanceSidecar().iter_rules()) == []


def test_add_and_lookup_round_trip() -> None:
    s = ProvenanceSidecar()
    entry = _minimal_prov_entry()
    s.add_rule_provenance(":induced/r1", entry)
    assert s.lookup(":induced/r1") == entry


def test_remove_rule() -> None:
    s = ProvenanceSidecar()
    s.add_rule_provenance(":induced/r1", _minimal_prov_entry())
    s.remove_rule(":induced/r1")
    assert s.lookup(":induced/r1") is None


def test_remove_unknown_rule_is_idempotent() -> None:
    s = ProvenanceSidecar()
    s.remove_rule(":induced/nope")  # no raise


# ---------------------------------------------------------------------------
# REQ-PROV-041: Required fields + validation
# ---------------------------------------------------------------------------

def test_required_fields_present() -> None:
    """REQ-PROV-041: missing a required key raises ValueError."""
    s = ProvenanceSidecar()
    bad = _minimal_prov_entry()
    del bad[":prov/entrenchment"]
    with pytest.raises(ValueError, match="entrenchment"):
        s.add_rule_provenance(":induced/r1", bad)


def test_unknown_key_rejected() -> None:
    """REQ-PROV-041: unknown key outside the closed schema raises ValueError."""
    s = ProvenanceSidecar()
    bad = _minimal_prov_entry()
    bad[":prov/not-a-real-key"] = "oops"
    with pytest.raises(ValueError, match="unknown"):
        s.add_rule_provenance(":induced/r1", bad)


def test_status_enum_enforced() -> None:
    """REQ-PROV-041: status must be one of :active, :tentative, :quarantined."""
    s = ProvenanceSidecar()
    bad = _minimal_prov_entry()
    bad[":prov/status"] = ":bogus"
    with pytest.raises(ValueError, match="status"):
        s.add_rule_provenance(":induced/r1", bad)


def test_repair_calls_range() -> None:
    """REQ-PROV-041: llm-repair-calls outside [0, 3] raises ValueError."""
    s = ProvenanceSidecar()
    bad = _minimal_prov_entry()
    bad[":prov/llm-repair-calls"] = 4
    with pytest.raises(ValueError, match="repair"):
        s.add_rule_provenance(":induced/r1", bad)


def test_entrenchment_range() -> None:
    """REQ-PROV-041: entrenchment outside [0.0, 1.0] raises ValueError."""
    s = ProvenanceSidecar()
    bad = _minimal_prov_entry()
    bad[":prov/entrenchment"] = 1.5
    with pytest.raises(ValueError, match="entrenchment"):
        s.add_rule_provenance(":induced/r1", bad)


def test_cost_usd_nonnegative() -> None:
    s = ProvenanceSidecar()
    bad = _minimal_prov_entry()
    bad[":prov/cost-usd"] = -0.01
    with pytest.raises(ValueError, match="cost"):
        s.add_rule_provenance(":induced/r1", bad)


def test_status_active_accepted() -> None:
    s = ProvenanceSidecar()
    e = _minimal_prov_entry()
    e[":prov/status"] = ":active"
    s.add_rule_provenance(":induced/r1", e)


def test_status_tentative_accepted() -> None:
    s = ProvenanceSidecar()
    e = _minimal_prov_entry()
    e[":prov/status"] = ":tentative"
    s.add_rule_provenance(":induced/r1", e)


def test_status_quarantined_accepted() -> None:
    s = ProvenanceSidecar()
    e = _minimal_prov_entry()
    e[":prov/status"] = ":quarantined"
    s.add_rule_provenance(":induced/r1", e)


# ---------------------------------------------------------------------------
# REQ-PROV-042: Optional semantic neighbours
# ---------------------------------------------------------------------------

def test_semantic_neighbours_optional_round_trip(tmp_path: Path) -> None:
    """REQ-PROV-042: semantic-neighbours (optional) round-trips when present."""
    s = ProvenanceSidecar()
    e = _minimal_prov_entry()
    e[":prov/semantic-neighbours"] = ["c-203", "c-411"]
    s.add_rule_provenance(":induced/r1", e)
    path = tmp_path / "induced-theory.prov.edn"
    s.save(path)
    s2 = ProvenanceSidecar.load(path)
    assert s2.lookup(":induced/r1")[":prov/semantic-neighbours"] == ["c-203", "c-411"]


def test_semantic_neighbours_capped_at_three() -> None:
    s = ProvenanceSidecar()
    e = _minimal_prov_entry()
    e[":prov/semantic-neighbours"] = ["a", "b", "c", "d"]
    with pytest.raises(ValueError, match="neighbours"):
        s.add_rule_provenance(":induced/r1", e)


# ---------------------------------------------------------------------------
# REQ-PROV-043: Top-level shape
# ---------------------------------------------------------------------------

def test_sidecar_file_path_and_top_level_shape(tmp_path: Path) -> None:
    """REQ-PROV-043: top-level shape is `{:version 1 :rules {<rule-id> {...}}}`."""
    s = ProvenanceSidecar()
    s.add_rule_provenance(":induced/r1", _minimal_prov_entry())
    path = tmp_path / "induced-theory.prov.edn"
    s.save(path)
    text = path.read_text(encoding="utf-8")
    assert ":version" in text
    assert ":rules" in text
    # Re-parse via the EDN reader and verify shape:
    from scripts._edn_reader import Keyword, read_edn
    parsed = read_edn(text)
    assert isinstance(parsed, dict)
    assert parsed[Keyword("version")] == 1
    assert Keyword("rules") in parsed


def test_empty_sidecar_persists_well_formed(tmp_path: Path) -> None:
    s = ProvenanceSidecar()
    path = tmp_path / "induced-theory.prov.edn"
    s.save(path)
    s2 = ProvenanceSidecar.load(path)
    assert list(s2.iter_rules()) == []


# ---------------------------------------------------------------------------
# REQ-PROV-044: Graceful degrade
# ---------------------------------------------------------------------------

def test_load_missing_raises_typed_error(tmp_path: Path) -> None:
    """REQ-PROV-044: missing sidecar raises ProvenanceSidecarError."""
    nonexistent = tmp_path / "does-not-exist.prov.edn"
    with pytest.raises(ProvenanceSidecarError) as excinfo:
        ProvenanceSidecar.load(nonexistent)
    assert str(nonexistent) in str(excinfo.value)


def test_load_malformed_raises_typed_error(tmp_path: Path) -> None:
    """REQ-PROV-044: malformed sidecar raises ProvenanceSidecarError with path."""
    path = tmp_path / "induced-theory.prov.edn"
    path.write_text("{not valid edn", encoding="utf-8")
    with pytest.raises(ProvenanceSidecarError) as excinfo:
        ProvenanceSidecar.load(path)
    assert str(path) in str(excinfo.value)


def test_load_missing_version_key_raises(tmp_path: Path) -> None:
    """REQ-PROV-044: missing :version raises ProvenanceSidecarError."""
    path = tmp_path / "induced-theory.prov.edn"
    path.write_text("{:rules {}}", encoding="utf-8")
    with pytest.raises(ProvenanceSidecarError, match="version"):
        ProvenanceSidecar.load(path)


def test_load_missing_rules_key_raises(tmp_path: Path) -> None:
    """REQ-PROV-044: missing :rules raises ProvenanceSidecarError."""
    path = tmp_path / "induced-theory.prov.edn"
    path.write_text("{:version 1}", encoding="utf-8")
    with pytest.raises(ProvenanceSidecarError, match="rules"):
        ProvenanceSidecar.load(path)


# ---------------------------------------------------------------------------
# REQ-PROV-045: Byte-stable round-trip — the canonical safety net
# ---------------------------------------------------------------------------

def test_round_trip_byte_stable_minimal(tmp_path: Path) -> None:
    """REQ-PROV-045: write -> read -> write produces identical bytes."""
    s = ProvenanceSidecar()
    s.add_rule_provenance(":induced/r1", _minimal_prov_entry())
    path = tmp_path / "induced-theory.prov.edn"
    s.save(path)
    first_bytes = path.read_bytes()

    s2 = ProvenanceSidecar.load(path)
    s2.save(path)
    second_bytes = path.read_bytes()

    assert first_bytes == second_bytes


def test_ten_rule_byte_stable_round_trip(tmp_path: Path) -> None:
    """REQ-PROV-045: 10-rule sidecar with every field round-trips byte-stable.

    Build sidecar with 10 rules, save, load, save again, and assert byte
    identity. Also assert each rule's prov dict equals the original via `==`.
    """
    original_entries = {
        f":induced/r{i:02d}": _full_prov_entry(suffix=str(i))
        for i in range(10)
    }
    s = ProvenanceSidecar()
    # Insertion order is intentionally non-sorted to confirm the writer
    # sorts at emit time regardless of insertion order.
    for rid in reversed(list(original_entries.keys())):
        s.add_rule_provenance(rid, original_entries[rid])

    path = tmp_path / "induced-theory.prov.edn"
    s.save(path)
    first_bytes = path.read_bytes()

    s2 = ProvenanceSidecar.load(path)
    s2.save(path)
    second_bytes = path.read_bytes()

    assert first_bytes == second_bytes, (
        "byte mismatch after re-save:\nfirst:\n"
        + first_bytes.decode("utf-8")
        + "\nsecond:\n"
        + second_bytes.decode("utf-8")
    )

    # Every rule's provenance dict must equal the original (==).
    for rid, expected in original_entries.items():
        got = s2.lookup(rid)
        assert got == expected, f"rule {rid} mismatch:\nexpected={expected!r}\ngot={got!r}"


def test_round_trip_preserves_list_order(tmp_path: Path) -> None:
    """REQ-PROV-045: list-valued fields preserve insertion order on round-trip."""
    s = ProvenanceSidecar()
    e = _minimal_prov_entry()
    e[":prov/derived-from-atoms"] = ["c-z", "c-a", "c-m", "c-b"]
    e[":prov/source-documents"] = ["pmid:99", "pmid:1", "pmid:50"]
    s.add_rule_provenance(":induced/r1", e)
    path = tmp_path / "induced-theory.prov.edn"
    s.save(path)
    s2 = ProvenanceSidecar.load(path)
    got = s2.lookup(":induced/r1")
    assert got[":prov/derived-from-atoms"] == ["c-z", "c-a", "c-m", "c-b"]
    assert got[":prov/source-documents"] == ["pmid:99", "pmid:1", "pmid:50"]


def test_floats_no_scientific_notation(tmp_path: Path) -> None:
    """REQ-PROV-045 / REQ-EDN-050: float fields must not use scientific notation."""
    import re
    s = ProvenanceSidecar()
    e = _minimal_prov_entry()
    e[":prov/cost-usd"] = 0.00000123  # would naturally produce '1.23e-06'
    e[":prov/entrenchment"] = 0.5
    s.add_rule_provenance(":induced/r1", e)
    path = tmp_path / "induced-theory.prov.edn"
    s.save(path)
    text = path.read_text(encoding="utf-8")
    # Match digit + 'e' + optional sign + digit, i.e. a real scientific
    # notation float — not the literal hyphens in keys like ":prov/cost-usd".
    sci_pattern = re.compile(r"\d[eE][+-]?\d")
    assert not sci_pattern.search(text), \
        f"scientific notation leaked: {text!r}"


# ---------------------------------------------------------------------------
# REQ-PROV-046: Per-corpus tracking
# ---------------------------------------------------------------------------

def test_induced_from_corpus_round_trip(tmp_path: Path) -> None:
    """REQ-PROV-046: :prov/induced-from-corpus round-trips when present."""
    s = ProvenanceSidecar()
    e = _minimal_prov_entry()
    e[":prov/induced-from-corpus"] = "verifiers/adsc-clinical/fixtures/claims_clean.jsonl"
    s.add_rule_provenance(":induced/r1", e)
    path = tmp_path / "induced-theory.prov.edn"
    s.save(path)
    s2 = ProvenanceSidecar.load(path)
    got = s2.lookup(":induced/r1")
    assert got[":prov/induced-from-corpus"] == \
        "verifiers/adsc-clinical/fixtures/claims_clean.jsonl"


def test_induced_from_corpus_optional_when_absent() -> None:
    """REQ-PROV-046: corpus field may be omitted on single-corpus projects."""
    s = ProvenanceSidecar()
    s.add_rule_provenance(":induced/r1", _minimal_prov_entry())
    got = s.lookup(":induced/r1")
    assert ":prov/induced-from-corpus" not in got
