"""Tolerant reader for constraints.edn (both real on-disk shapes)."""
from __future__ import annotations
import textwrap
from scripts.governance._constraints import load_constraints


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text), encoding="utf-8")
    return p


def test_source_shape_forms(tmp_path):
    f = _write(tmp_path / "constraints.edn", """
        {:forms
         [(defconstraint C001-method-x
            :backend :z3
            :assert (= (:method-x :subj) 1)
            :track :claim/id
            :on-unsat {:defect :D1 :severity :critical :message "x"})
          (defconstraint C002-other
            :backend :z3
            :assert (= (:a :subj) (:b :subj))
            :on-unsat {:defect :D2 :severity :critical :message "y"})]}
    """)
    out = load_constraints(f)
    assert set(out) == {":C001-method-x", ":C002-other"}
    assert out[":C001-method-x"]["track"] == ":claim/id"
    assert out[":C002-other"]["track"] is None


def test_compiled_shape_vector_of_maps(tmp_path):
    f = _write(tmp_path / "constraints.edn", """
        {:version 1, :constraints
         [{:id "C001-method-x", :backend :z3, :assert (= (:m :s) 1),
           :tolerance nil, :track :claim/id,
           :on-unsat {:defect :D13, :severity :critical, :message "x"}}
          {:id "C007-tau", :backend :z3, :assert (= (:t :s) 1),
           :tolerance nil, :track :C007-tracker,
           :on-unsat {:defect :D13, :severity :critical, :message "y"}}]}
    """)
    out = load_constraints(f)
    assert set(out) == {":C001-method-x", ":C007-tau"}
    assert out[":C007-tau"]["track"] == ":C007-tracker"


def test_missing_file_returns_empty(tmp_path):
    assert load_constraints(tmp_path / "absent.edn") == {}
