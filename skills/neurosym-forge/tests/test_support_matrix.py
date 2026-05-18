"""REQ-BOOKLOGIC-049, REQ-BOOKLOGIC-050: SUPPORT_MATRIX.md agrees with
codegen reality. The lint parses both sources and fails if they drift.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "SUPPORT_MATRIX.md"
CODEGEN_AXIOMS = ROOT / "scripts" / "codegen_axioms.py"


def _matrix_row_status(form: str, backend: str | None = None) -> str | None:
    """Return the trailing 'Status' cell for a given form-family row.

    Matches rows like:
      | `defconstraint :backend :z3` | wired   | ... | wired  |
    """
    text = MATRIX.read_text(encoding="utf-8")
    needle = (f"`{form} :backend :{backend}`" if backend
              else f"`{form}`")
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        if needle in line:
            cells = [c.strip() for c in line.split("|") if c.strip()]
            return cells[-1] if cells else None
    return None


def test_matrix_file_exists():
    assert MATRIX.exists(), f"SUPPORT_MATRIX.md missing at {MATRIX}"


def test_matrix_rows_match_codegen_supported_backends():
    """REQ-BOOKLOGIC-049: the matrix's defconstraint rows enumerate
    every backend in SUPPORTED_BACKENDS."""
    code = CODEGEN_AXIOMS.read_text(encoding="utf-8")
    m = re.search(r"SUPPORTED_BACKENDS\s*=\s*\{([^}]*)\}", code)
    assert m, "SUPPORTED_BACKENDS not found in codegen_axioms.py"
    backends = sorted(re.findall(r'Keyword\("([^"]+)"\)', m.group(1)))
    assert backends == ["cozo", "egg", "z3"], (
        f"SUPPORTED_BACKENDS changed in codegen — update SUPPORT_MATRIX. Got: {backends}"
    )


def test_matrix_z3_is_wired():
    """REQ-BOOKLOGIC-050: matrix claims :z3 is the live path."""
    status = _matrix_row_status("defconstraint", "z3")
    assert status is not None, "matrix missing defconstraint :backend :z3 row"
    assert "wired" in status.lower(), (
        f"matrix claims :z3 status {status!r} but codegen wires it"
    )


def test_matrix_egg_is_wired_post_phase_h():
    """REQ-EQSAT-045: post-Phase-H, the matrix flips :egg to wired."""
    status = _matrix_row_status("defconstraint", "egg")
    assert status is not None, "matrix missing defconstraint :backend :egg row"
    assert "wired" in status.lower(), (
        f"matrix should report :egg as wired post-Phase-H; got {status!r}"
    )


def test_matrix_defrule_is_wired_post_phase_h():
    """REQ-EQSAT-045: post-Phase-H, the matrix flips defrule to wired."""
    status = _matrix_row_status("defrule")
    assert status is not None, "matrix missing defrule row"
    assert "wired" in status.lower(), (
        f"matrix should report defrule as wired post-Phase-H; got {status!r}"
    )


def test_matrix_cozo_is_wired():
    """REQ-DATALOG-045: after Tier 3, :cozo constraints route through
    `_emit_cozo_block` into `axioms::cozo_constraints` and lib.rs runs
    each through `kg::evaluate_constraint`. The matrix must say wired.
    """
    status = _matrix_row_status("defconstraint", "cozo")
    assert status is not None, "matrix missing defconstraint :backend :cozo row"
    assert "wired" in status.lower(), (
        f"matrix claims :cozo status {status!r} — Tier 3 promoted "
        f":cozo to wired (REQ-DATALOG-041)"
    )


def test_matrix_defquery_is_wired():
    """REQ-DATALOG-045: after Tier 3, `defquery` forms run at smoke
    time via `kg::run_queries` and surface on the verdict."""
    status = _matrix_row_status("defquery")
    assert status is not None, "matrix missing defquery row"
    assert "wired" in status.lower() and "wired-builder" not in status.lower(), (
        f"matrix claims defquery status {status!r} — Tier 3 promoted "
        f"defquery to wired (REQ-DATALOG-040)"
    )


def test_matrix_defremedy_is_query_bound():
    """REQ-DATALOG-045: after Tier 3, `defremedy` whose `:when` references
    a `defquery` receives the query's row count via `verdict_to_qa.py`.
    """
    status = _matrix_row_status("defremedy")
    assert status is not None, "matrix missing defremedy row"
    s = status.lower()
    assert "wired" in s and "query-bound" in s, (
        f"matrix claims defremedy status {status!r} — Tier 3 promoted "
        f"defremedy to wired (query-bound) (REQ-DATALOG-043)"
    )


def test_codegen_dispatches_egg_and_cozo_post_tier3():
    """REQ-EQSAT-041 + REQ-DATALOG-041: codegen dispatches `:egg` to
    `_emit_egg_block` and `:cozo` to `_emit_cozo_block`. No silent drop."""
    code = CODEGEN_AXIOMS.read_text(encoding="utf-8")
    # No remaining pre-Tier-3 silent-drop pattern.
    assert re.search(
        r"if\s+backend\s*!=\s*Keyword\(['\"]z3['\"]\)\s*:",
        code,
    ) is None, (
        "codegen_axioms.py still has the pre-Tier-3 "
        "`if backend != Keyword('z3'): continue` drop pattern."
    )
    # :egg dispatch wired.
    assert "_emit_egg_block" in code, (
        "codegen_axioms.py is missing _emit_egg_block — :egg backend is "
        "not actually wired despite SUPPORT_MATRIX claiming so."
    )
    # :cozo dispatch wired.
    assert "_emit_cozo_block" in code, (
        "codegen_axioms.py is missing _emit_cozo_block — Tier 3 :cozo "
        "promotion lost; update SUPPORT_MATRIX or codegen."
    )
    assert "cozo_constraints" in code, (
        "codegen_axioms.py no longer emits cozo_constraints() — Tier 3 "
        "promotion lost."
    )
