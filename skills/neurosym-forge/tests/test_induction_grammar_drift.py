"""REQ-INDUCE-046: drift lint — the grammar enforcer's
SUPPORTED-OPERATORS set tracks codegen_axioms.py's
_SUPPORTED_ASSERT_HEADS set.

If a future change adds `(mod a b)` to codegen without updating the
grammar enforcer, the inducer will silently reject candidates the
codegen would happily accept. This lint catches the drift at
`make lint` time.

The three sources of truth that MUST stay in sync:

  1. `skills/neurosym-forge/scripts/codegen_axioms.py`
       — `_SUPPORTED_ASSERT_HEADS` frozenset
  2. `skills/neurosym-forge/scripts/_induction_grammar.cljs`
       — `SUPPORTED-OPERATORS` ^:const set
  3. `skills/neurosym-forge/scripts/_induction_proposer.py`
       — `_OPERATOR_BNF_DISPLAY` list (also mirrored into the prompt)

This is the same drift-lint pattern as `test_support_matrix.py` for
the backend matrix (Tier 5 precedent).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

import re
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
CODEGEN_PY = SKILL_ROOT / "scripts" / "codegen_axioms.py"
GRAMMAR_CLJS = SKILL_ROOT / "scripts" / "_induction_grammar.cljs"
PROPOSER_PY = SKILL_ROOT / "scripts" / "_induction_proposer.py"


# ---------------------------------------------------------------------------
# Parsers — deliberately tight regexes so adding a new source of truth is
# loud rather than silently slipping past.
# ---------------------------------------------------------------------------


def _parse_codegen_supported_heads() -> set[str]:
    """Extract `_SUPPORTED_ASSERT_HEADS = frozenset({ ... })` literal."""
    src = CODEGEN_PY.read_text(encoding="utf-8")
    m = re.search(
        r"_SUPPORTED_ASSERT_HEADS\s*=\s*frozenset\(\s*\{([^}]*)\}\s*\)",
        src,
        re.DOTALL,
    )
    assert m, (
        "could not find _SUPPORTED_ASSERT_HEADS frozenset literal in "
        f"{CODEGEN_PY}; the drift lint depends on this exact shape"
    )
    body = m.group(1)
    items = re.findall(r'"([^"]+)"', body)
    return set(items)


def _parse_grammar_supported_operators() -> set[str]:
    """Extract `SUPPORTED-OPERATORS` ^:const set from the cljs file.

    The cljs file declares it as:

        (def ^:const SUPPORTED-OPERATORS
          "docstring"
          #{'= '~= 'approx= ...})

    The set elements are Clojure quoted symbols (`'name`). We strip the
    quote prefix and return the bare symbol names."""
    src = GRAMMAR_CLJS.read_text(encoding="utf-8")
    m = re.search(
        r"\^:const\s+SUPPORTED-OPERATORS\b.*?#\{([^}]*)\}",
        src,
        re.DOTALL,
    )
    assert m, (
        "could not find SUPPORTED-OPERATORS ^:const set literal in "
        f"{GRAMMAR_CLJS}; the drift lint depends on this exact shape"
    )
    body = m.group(1)
    # Match each quoted symbol — Clojure symbols can include - / = < > etc.
    # We strip a leading `'` and accept any printable non-whitespace chars.
    raw_tokens = re.findall(r"'(\S+)", body)
    # Drop trailing punctuation that may have stuck (e.g. comment-only
    # case) — none expected, but be defensive.
    return {tok.rstrip(",") for tok in raw_tokens}


def _parse_proposer_operator_bnf() -> set[str]:
    """Extract `_OPERATOR_BNF_DISPLAY = [...]` list literal."""
    src = PROPOSER_PY.read_text(encoding="utf-8")
    m = re.search(
        r"_OPERATOR_BNF_DISPLAY\s*=\s*\[([^\]]*)\]",
        src,
        re.DOTALL,
    )
    assert m, (
        "could not find _OPERATOR_BNF_DISPLAY list literal in "
        f"{PROPOSER_PY}; the drift lint depends on this exact shape"
    )
    body = m.group(1)
    items = re.findall(r'"([^"]+)"', body)
    return set(items)


# ---------------------------------------------------------------------------
# Static health checks (sanity)
# ---------------------------------------------------------------------------


def test_codegen_supported_heads_is_parseable():
    heads = _parse_codegen_supported_heads()
    assert heads, "_SUPPORTED_ASSERT_HEADS parsed empty — regex broken"
    # Sanity: a couple of canonical ops must be present.
    assert "=" in heads
    assert "and" in heads


def test_grammar_supported_operators_is_parseable():
    ops = _parse_grammar_supported_operators()
    assert ops, "SUPPORTED-OPERATORS parsed empty — regex broken"
    assert "=" in ops
    assert "and" in ops


def test_proposer_operator_bnf_is_parseable():
    ops = _parse_proposer_operator_bnf()
    assert ops, "_OPERATOR_BNF_DISPLAY parsed empty — regex broken"
    assert "=" in ops
    assert "and" in ops


# ---------------------------------------------------------------------------
# The drift checks themselves (REQ-INDUCE-046)
# ---------------------------------------------------------------------------


def test_grammar_tracks_codegen_supported_heads():
    """REQ-INDUCE-046: SUPPORTED-OPERATORS in _induction_grammar.cljs
    SHALL equal _SUPPORTED_ASSERT_HEADS in codegen_axioms.py.

    If codegen adds `(mod a b)` without a matching entry in the
    grammar enforcer, the inducer will silently reject candidates
    that the codegen would accept. This lint fails before that
    drift reaches production.
    """
    codegen = _parse_codegen_supported_heads()
    grammar = _parse_grammar_supported_operators()
    only_in_codegen = codegen - grammar
    only_in_grammar = grammar - codegen
    assert codegen == grammar, (
        "DRIFT: codegen_axioms.py's _SUPPORTED_ASSERT_HEADS and "
        "_induction_grammar.cljs's SUPPORTED-OPERATORS disagree.\n"
        f"  only in codegen: {sorted(only_in_codegen)}\n"
        f"  only in grammar: {sorted(only_in_grammar)}\n"
        "REQ-INDUCE-046: both sets MUST be equal. Update the lagging "
        "file (typically the grammar enforcer when codegen gains a "
        "new operator)."
    )


def test_proposer_bnf_tracks_grammar_supported_operators():
    """REQ-INDUCE-041, 046: the BNF embedded in the LLM prompt
    SHALL match the grammar enforcer's accepted set. If the prompt
    advertises an op the enforcer will reject, every candidate using
    that op wastes an LLM call before the gate rejects it."""
    grammar = _parse_grammar_supported_operators()
    proposer = _parse_proposer_operator_bnf()
    only_in_grammar = grammar - proposer
    only_in_proposer = proposer - grammar
    assert grammar == proposer, (
        "DRIFT: _induction_grammar.cljs's SUPPORTED-OPERATORS and "
        "_induction_proposer.py's _OPERATOR_BNF_DISPLAY disagree.\n"
        f"  only in grammar:  {sorted(only_in_grammar)}\n"
        f"  only in proposer: {sorted(only_in_proposer)}\n"
        "REQ-INDUCE-046: the prompt's BNF and the enforcer's set MUST "
        "agree — otherwise the LLM is told it may use ops the gate "
        "will reject."
    )


def test_lint_fails_when_codegen_adds_op_without_bnf_entry(tmp_path, monkeypatch):
    """REQ-INDUCE-046: simulate adding a new op to codegen without
    updating the grammar enforcer, and confirm the drift lint surfaces
    the missing operator with a clear message.

    We patch the parser-helpers to read from tmp-path copies of the
    source files so we don't have to touch the real codegen_axioms.py
    in the test.
    """
    fake_codegen = tmp_path / "codegen_axioms_fake.py"
    fake_codegen.write_text(
        '_SUPPORTED_ASSERT_HEADS = frozenset({\n'
        '    "=", "<", "<=", "and", "or", "not",\n'
        '    "mod",  # newly added, but not yet in grammar enforcer\n'
        "})\n",
        encoding="utf-8",
    )
    fake_grammar = tmp_path / "_induction_grammar_fake.cljs"
    fake_grammar.write_text(
        "(def ^:const SUPPORTED-OPERATORS\n"
        '  "docstring"\n'
        "  #{'= '< '<= 'and 'or 'not})\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "tests.test_induction_grammar_drift.CODEGEN_PY", fake_codegen
    )
    monkeypatch.setattr(
        "tests.test_induction_grammar_drift.GRAMMAR_CLJS", fake_grammar
    )

    codegen = _parse_codegen_supported_heads()
    grammar = _parse_grammar_supported_operators()
    assert "mod" in codegen
    assert "mod" not in grammar
    # The real lint assertion would now fail; we record that the
    # diff carries the offending op so the failure message is
    # actionable.
    drift = codegen - grammar
    assert drift == {"mod"}, (
        f"expected the simulated drift to surface 'mod' as the "
        f"only diff; got {sorted(drift)}"
    )
