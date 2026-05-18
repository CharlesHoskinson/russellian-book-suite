"""End-to-end checks that the Bermuda BookLogic source files parse cleanly
through the BookLogic compiler. Each test reads one file via the EDN reader
and asserts the expected form heads are present.

REQ-BERMUDA-RULES-010..021"""
from __future__ import annotations

import json
from pathlib import Path


# scripts/__init__.py extends this package's __path__ to include forge's
# scripts/ dir, so the imports below resolve to neurosym-forge's modules.
from scripts._edn_reader import Keyword  # noqa: E402
from scripts._io import read_edn_file  # noqa: E402


RULES_DIR = Path(__file__).resolve().parents[1] / "rules" / "booklogic"


def _read_forms(name: str) -> list:
    """Load a BookLogic source file and return its :forms vector."""
    data = read_edn_file(RULES_DIR / name)
    return data.get(Keyword("forms"), [])


def _heads(forms: list) -> list[str]:
    """Return the head symbol of each form as a string ('defsort', etc.)."""
    out = []
    for f in forms:
        if isinstance(f, list) and f:
            out.append(str(f[0]))
    return out


# ---------- sorts.edn ----------

def test_sorts_edn_parses() -> None:
    forms = _read_forms("sorts.edn")
    assert len(forms) >= 9  # 9 sort families minimum


def test_sorts_edn_has_required_sorts() -> None:
    forms = _read_forms("sorts.edn")
    # Each defsort form is (defsort :name); we look at the keyword arg.
    declared = {f[1] for f in forms if isinstance(f, list) and len(f) >= 2}
    # All Bermuda predicate value kinds + the universal entity sort
    expected = {
        Keyword("int"), Keyword("real"), Keyword("bool"),
        Keyword("string"), Keyword("entity"),
        Keyword("formula"), Keyword("verdict"),
        Keyword("claim"), Keyword("source"),
    }
    missing = expected - declared
    assert not missing, f"missing sorts: {missing}"


# ---------- predicates.edn ----------

def test_predicates_edn_parses() -> None:
    forms = _read_forms("predicates.edn")
    assert len(forms) >= 9  # 5 existing + 4 new quantitative


def test_predicates_edn_has_five_existing() -> None:
    forms = _read_forms("predicates.edn")
    names = {f[1] for f in forms if isinstance(f, list) and len(f) >= 2}
    expected = {
        Keyword("parishes-count"),
        Keyword("named-islands-and-rocks"),
        Keyword("currency-pegged-at-parity"),
        Keyword("airport-on-island"),
        Keyword("binomial"),
    }
    missing = expected - names
    assert not missing, f"missing existing predicates: {missing}"


def test_predicates_edn_has_four_new_quantitative() -> None:
    forms = _read_forms("predicates.edn")
    names = {f[1] for f in forms if isinstance(f, list) and len(f) >= 2}
    expected = {
        Keyword("population"),
        Keyword("land-area-km2"),
        Keyword("gdp-usd-billion"),
        Keyword("hospital-beds-kemh"),
    }
    missing = expected - names
    assert not missing, f"missing new predicates: {missing}"


def test_predicates_edn_arity_shape() -> None:
    """Each (defpredicate :name [arg-sorts...] return-sort) has exactly 4 elements."""
    forms = _read_forms("predicates.edn")
    bad = [f for f in forms if not (isinstance(f, list) and len(f) == 4)]
    assert not bad, f"malformed predicate forms: {bad}"


# ---------- lifts.edn ----------

def test_lifts_edn_parses() -> None:
    forms = _read_forms("lifts.edn")
    assert len(forms) >= 9  # at least one lift per predicate


def test_lifts_edn_each_form_has_required_options() -> None:
    """Each (deflift name :from V :when V :emit V ...) must declare :from, :when, :emit."""
    forms = _read_forms("lifts.edn")
    for f in forms:
        assert isinstance(f, list) and len(f) >= 5
        # form: (deflift NAME :from V :when V :emit V ...)
        # parse options after the name
        options = f[2:]
        keys = options[0::2]
        assert Keyword("from") in keys, f"lift {f[1]} missing :from"
        assert Keyword("when") in keys, f"lift {f[1]} missing :when"
        assert Keyword("emit") in keys, f"lift {f[1]} missing :emit"


def test_lifts_edn_covers_every_predicate() -> None:
    """Each predicate declared in predicates.edn must have at least one lift
    in lifts.edn whose :emit (fact ...) targets it."""
    preds = {f[1] for f in _read_forms("predicates.edn") if isinstance(f, list)}
    lift_targets = set()
    for f in _read_forms("lifts.edn"):
        if not isinstance(f, list):
            continue
        options = f[2:]
        opts = dict(zip(options[0::2], options[1::2]))
        emit = opts.get(Keyword("emit"))
        # (fact ?claim-id :Subject :pred-name body...) → :pred-name at index 3
        if isinstance(emit, list) and len(emit) >= 4 and str(emit[0]) == "fact":
            lift_targets.add(emit[3])
    missing = preds - lift_targets
    assert not missing, f"predicates without lifts: {missing}"


# ---------- rules.edn ----------

def test_rules_edn_parses() -> None:
    forms = _read_forms("rules.edn")
    assert len(forms) >= 2


def test_rules_edn_form_heads_are_defrule() -> None:
    forms = _read_forms("rules.edn")
    bad = [str(f[0]) for f in forms if isinstance(f, list) and str(f[0]) != "defrule"]
    assert not bad, f"non-defrule forms in rules.edn: {bad}"


# ---------- constraints.edn ----------

def test_constraints_edn_parses() -> None:
    forms = _read_forms("constraints.edn")
    assert len(forms) >= 9  # 5 existing + 4 quantitative


def test_constraints_edn_each_form_has_backend_and_assert() -> None:
    forms = _read_forms("constraints.edn")
    for f in forms:
        assert isinstance(f, list) and len(f) >= 4
        options = f[2:]
        keys = set(options[0::2])
        assert Keyword("backend") in keys, f"constraint {f[1]} missing :backend"
        assert Keyword("assert") in keys, f"constraint {f[1]} missing :assert"


def test_constraints_edn_covers_canonical_facts() -> None:
    """Every canonical fact previously asserted in canonical.rs must be
    represented by at least one constraint in constraints.edn."""
    names = {str(f[1]) for f in _read_forms("constraints.edn") if isinstance(f, list)}
    expected_canonical = {
        "C001-bermuda-parishes",
        "C002-named-islands-and-rocks",
        "C003-bmd-usd-parity",
        "C004-airport-st-davids",
        "C005-cedar-binomial",
    }
    missing = expected_canonical - names
    assert not missing, f"missing canonical constraints: {missing}"


def test_constraints_edn_includes_quantitative() -> None:
    names = {str(f[1]) for f in _read_forms("constraints.edn") if isinstance(f, list)}
    expected_quant = {
        "C006-population",
        "C007-land-area-km2",
        "C008-gdp-usd-billion",
        "C009-hospital-beds-kemh",
    }
    missing = expected_quant - names
    assert not missing, f"missing quantitative constraints: {missing}"


# ---------- queries.edn ----------

def test_queries_edn_parses() -> None:
    forms = _read_forms("queries.edn")
    assert len(forms) >= 1


def test_queries_edn_each_form_has_backend_find_where() -> None:
    for f in _read_forms("queries.edn"):
        assert isinstance(f, list)
        options = f[2:]
        keys = set(options[0::2])
        assert Keyword("backend") in keys
        assert Keyword("find") in keys
        assert Keyword("where") in keys


# ---------- remedies.edn ----------

def test_remedies_edn_parses() -> None:
    forms = _read_forms("remedies.edn")
    assert len(forms) >= 1


def test_remedies_edn_each_form_has_when_propose() -> None:
    for f in _read_forms("remedies.edn"):
        assert isinstance(f, list)
        options = f[2:]
        keys = set(options[0::2])
        assert Keyword("when") in keys
        assert Keyword("propose") in keys


# ---------- package.json + namespace ----------

def test_package_json_declares_booklogic_compile() -> None:
    pkg = json.loads((RULES_DIR.parents[1] / "package.json").read_text(encoding="utf-8"))
    assert "nbb" in pkg.get("devDependencies", {}), \
        "package.json must declare nbb as a devDependency"
    assert "booklogic-compile" in pkg.get("scripts", {}), \
        "package.json must declare booklogic-compile script"


def test_booklogic_namespace_file_exists() -> None:
    p = (RULES_DIR.parents[1] / "cljs-orchestrator" / "src" / "main"
         / "bermuda" / "booklogic.cljs")
    assert p.exists(), f"BookLogic compiler missing at {p}"
    text = p.read_text(encoding="utf-8")
    assert "ns bermuda.booklogic" in text, "namespace declaration must read bermuda.booklogic"
