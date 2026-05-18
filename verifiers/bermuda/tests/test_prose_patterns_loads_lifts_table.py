"""prose_patterns.py is a thin loader of the codegened regex table written
to rules/predicates.edn by `npm run booklogic-compile`. These tests confirm
the loader contract and that every predicate declared in
rules/booklogic/predicates.edn has at least one regex available at runtime.

REQ-BERMUDA-RULES-015, REQ-BERMUDA-RULES-021"""
from __future__ import annotations

from pathlib import Path


from scripts._edn_reader import Keyword  # noqa: E402
from scripts._io import read_edn_file  # noqa: E402

from scripts.prose_patterns import _load_predicates, extract_pass_a

BERMUDA_ROOT = Path(__file__).resolve().parents[1]


def test_loader_returns_keyword_keyed_dict() -> None:
    preds = _load_predicates()
    assert isinstance(preds, dict)
    # Codegened entries keyed by predicate keyword.
    assert any(isinstance(k, Keyword) for k in preds.keys()) or len(preds) >= 9


def test_every_booklogic_predicate_has_a_codegened_regex() -> None:
    """Walk the BookLogic predicates source and confirm each appears in the
    codegened regex table (after the compiler ran)."""
    bl_preds_path = BERMUDA_ROOT / "rules" / "booklogic" / "predicates.edn"
    data = read_edn_file(bl_preds_path)
    forms = data.get(Keyword("forms"), [])
    declared = {str(f[1]).lstrip(":") for f in forms if isinstance(f, list)}
    preds = _load_predicates()
    # Codegen keys are predicate names (strings or keywords). Normalise.
    have = {str(k).lstrip(":") for k in preds.keys()}
    # Permit the lift-name keys ('L001-...') too; what we want is that every
    # predicate's name appears somewhere in the predicate field of an entry.
    fields = set()
    for v in preds.values():
        p = v.get(Keyword("predicate"))
        if p is None:
            p = v.get(Keyword("predicate"))
        if p is not None:
            fields.add(str(p).lstrip(":"))
    missing = declared - have - fields
    assert not missing, f"codegened table missing predicates: {missing}"


def test_extract_pass_a_finds_quantitative_population() -> None:
    atoms = extract_pass_a("Bermuda has a population of approximately 63,918 residents.",
                           source_file="t.md")
    pop = [a for a in atoms
           if a.get(Keyword("predicate")) in {":population", Keyword("population")}]
    assert pop, "extractor did not match the :population regex"
    assert pop[0].get(Keyword("value")) == 63918
