"""build_positions emits charter-driven positions for defconstraint rules."""
from __future__ import annotations
from pathlib import Path
from scripts.governance.build_positions import build_positions
from scripts.governance._positions_io import read_positions
from scripts.governance._stance import Stance


def _seed(ws: Path):
    (ws / "syntopical" / "schools").mkdir(parents=True)
    (ws / "knowledge" / "claims").mkdir(parents=True)
    (ws / "rules" / "booklogic").mkdir(parents=True)
    (ws / "syntopical" / "schools" / "school-a.edn").write_text(
        '{:version 1 :school :school-a :name "A" :charter "-" '
        ':members ["doc-a1"] :canonical-asserts [":C001-method-x"] :canonical-rejects []}',
        encoding="utf-8")
    (ws / "syntopical" / "schools" / "school-b.edn").write_text(
        '{:version 1 :school :school-b :name "B" :charter "-" '
        ':members ["doc-b1"] :canonical-asserts [] :canonical-rejects []}',
        encoding="utf-8")
    (ws / "knowledge" / "claims" / "ledger.jsonl").write_text(
        '{"claim_id":"clm-1","status":"verified","source_spans":[{"doc_id":"doc-a1"}]}\n',
        encoding="utf-8")
    (ws / "rules" / "booklogic" / "constraints.edn").write_text(
        '{:forms\n'
        ' [(defconstraint C001-method-x\n'
        '    :backend :z3\n'
        '    :assert (= (:method-x :subj) 1)\n'
        '    :track :claim/id\n'
        '    :on-unsat {:defect :D1 :severity :critical :message "x"})]}\n',
        encoding="utf-8")


def test_defconstraint_charter_assert_supports(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    _seed(ws)
    build_positions(ws, generated_at="2026-05-31T00:00:00Z")
    rows = read_positions(ws / "syntopical" / "positions.edn")
    c = {r.school: r for r in rows if r.rule_id == ":C001-method-x"}
    assert set(c) == {"school-a", "school-b"}
    assert all(r.source == "defconstraint" for r in c.values())
    assert c["school-a"].stance == Stance.SUPPORTS
    assert c["school-a"].declared_by_charter is True
    assert c["school-b"].stance == Stance.SILENT


def test_defconstraint_and_induced_coexist(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    _seed(ws)
    (ws / "rules" / "booklogic" / "induced-theory.prov.edn").write_text(
        '{:version 1 :rules {":induced/r-001" '
        '{:prov/derived-from-atoms ["clm-1"] '
        ':prov/source-documents ["doc-a1"] '
        ':prov/contradiction-atoms []}}}',
        encoding="utf-8")
    build_positions(ws, generated_at="2026-05-31T00:00:00Z")
    rows = read_positions(ws / "syntopical" / "positions.edn")
    assert {r.source for r in rows} == {"defconstraint", "induced"}
