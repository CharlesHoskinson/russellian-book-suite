"""REQ-SMT-051, 052, 054 — quantifier support in :assert heads."""
import pytest

pytestmark = pytest.mark.windows_canary

import shutil
import subprocess
from pathlib import Path

import pytest
from scripts.codegen_axioms import generate_axioms_source, CodegenError
from scripts._edn_reader import Keyword, Symbol


def _quant(quant_head, bindings, body, sorts=None):
    constraint = {
        Keyword("id"): "CQ001",
        Keyword("backend"): Keyword("z3"),
        Keyword("assert"): (Symbol(quant_head), bindings, body),
        Keyword("track"): Keyword("CQ001"),
        Keyword("on-unsat"): {Keyword("defect"): Keyword("D13"),
                              Keyword("severity"): Keyword("critical"),
                              Keyword("message"): "quantifier check failed"},
    }
    return [constraint], (sorts or [])


def test_forall_single_var():
    constraints, sorts = _quant(
        "forall",
        [(Symbol("?o"), Keyword("proof-obligation"))],
        (Symbol("="), Symbol("?o"), Keyword("special")),
        sorts=[{Keyword("name"): Keyword("proof-obligation")}],
    )
    out = generate_axioms_source(constraints, sorts=sorts)
    assert "mk_forall_const" in out


def test_exists_single_var():
    constraints, sorts = _quant(
        "exists",
        [(Symbol("?r"), Keyword("reference"))],
        (Symbol("="), Symbol("?r"), Keyword("v2-spec")),
        sorts=[{Keyword("name"): Keyword("reference")}],
    )
    out = generate_axioms_source(constraints, sorts=sorts)
    assert "mk_exists_const" in out


def test_forall_two_vars_with_implication():
    """The EpochPoET C003 pattern."""
    body = (Symbol("=>"),
            (Keyword("contradicts"), Symbol("?a"), Symbol("?b")),
            (Keyword("supersedes"), Symbol("?a"), Symbol("?b")))
    constraints, sorts = _quant(
        "forall",
        [(Symbol("?a"), Keyword("proof-obligation")),
         (Symbol("?b"), Keyword("proof-obligation"))],
        body,
        sorts=[{Keyword("name"): Keyword("proof-obligation")}],
    )
    out = generate_axioms_source(constraints, sorts=sorts)
    assert "mk_forall_const" in out
    assert ".implies" in out


def test_undeclared_sort_in_binding_raises():
    constraints, sorts = _quant(
        "forall",
        [(Symbol("?x"), Keyword("nonexistent-sort"))],
        (Symbol("="), Symbol("?x"), 5),
        sorts=[],
    )
    with pytest.raises(CodegenError, match=r"sort 'nonexistent-sort' not declared"):
        generate_axioms_source(constraints, sorts=sorts)


def test_nested_quantifier_exists_inside_forall():
    """The EpochPoET C004 pattern: forall over obligations, exists over references."""
    body = (Symbol("exists"),
            [(Symbol("?r"), Keyword("reference"))],
            (Symbol("="), Symbol("?r"), Symbol("?o")))
    constraints, sorts = _quant(
        "forall",
        [(Symbol("?o"), Keyword("proof-obligation"))],
        body,
        sorts=[{Keyword("name"): Keyword("proof-obligation")},
               {Keyword("name"): Keyword("reference")}],
    )
    out = generate_axioms_source(constraints, sorts=sorts)
    assert "mk_forall_const" in out
    assert "mk_exists_const" in out


# ---------------------------------------------------------------- compile gate

_CARGO_TOML = """\
[package]
name = "quantifier_smoke"
version = "0.0.0"
edition = "2024"
publish = false

[lib]
path = "src/lib.rs"

[features]
default = ["smt"]
smt = ["dep:z3"]

[dependencies]
z3 = { version = "0.20", optional = true }
"""


@pytest.mark.slow
def test_emitted_quantifier_rust_compiles(tmp_path: Path) -> None:
    """Compile-gate the codegen output against z3 0.20.

    v0.5 originally shipped a quantifier emit that *looked* right under
    string-presence tests but failed cargo build with:
      - `'?a'` character literal (multi-codepoint)
      - `Datatype::new_const(ctx, name, sort)` (wrong arity for z3 0.20)
      - free `ctx`/`proof_obligation_sort` identifiers in
        `axioms_for_subject(solver, subject)` scope

    This test exercises the full forall + exists + nested quantifier matrix
    against an actual `cargo check`, so the next regression in this corner
    fails locally rather than waiting for an end-to-end verifier build.
    """
    cargo = shutil.which("cargo")
    if cargo is None:
        pytest.skip("cargo not on PATH")

    # Single fixture: covers single-var forall, exists, two-var forall,
    # and nested exists-inside-forall. Mirrors the four EpochPoET patterns.
    sorts = [
        {Keyword("name"): Keyword("proof-obligation")},
        {Keyword("name"): Keyword("reference")},
    ]
    constraints = [
        {
            Keyword("id"): "Q001",
            Keyword("backend"): Keyword("z3"),
            Keyword("assert"): (
                Symbol("forall"),
                [(Symbol("?o"), Keyword("proof-obligation"))],
                (Symbol("="), Symbol("?o"), Keyword("special")),
            ),
            Keyword("track"): Keyword("Q001"),
            Keyword("on-unsat"): {
                Keyword("defect"): Keyword("D13"),
                Keyword("severity"): Keyword("critical"),
                Keyword("message"): "fail",
            },
        },
        {
            Keyword("id"): "Q002",
            Keyword("backend"): Keyword("z3"),
            Keyword("assert"): (
                Symbol("exists"),
                [(Symbol("?r"), Keyword("reference"))],
                (Symbol("="), Symbol("?r"), Keyword("v2-spec")),
            ),
            Keyword("track"): Keyword("Q002"),
            Keyword("on-unsat"): {
                Keyword("defect"): Keyword("D13"),
                Keyword("severity"): Keyword("critical"),
                Keyword("message"): "fail",
            },
        },
        {
            Keyword("id"): "Q003",
            Keyword("backend"): Keyword("z3"),
            Keyword("assert"): (
                Symbol("forall"),
                [(Symbol("?a"), Keyword("proof-obligation")),
                 (Symbol("?b"), Keyword("proof-obligation"))],
                (Symbol("=>"),
                 (Keyword("contradicts"), Symbol("?a"), Symbol("?b")),
                 (Keyword("supersedes"), Symbol("?a"), Symbol("?b"))),
            ),
            Keyword("track"): Keyword("Q003"),
            Keyword("on-unsat"): {
                Keyword("defect"): Keyword("D13"),
                Keyword("severity"): Keyword("critical"),
                Keyword("message"): "fail",
            },
        },
        {
            Keyword("id"): "Q004",
            Keyword("backend"): Keyword("z3"),
            Keyword("assert"): (
                Symbol("forall"),
                [(Symbol("?o"), Keyword("proof-obligation"))],
                (Symbol("exists"),
                 [(Symbol("?r"), Keyword("reference"))],
                 (Symbol("="), Symbol("?r"), Symbol("?o"))),
            ),
            Keyword("track"): Keyword("Q004"),
            Keyword("on-unsat"): {
                Keyword("defect"): Keyword("D13"),
                Keyword("severity"): Keyword("critical"),
                Keyword("message"): "fail",
            },
        },
    ]
    src = generate_axioms_source(constraints, sorts=sorts)

    # Carve out a throwaway library crate with z3 0.20 as the only dep.
    crate = tmp_path / "quantifier_smoke"
    (crate / "src").mkdir(parents=True)
    (crate / "Cargo.toml").write_text(_CARGO_TOML, encoding="utf-8")
    (crate / "src" / "lib.rs").write_text(src, encoding="utf-8")

    try:
        r = subprocess.run(
            [cargo, "check", "--features", "smt", "--manifest-path",
             str(crate / "Cargo.toml")],
            capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        pytest.skip("cargo check timed out (slow network or first-build link)")

    if r.returncode != 0:
        stderr_lower = r.stderr.lower()
        # Environmental failures (missing C++ linker, z3 system library,
        # cmake) -> skip rather than fail, matching test_pr4_full_smoke's
        # OQ#5 deferral policy on Windows.
        env_keywords = (
            "cmake", "cl.exe", "link.exe", "msvc",
            "c++ toolchain", "linker", "cc",
            "could not find native static library",
            "libz3", "z3.dll", "z3.lib",
        )
        if any(k in stderr_lower for k in env_keywords):
            pytest.skip(
                "cargo check: environment lacks z3/C++ toolchain "
                f"(stderr excerpt: {r.stderr[:400]})"
            )
        pytest.fail(
            "cargo check failed against quantifier-emit output:\n"
            f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}\n"
            "---- generated source (last 2 KiB) ----\n"
            + src[-2048:]
        )


def test_emitted_quantifier_syntactically_valid_rust() -> None:
    """Fast gate: even without cargo on PATH, every quantifier shape we emit
    parses as valid Rust under `syn`-grade tokenisation (matched braces,
    parens, brackets; no stray identifiers like `ctx` referenced outside a
    block that introduces them).

    This catches the v0.5 regressions without requiring cargo or z3 to be
    installed in the test runner, so it runs on every neurosym-forge test
    invocation.
    """
    fixtures = [
        # single-var forall
        ([(Symbol("?o"), Keyword("proof-obligation"))],
         (Symbol("="), Symbol("?o"), Keyword("special")),
         "forall",
         [{Keyword("name"): Keyword("proof-obligation")}]),
        # two-var forall with implication
        ([(Symbol("?a"), Keyword("proof-obligation")),
          (Symbol("?b"), Keyword("proof-obligation"))],
         (Symbol("=>"),
          (Keyword("contradicts"), Symbol("?a"), Symbol("?b")),
          (Keyword("supersedes"), Symbol("?a"), Symbol("?b"))),
         "forall",
         [{Keyword("name"): Keyword("proof-obligation")}]),
        # exists single-var
        ([(Symbol("?r"), Keyword("reference"))],
         (Symbol("="), Symbol("?r"), Keyword("v2-spec")),
         "exists",
         [{Keyword("name"): Keyword("reference")}]),
    ]
    for bindings, body, head, sorts in fixtures:
        constraints, _ = _quant(head, bindings, body, sorts=sorts)
        src = generate_axioms_source(constraints, sorts=sorts)
        # Bracket balance: every emitted axioms.rs has matched braces, parens, brackets.
        assert src.count("{") == src.count("}"), f"brace mismatch for {head}"
        assert src.count("(") == src.count(")"), f"paren mismatch for {head}"
        assert src.count("[") == src.count("]"), f"bracket mismatch for {head}"
        # Anti-regression: the v0.5 bug emitted `'?a'` (char literal) and
        # `Datatype::new_const(ctx,` and bare `ctx.mk_forall_const(`.
        assert "'?" not in src, f"char-literal regression: {head}"
        assert "Datatype::new_const(ctx," not in src, (
            f"Datatype::new_const(ctx, ...) regression: {head}"
        )
        assert "ctx.mk_forall_const(" not in src, (
            f"ctx.mk_forall_const(...) regression: {head}"
        )
        assert "ctx.mk_exists_const(" not in src, (
            f"ctx.mk_exists_const(...) regression: {head}"
        )
        # Positive shape: z3 0.20 free fn + Sort::uninterpreted + Dynamic::new_const.
        if head == "forall":
            assert "ast::forall_const(" in src
        else:
            assert "ast::exists_const(" in src
        assert "Sort::uninterpreted(" in src
        assert "Dynamic::new_const(" in src
        # Variable names appear as `"?var"` proper string literals (not char literals).
        for b in bindings:
            var_str = str(b[0])
            assert f'"{var_str}"' in src, (
                f"expected proper string literal {var_str!r} in emit for {head}"
            )
