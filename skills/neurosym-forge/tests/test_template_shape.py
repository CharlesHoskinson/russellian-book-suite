"""Template-shape tests for the scaffolded Rust addon.

These tests verify the .tmpl files have the right structure to produce a
Rust crate that actually verifies (calls Z3, asserts axioms, tracks atoms
for unsat-core extraction). They do not build Rust; they only string-search
the template content.
"""
from __future__ import annotations

from pathlib import Path



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
    """ir.rs.tmpl must parse the 'atoms' array via edn-rs, not return empty."""
    text = _read("ir.rs.tmpl")
    assert 'atoms' in text, "ir.rs.tmpl must reference the 'atoms' array"
    # The stub `Ok(Vec::new())` should be gone; edn_rs is used for parsing
    assert 'edn_rs' in text or '":atoms"' in text


def test_cargo_template_includes_edn_rs() -> None:
    text = _read("Cargo.toml.tmpl")
    assert "edn-rs" in text, "Cargo.toml.tmpl must declare edn-rs"


def test_cargo_template_declares_msrv_for_edition_2024() -> None:
    """cargo-edition-2024-toolchain: edition 2024 needs Rust 1.85+, so the
    template must declare `rust-version` to emit an actionable MSRV error
    on older toolchains instead of an opaque edition-support failure."""
    text = _read("Cargo.toml.tmpl")
    assert 'edition = "2024"' in text
    assert 'rust-version = "1.85"' in text, (
        "Cargo.toml.tmpl pins edition 2024 (Rust 1.85+) but declares no "
        "rust-version MSRV"
    )


def test_readme_template_documents_rust_toolchain() -> None:
    """cargo-edition-2024-toolchain: the scaffolded README must surface the
    Rust 1.85+ toolchain requirement so a builder on an older toolchain
    knows why the build fails."""
    readme = (TEMPLATE_ROOT / "README.md.tmpl").read_text(encoding="utf-8")
    assert "1.85" in readme, "README.md.tmpl must document the Rust 1.85+ MSRV"


def test_ir_template_uses_edn_rs_not_serde_json() -> None:
    text = _read("ir.rs.tmpl")
    # ir.rs PARSES atoms from the Python writer — must use edn-rs
    assert "edn_rs" in text or "edn-rs" in text, "ir.rs.tmpl must use edn-rs for parsing"
    # serde_json may still appear for the verdict serialization or types,
    # but the PARSE path must not be serde_json
    assert "serde_json::from_str" not in text, \
        "ir.rs.tmpl must not use serde_json::from_str on the atom parse path"


def test_smt_template_dispatches_on_edn() -> None:
    text = _read("smt.rs.tmpl")
    # smt.rs receives parsed atoms from ir.rs. After PR-1 these are
    # edn_rs::Edn values, not serde_json::Value.
    assert "edn_rs" in text or "Edn" in text, \
        "smt.rs.tmpl must dispatch on edn_rs::Edn values"


def test_ir_template_verdict_uses_edn_not_serde_json() -> None:
    text = _read("ir.rs.tmpl")
    # The return-trip verdict serialization must not use serde_json::to_string
    assert "serde_json::to_string" not in text, \
        "ir.rs.tmpl emit_verdict must use EDN emission, not serde_json::to_string"


# ----------------------------------------------------------------- BookLogic templates

BOOKLOGIC_TMPL = TEMPLATE_ROOT / "cljs-orchestrator" / "src" / "main" / "__project__" / "booklogic.cljs.tmpl"
BOOKLOGIC_TEST_TMPL = TEMPLATE_ROOT / "cljs-orchestrator" / "src" / "test" / "__project__" / "booklogic_test.cljs.tmpl"


def test_booklogic_template_exists() -> None:
    assert BOOKLOGIC_TMPL.exists()


def test_booklogic_test_template_exists() -> None:
    assert BOOKLOGIC_TEST_TMPL.exists()


def test_booklogic_template_has_main() -> None:
    text = BOOKLOGIC_TMPL.read_text(encoding="utf-8")
    assert "(defn -main" in text, "booklogic.cljs.tmpl must declare a -main CLI entry"


def test_booklogic_template_dispatches_three_forms() -> None:
    text = BOOKLOGIC_TMPL.read_text(encoding="utf-8")
    for sym in ("defsort", "defpredicate", "deflift"):
        assert sym in text, f"booklogic.cljs.tmpl must reference {sym!r}"


def test_booklogic_template_emits_predicates_edn() -> None:
    text = BOOKLOGIC_TMPL.read_text(encoding="utf-8")
    assert "emit-predicates-edn" in text
    assert "writeFileSync" in text, "booklogic.cljs.tmpl must write predicates.edn to disk"


def test_booklogic_template_dispatches_seven_forms() -> None:
    text = BOOKLOGIC_TMPL.read_text(encoding="utf-8")
    for sym in ("defsort", "defpredicate", "deflift",
                "defrule", "defconstraint", "defquery", "defremedy"):
        assert sym in text, f"booklogic.cljs.tmpl must reference {sym!r}"


def test_booklogic_template_emits_rules_edn() -> None:
    text = BOOKLOGIC_TMPL.read_text(encoding="utf-8")
    assert "emit-rewrite-rules-edn" in text
    assert "rules.edn" in text


def test_booklogic_template_loads_seven_files() -> None:
    text = BOOKLOGIC_TMPL.read_text(encoding="utf-8")
    for fname in ("sorts.edn", "predicates.edn", "lifts.edn",
                  "rules.edn", "constraints.edn", "queries.edn", "remedies.edn"):
        assert fname in text, f"load-booklogic must reference {fname!r}"


# ----------------------------------------------------------------- REQ-VERIFIER-BUILD-020

CARGO_TMPL = TEMPLATE_ROOT / "rust-verifier" / "Cargo.toml.tmpl"


def test_cozo_active_dep() -> None:
    """REQ-VERIFIER-BUILD-020: cozo = 0.7 is active by default via the kg feature."""
    text = CARGO_TMPL.read_text(encoding="utf-8")
    # cozo dep must be declared
    assert 'cozo' in text, "Cargo.toml.tmpl must declare cozo dep"
    assert '"0.7"' in text or "0.7" in text, "Cargo.toml.tmpl must pin cozo at 0.7"
    # kg feature must be in the default set so cozo is always activated
    # e.g. default = ["smt", "eqsat", "kg"]
    assert '"kg"' in text, 'Cargo.toml.tmpl kg feature must be declared'
    # The default feature list must include kg
    import re
    default_match = re.search(r'default\s*=\s*\[([^\]]+)\]', text)
    assert default_match is not None, "Cargo.toml.tmpl must have a [features] default list"
    assert 'kg' in default_match.group(1), \
        "kg must be in the default feature list (activates cozo by default)"
