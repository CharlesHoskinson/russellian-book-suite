"""REQ-VERIFIER-BUILD-043: scaffold template's smt.rs.tmpl ships with
the Z3 timeout config so every new verifier inherits the gate."""
from __future__ import annotations

from pathlib import Path

SMT_TMPL = (Path(__file__).resolve().parents[1]
            / "assets" / "project-template" / "rust-verifier" / "src" / "smt.rs.tmpl")


def test_smt_template_has_timeout_env_var() -> None:
    text = SMT_TMPL.read_text(encoding="utf-8")
    assert "VERIFIER_SOLVER_TIMEOUT_MS" in text, (
        "smt.rs.tmpl must reference the timeout env var so authors can override it"
    )


def test_smt_template_calls_set_params() -> None:
    text = SMT_TMPL.read_text(encoding="utf-8")
    assert "set_params" in text, (
        "smt.rs.tmpl must configure the solver via Params/set_params"
    )


def test_smt_template_imports_params() -> None:
    text = SMT_TMPL.read_text(encoding="utf-8")
    assert "Params" in text, (
        "smt.rs.tmpl must import z3::Params"
    )


def test_smt_template_default_is_30s() -> None:
    text = SMT_TMPL.read_text(encoding="utf-8")
    assert "30_000" in text or "30000" in text, (
        "smt.rs.tmpl default timeout should be 30,000 ms"
    )
