"""REQ-INDUCE-040..045: BookLogic grammar enforcer + LLM proposer.

Five orthogonal tests cover the five failure categories named in the
design doc plus the stub-determinism property:

  1. A valid `defconstraint` form passes the grammar (REQ-INDUCE-040)
  2. A form with an invalid head fails              (REQ-INDUCE-042)
  3. A form citing an unknown predicate fails       (REQ-INDUCE-042)
  4. A form with an illegal operator fails          (REQ-INDUCE-042)
  5. A non-EDN string fails                         (REQ-INDUCE-042)
  6. The Stub provider produces a deterministic     (REQ-INDUCE-043)
     candidate identical across runs

The `nbb`-shelled tests SKIP cleanly if nbb is not on PATH so a
developer without the Node toolchain still gets a green pytest run;
CI on Linux always has it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[1]
GRAMMAR_CLJS = SKILL_ROOT / "scripts" / "_induction_grammar.cljs"
NBB = shutil.which("nbb")

# Ensure `from scripts._induction_proposer import ...` works when running
# pytest from the repo root rather than from the skill root.
sys.path.insert(0, str(SKILL_ROOT))


nbb_required = pytest.mark.skipif(
    NBB is None,
    reason="nbb not on PATH; grammar-conforming-json tests need nbb",
)


def _check(form_edn: str, schema_edn: str) -> dict:
    """Shell into nbb, evaluate the grammar checker, parse JSON result."""
    assert NBB is not None  # guarded by nbb_required
    # We invoke nbb with --classpath pointing at the scripts dir so the
    # `_induction-grammar` namespace is loadable. The expression escapes
    # the EDN strings as Clojure string literals via `pr-str`-friendly
    # quoting at the Python level — both strings are passed through
    # `json.dumps` to get a safe Clojure-readable quoted form.
    form_quoted = json.dumps(form_edn)
    schema_quoted = json.dumps(schema_edn)
    expr = (
        "(require '[_induction-grammar :as g]) "
        f"(println (g/grammar-conforming-json {form_quoted} {schema_quoted}))"
    )
    result = subprocess.run(
        [NBB, "--classpath", str(GRAMMAR_CLJS.parent), "-e", expr],
        capture_output=True, text=True, check=False, timeout=30,
    )
    if result.returncode != 0:
        pytest.fail(
            f"nbb invocation failed (rc={result.returncode})\n"
            f"stdout: {result.stdout!r}\n"
            f"stderr: {result.stderr!r}"
        )
    # The grammar-conforming-json fn prints a single JSON line.
    line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    return json.loads(line)


# ---------------------------------------------------------------------------
# Static checks on the cljs source itself (REQ-INDUCE-040)
# ---------------------------------------------------------------------------


def test_induction_grammar_module_exists():
    """REQ-INDUCE-040: the enforcer ships at the documented path."""
    assert GRAMMAR_CLJS.exists(), (
        f"_induction_grammar.cljs missing at {GRAMMAR_CLJS}; "
        f"REQ-INDUCE-040 requires the enforcer to live here"
    )


def test_bnf_block_is_top_level_const():
    """REQ-INDUCE-040: the BNF / supported-operators set lives as a
    top-level `^:const` declaration so the drift lint can parse it
    statically without spinning up nbb."""
    src = GRAMMAR_CLJS.read_text(encoding="utf-8")
    assert "SUPPORTED-OPERATORS" in src, (
        "_induction_grammar.cljs missing SUPPORTED-OPERATORS top-level "
        "declaration"
    )
    assert "^:const" in src and "SUPPORTED-OPERATORS" in src, (
        "SUPPORTED-OPERATORS must be marked ^:const so the drift lint "
        "can rely on its top-level position"
    )


# ---------------------------------------------------------------------------
# Behavioural checks via nbb shell (REQ-INDUCE-040, 042)
# ---------------------------------------------------------------------------


SCHEMA_BASIC = (
    '{:predicates {:foo {:arg-sorts [:s] :return :int}} :sorts [:s]}'
)


@nbb_required
def test_valid_defconstraint_passes():
    form = (
        "(defconstraint :C1 :backend :z3 "
        ":assert (= (:foo :s) 1) "
        ':on-unsat {:defect :D :severity :advisory :message "x"})'
    )
    result = _check(form, SCHEMA_BASIC)
    assert result["ok"] is True, result


@nbb_required
def test_unknown_predicate_fails():
    form = (
        "(defconstraint :C2 :backend :z3 "
        ":assert (= (:bogus :s) 1) "
        ':on-unsat {:defect :D :severity :advisory :message "x"})'
    )
    result = _check(form, SCHEMA_BASIC)
    assert result["ok"] is False
    # Either the predicate-name or the failure tag appears in the reason.
    assert "bogus" in result["reason"] or "unknown" in result["reason"].lower()
    assert result.get("tag") == "grammar-fail/unknown-predicate"


@nbb_required
def test_wrong_head_fails():
    form = "(defpredicate :foo [:s] :int)"
    result = _check(form, SCHEMA_BASIC)
    assert result["ok"] is False
    assert "defconstraint" in result["reason"].lower()
    assert result.get("tag") == "grammar-fail/wrong-head"


@nbb_required
def test_illegal_operator_fails():
    """REQ-INDUCE-042: `mod` is outside the supported-operator set."""
    form = (
        "(defconstraint :C3 :backend :z3 "
        ":assert (mod (:foo :s) 7) "
        ':on-unsat {:defect :D :severity :advisory :message "x"})'
    )
    result = _check(form, SCHEMA_BASIC)
    assert result["ok"] is False
    assert result.get("tag") == "grammar-fail/illegal-op"
    assert "mod" in result["reason"]


@nbb_required
def test_non_edn_fails():
    form = "Sure, here is your constraint: blah blah"
    result = _check(form, SCHEMA_BASIC)
    assert result["ok"] is False
    assert result.get("tag") == "grammar-fail/non-edn"


@nbb_required
def test_missing_assert_fails():
    """A defconstraint without :assert is malformed and must be rejected."""
    form = (
        "(defconstraint :C4 :backend :z3 "
        ':on-unsat {:defect :D :severity :advisory :message "x"})'
    )
    result = _check(form, SCHEMA_BASIC)
    assert result["ok"] is False
    assert ":assert" in result["reason"]


# ---------------------------------------------------------------------------
# LLM proposer (REQ-INDUCE-041, 043, 044)
# ---------------------------------------------------------------------------


def test_stub_proposer_returns_deterministic_candidate(monkeypatch):
    """REQ-INDUCE-043: the Stub provider produces a deterministic
    candidate. Running it twice with the same env yields byte-identical
    output."""
    monkeypatch.setenv("NEUROSYM_LLM_PROVIDER", "stub")
    canned = (
        "(defconstraint :C1 :backend :z3 :assert (= (:foo :s) 1) "
        ':on-unsat {:defect :D :severity :advisory :message "x"})'
    )
    monkeypatch.setenv("NEUROSYM_STUB_CANDIDATE", canned)

    from scripts._induction_proposer import propose_constraint

    schema = {
        "predicates": {":foo": {":arg-sorts": [":s"], ":return": ":int"}},
        "sorts": [":s"],
    }
    cluster = [{"id": "c-1", "predicate": ":foo", "subject": ":s", "value": 1}]

    out1 = propose_constraint(schema=schema, atom_cluster=cluster)
    out2 = propose_constraint(schema=schema, atom_cluster=cluster)
    assert out1 == out2, "stub proposer is not deterministic across runs"
    assert out1.strip().startswith("(defconstraint"), out1
    assert ":foo" in out1


def test_proposer_prompt_embeds_schema_and_bnf(monkeypatch):
    """REQ-INDUCE-041: the proposer prompt SHALL embed (a) predicates +
    sorts and (b) the BookLogic operator BNF.

    We test this by inspecting the prompt the proposer would send,
    exposed via `build_proposer_prompt` (a pure function — no LLM
    needed)."""
    from scripts._induction_proposer import build_proposer_prompt

    schema = {
        "predicates": {":foo": {":arg-sorts": [":s"], ":return": ":int"}},
        "sorts": [":s"],
    }
    cluster = [{"id": "c-1", "predicate": ":foo", "subject": ":s", "value": 1}]
    prompt = build_proposer_prompt(schema=schema, atom_cluster=cluster)

    # Predicates section
    assert ":foo" in prompt, "prompt must list the schema's predicates"
    # BNF section: at least the canonical ops must appear
    for op in ("=", "<", "<=", "approx=", "and", "or", "not", "forall"):
        assert op in prompt, f"prompt is missing BNF op {op!r}"
    # Atom cluster section
    assert "c-1" in prompt, "prompt must list the cited atom cluster"


def test_proposer_unknown_provider_raises(monkeypatch):
    """REQ-INDUCE-043: NEUROSYM_LLM_PROVIDER must be one of stub | openai
    | anthropic | local. An unknown value raises a clear error."""
    monkeypatch.setenv("NEUROSYM_LLM_PROVIDER", "this-is-not-a-real-provider")
    from scripts._induction_proposer import propose_constraint
    from scripts._llm_lift import LLMLiftError

    schema = {"predicates": {}, "sorts": []}
    with pytest.raises(LLMLiftError):
        propose_constraint(schema=schema, atom_cluster=[])


def test_dry_run_prints_candidate_to_stdout(monkeypatch, capsys):
    """REQ-INDUCE-044: when NEUROSYM_INDUCTION_DRY_RUN=1 is set, the
    proposer prints the candidate to stdout (in ordered EDN form) so a
    developer can iterate on the prompt template without paying solver
    cost."""
    monkeypatch.setenv("NEUROSYM_LLM_PROVIDER", "stub")
    monkeypatch.setenv("NEUROSYM_INDUCTION_DRY_RUN", "1")
    canned = (
        "(defconstraint :C9 :backend :z3 :assert (= (:foo :s) 1) "
        ':on-unsat {:defect :D :severity :advisory :message "x"})'
    )
    monkeypatch.setenv("NEUROSYM_STUB_CANDIDATE", canned)

    from scripts._induction_proposer import propose_constraint

    schema = {
        "predicates": {":foo": {":arg-sorts": [":s"], ":return": ":int"}},
        "sorts": [":s"],
    }
    cluster = [{"id": "c-1", "predicate": ":foo", "subject": ":s", "value": 1}]
    candidate = propose_constraint(schema=schema, atom_cluster=cluster)

    captured = capsys.readouterr()
    assert ":C9" in captured.out, (
        "NEUROSYM_INDUCTION_DRY_RUN=1 should echo the candidate to stdout"
    )
    assert candidate.strip().startswith("(defconstraint")
