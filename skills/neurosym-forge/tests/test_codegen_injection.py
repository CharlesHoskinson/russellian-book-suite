"""REQ-NSI-002 / H-02 — codegen string-literal injection hardening.

Names and values that reach the codegen come from claim text, so a subject,
value, or predicate containing `"`, `\\`, or a newline must not break out of the
emitted Rust string literal. Constraint ids supplied at the `forge` CLI are
validated against a strict allowlist before they reach the template.
"""
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.codegen_axioms import generate_axioms_source
from scripts._edn_reader import Keyword, Symbol


def _eq_constraint(value):
    return [{
        Keyword("id"): "C1",
        Keyword("backend"): Keyword("z3"),
        Keyword("assert"): (Symbol("="), (Keyword("status"), Keyword("s")), value),
        Keyword("track"): Keyword("C1"),
        Keyword("on-unsat"): {Keyword("defect"): Keyword("D1"),
                              Keyword("severity"): Keyword("advisory"),
                              Keyword("message"): "x"},
    }]


def test_string_value_with_backslash_and_newline_is_escaped():
    """A value carrying a backslash and a newline must be emitted as a valid,
    single-line Rust string literal (no raw newline, backslash doubled)."""
    out = generate_axioms_source(_eq_constraint("a\\b\nc"))
    line = next(l for l in out.splitlines() if "from_str(" in l)
    assert "\n" not in line.replace("\\n", "")   # no RAW newline survived
    assert "\\\\" in line                          # backslash doubled
    assert "\\n" in line                           # newline escaped


def test_string_value_with_quote_is_escaped():
    out = generate_axioms_source(_eq_constraint('ev"il'))
    line = next(l for l in out.splitlines() if "from_str(" in l)
    # exactly the opening and closing quotes plus the escaped inner quote.
    assert '\\"' in line
