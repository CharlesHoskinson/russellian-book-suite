"""Template-shape tests for the scaffolded Rust addon.

These tests verify the .tmpl files have the right structure to produce a
Rust crate that actually verifies (calls Z3, asserts axioms, tracks atoms
for unsat-core extraction). They do not build Rust; they only string-search
the template content.
"""
from __future__ import annotations

from pathlib import Path

import pytest


TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "assets" / "project-template"
RUST_SRC = TEMPLATE_ROOT / "rust-verifier" / "src"


def _read(name: str) -> str:
    p = RUST_SRC / name if not name.startswith("Cargo") else TEMPLATE_ROOT / "rust-verifier" / name
    return p.read_text(encoding="utf-8")


def test_axioms_template_exists() -> None:
    assert (RUST_SRC / "axioms.rs.tmpl").exists()


def test_axioms_template_is_no_op() -> None:
    """The default scaffold ships a no-op axioms hook; projects override it."""
    text = _read("axioms.rs.tmpl")
    assert "pub fn assert_axioms" in text
    # No-op body: either empty `{}`, a comment-only body, or `()` returned.
    # We assert it does NOT do anything dangerous like calling Z3 directly.
    assert "solver.assert" not in text


def test_smt_template_calls_axioms_hook() -> None:
    text = _read("smt.rs.tmpl")
    assert "crate::axioms::assert_axioms" in text or "axioms::assert_axioms" in text, \
        "smt.rs.tmpl must call axioms::assert_axioms"


def test_smt_template_uses_assert_and_track() -> None:
    text = _read("smt.rs.tmpl")
    assert "assert_and_track" in text, \
        "smt.rs.tmpl must use assert_and_track for unsat-core extraction"


def test_lib_template_pdf_is_feature_gated() -> None:
    """render_pdf and the typeset mod must be gated under `pdf` feature."""
    text = _read("lib.rs.tmpl")
    # render_pdf entry point gated
    pdf_gate_idx = text.find("#[cfg(feature = \"pdf\")]")
    render_pdf_idx = text.find("pub fn render_pdf")
    assert pdf_gate_idx != -1, "lib.rs.tmpl missing #[cfg(feature = \"pdf\")]"
    assert render_pdf_idx != -1
    assert pdf_gate_idx < render_pdf_idx, "feature gate must precede render_pdf"


def test_cargo_template_has_feature_flags() -> None:
    """Cargo.toml.tmpl must declare optional deps and a [features] section."""
    text = _read("Cargo.toml.tmpl")
    assert "[features]" in text
    assert "pdf" in text
    assert "default" in text
    # Optional deps
    assert "optional = true" in text


def test_cargo_template_tectonic_optional() -> None:
    text = _read("Cargo.toml.tmpl")
    # tectonic dep should be marked optional
    assert "tectonic" in text
    # Either explicitly `tectonic = { ... optional = true }` or in [features] dep:tectonic
    has_optional = (
        'tectonic = {' in text and 'optional = true' in text
    ) or 'dep:tectonic' in text
    assert has_optional, "tectonic must be optional in Cargo.toml.tmpl"


def test_ir_template_parses_atoms_array() -> None:
    """ir.rs.tmpl must parse the 'atoms' array from EDN-as-JSON, not return empty."""
    text = _read("ir.rs.tmpl")
    assert 'atoms' in text, "ir.rs.tmpl must reference the 'atoms' array"
    # The stub `Ok(Vec::new())` should be gone; serde_json should be used
    assert 'serde_json' in text or '"atoms"' in text
