"""BookLogic remedy adapter for book-qa.propose_writeback.

REQ-DSL-040: defremedy expander emits to rules/remedies.edn.
REQ-QA-PIPE-010: propose_writeback loads rules/remedies.edn and matches verdict shape.
REQ-QA-PIPE-012: :requires :human-review blocks apply_writeback auto-apply.

A `defremedy` form produced by the CLJS compiler lands in
`<project>/rules/remedies.edn`. This module reads that file, matches
each remedy's :when pattern against a verdict shape, and returns
proposal dicts that `propose_writeback` merges with its existing
tickets-driven transitions.

The pattern language is intentionally tiny in v0.4:

  (unsat-core ?claim)        — bind ?claim to each id in verdict["core"]
  (low-confidence ?claim)    — bind ?claim to each id in verdict["low_confidence"]

Each matched pattern emits a proposal of shape:

  {"remedy_id":  str,           # the remedy's :id
   "transition": {"kind": "claim",
                  "claim_id": <bound ?claim>,
                  "to":       <from :propose target>},
   "requires":   "human-review" | "auto-apply",
   "auto_apply": bool}

The Phase-4.4 propose_writeback extension routes these through the
existing pipeline.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

# Re-use neurosym-forge's EDN reader without a hard dep.
# Import the module directly from the on-disk path so we avoid conflicts
# with the local `scripts` package (book-qa/scripts/__init__.py).
def _load_edn_reader():
    import sys as _sys
    _reader_path = (
        Path(__file__).resolve().parents[3]
        / "skills" / "neurosym-forge" / "scripts" / "_edn_reader.py"
    )
    _mod_name = "_nf_edn_reader"
    if _mod_name in _sys.modules:
        return _sys.modules[_mod_name]
    spec = importlib.util.spec_from_file_location(_mod_name, _reader_path)
    mod  = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[_mod_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod

_edn_mod = _load_edn_reader()
Keyword   = _edn_mod.Keyword
read_edn  = _edn_mod.read_edn


class RemedyError(ValueError):
    """Raised when a remedy file is malformed."""


# Map a verdict-shape key to the EDN head symbol that selects it.
_PATTERN_HEAD_TO_VERDICT_FIELD = {
    "unsat-core":      "core",
    "low-confidence":  "low_confidence",
}


def load_remedies(path: Path) -> list[dict]:
    """Read a remedies.edn file; return a list of remedy dicts.

    Each dict has keys: id, when (parsed form), propose (parsed form),
    requires (string, no leading colon).

    Returns an empty list if the file does not exist.
    """
    if not path.exists():
        return []
    payload = read_edn(path.read_text(encoding="utf-8"))
    remedies = payload.get(Keyword("remedies"), [])
    out: list[dict] = []
    for entry in remedies:
        if not isinstance(entry, dict):
            raise RemedyError(f"remedy entry must be a map, got {type(entry).__name__}")
        for required in ("id", "when", "propose"):
            if Keyword(required) not in entry:
                raise RemedyError(f"remedy missing :{required}")
        out.append({
            "id":       entry[Keyword("id")],
            "when":     entry[Keyword("when")],
            "propose":  entry[Keyword("propose")],
            "requires": _strip_kw(entry.get(Keyword("requires"), Keyword("auto-apply"))),
        })
    return out


def _strip_kw(v: Any) -> str:
    if isinstance(v, Keyword):
        return v.name
    return str(v)


def match_remedies_against_verdict(remedies: list[dict],
                                   verdict: dict) -> list[dict]:
    """Walk each remedy; emit one proposal per pattern bound variable."""
    proposals: list[dict] = []
    for r in remedies:
        for binding in _bindings_for_pattern(r["when"], verdict):
            proposals.append(_build_proposal(r, binding))
    return proposals


def _bindings_for_pattern(pattern: Any, verdict: dict) -> list[dict[str, str]]:
    """Yield variable bindings for the pattern against the verdict.

    v0.4 patterns: (head ?var). Multi-clause patterns and arithmetic
    comparisons land in v0.5; not in scope here.
    """
    if not isinstance(pattern, list) or len(pattern) < 2:
        return []
    head = pattern[0]
    head_str = head.name if isinstance(head, Keyword) else str(head)
    field = _PATTERN_HEAD_TO_VERDICT_FIELD.get(head_str)
    if field is None:
        return []
    var = pattern[1]
    var_name = str(var).lstrip("?")
    candidates = verdict.get(field, [])
    if not isinstance(candidates, list):
        return []
    return [{var_name: c} for c in candidates if isinstance(c, str)]


def _build_proposal(remedy: dict, binding: dict[str, str]) -> dict:
    propose = remedy["propose"]
    # Expect shape (ledger/transition ?claim :refuted)
    if not (isinstance(propose, list) and len(propose) >= 3):
        raise RemedyError(f"remedy {remedy['id']!r}: malformed :propose form")
    head = propose[0]
    head_str = head.name if isinstance(head, Keyword) else str(head)
    if head_str not in ("ledger/transition", "transition"):
        raise RemedyError(f"remedy {remedy['id']!r}: unknown :propose head {head_str!r}")
    var       = str(propose[1]).lstrip("?")
    target    = _strip_kw(propose[2])
    claim_id  = binding.get(var)
    if claim_id is None:
        raise RemedyError(f"remedy {remedy['id']!r}: var {var!r} not bound")
    requires   = remedy["requires"]
    auto_apply = requires == "auto-apply"
    return {
        "remedy_id":  remedy["id"],
        "transition": {
            "kind":     "claim",
            "claim_id": claim_id,
            "to":       target,
        },
        "requires":   requires,
        "auto_apply": auto_apply,
    }
