# skills/neurosym-forge/scripts/lint_atomspace.py
"""Lint an atomspace EDN file for shape, sort coverage, and rule balance.

Exits 0 if clean, 1 if any error is found. Emits human-readable lines on stdout.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file
from scripts.atom import Atom
from scripts.rewrite_rule import RewriteRule
from scripts.sort_registry import SortRegistry, _dict_get

SORTS_KEY = Keyword("sorts")
ATOMS_KEY = Keyword("atoms")
RULES_KEY = Keyword("rules")
KIND_KEY = Keyword("kind")
SORT_KEY = Keyword("sort")
HEAD_KEY = Keyword("head")
ARGS_KEY = Keyword("args")
NAME_KEY = Keyword("name")
LHS_KEY = Keyword("lhs")
RHS_KEY = Keyword("rhs")
ID_KEY = Keyword("id")
TAGS_KEY = Keyword("tags")
CHECKSUMS_KEY = Keyword("checksums")


@dataclass
class LintReport:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _sort_str(s: Any) -> str:
    """Return a string representation of a sort value for error messages."""
    if isinstance(s, Keyword):
        return str(s)
    return str(s)


def _collect_sort_strings(s: Any) -> set[Any]:
    """Collect all primitive sort identifiers (str or Keyword) from a sort value."""
    out: set[Any] = set()
    if isinstance(s, Keyword):
        out.add(s)
    elif isinstance(s, str):
        out.add(s)
    elif isinstance(s, dict):
        kind_raw = _dict_get(s, "kind")
        kind_str = str(kind_raw) if kind_raw is not None else None
        if kind_str in (":fn", "fn"):
            for a in (_dict_get(s, "args") or []):
                out |= _collect_sort_strings(a)
            ret = _dict_get(s, "ret")
            if ret is not None:
                out |= _collect_sort_strings(ret)
        elif kind_str in (":enum", "enum"):
            pass  # enum members are not sort references
    return out


def walk_atom_sorts(payload: dict[str, Any], collect: set[Any]) -> None:
    sort_val = _dict_get(payload, "sort")
    if sort_val is not None:
        collect |= _collect_sort_strings(sort_val)
    head_val = _dict_get(payload, "head")
    if head_val is not None and isinstance(head_val, dict):
        walk_atom_sorts(head_val, collect)
    for a in (_dict_get(payload, "args") or []):
        if isinstance(a, dict):
            walk_atom_sorts(a, collect)


_SENTINEL = object()


def _dict_get_or_sentinel(d: dict, name: str) -> Any:
    """Like _dict_get but returns _SENTINEL if key is absent (not None value)."""
    if name in d:
        return d[name]
    for k, v in d.items():
        if _is_keyword_named(k, name):
            return v
    return _SENTINEL


def _is_keyword_named(k: Any, name: str) -> bool:
    return hasattr(k, "name") and not isinstance(k, type) and k.name == name


def lint_atomspace(payload: dict[str, Any]) -> LintReport:
    report = LintReport()

    sorts_raw = _dict_get_or_sentinel(payload, "sorts")
    if sorts_raw is _SENTINEL:
        report.errors.append("atomspace missing 'sorts' field")
        return report
    sorts_val = sorts_raw
    if not isinstance(sorts_val, list):
        report.errors.append("atomspace 'sorts' must be a list")
        return report
    try:
        registry = SortRegistry.from_dict({SORTS_KEY: sorts_val})
    except ValueError as e:
        report.errors.append(f"sort registry: {e}")
        return report
    # known_primitives: set of string representations like ":int"
    known_primitives: set[str] = set()
    for s in registry._sorts:
        if isinstance(s.value, str):
            known_primitives.add(s.value)

    def _is_unknown(sort_ref: Any) -> bool:
        """Return True if sort_ref is a primitive sort not in known_primitives."""
        if isinstance(sort_ref, Keyword):
            return str(sort_ref) not in known_primitives
        if isinstance(sort_ref, str) and sort_ref.startswith(":"):
            return sort_ref not in known_primitives
        return False

    atoms_val = _dict_get(payload, "atoms") or []
    for i, raw in enumerate(atoms_val):
        if not isinstance(raw, dict):
            report.errors.append(f"atoms[{i}]: not an object")
            continue
        if _dict_get(raw, "sort") is None:
            name_raw = _dict_get(raw, "name")
            name_str = str(name_raw) if name_raw is not None else "?"
            report.errors.append(f"atoms[{i}] ({name_str}): missing 'sort'")
            continue
        try:
            Atom.from_dict(raw)
        except ValueError as e:
            report.errors.append(f"atoms[{i}]: {e}")
            continue
        referenced: set[Any] = set()
        walk_atom_sorts(raw, referenced)
        for s in referenced:
            if _is_unknown(s):
                name_raw = _dict_get(raw, "name")
                name_str = str(name_raw) if name_raw is not None else "?"
                report.errors.append(
                    f"atoms[{i}] ({name_str}): unknown sort {_sort_str(s)!r}"
                )

    rules_val = _dict_get(payload, "rules") or []
    for i, raw in enumerate(rules_val):
        try:
            rule = RewriteRule.from_dict(raw)
        except ValueError as e:
            report.errors.append(f"rules[{i}]: {e}")
            continue
        try:
            rule.check_variable_balance()
        except ValueError as e:
            report.errors.append(f"rules[{i}] {rule.id}: {e}")
        referenced: set[Any] = set()
        lhs_raw = _dict_get(raw, "lhs")
        rhs_raw = _dict_get(raw, "rhs")
        if lhs_raw:
            walk_atom_sorts(lhs_raw, referenced)
        if rhs_raw:
            walk_atom_sorts(rhs_raw, referenced)
        for s in referenced:
            if _is_unknown(s):
                report.errors.append(f"rules[{i}] {rule.id}: unknown sort {_sort_str(s)!r}")

    return report


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m scripts.lint_atomspace <atomspace.edn>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    payload = read_edn_file(path)
    report = lint_atomspace(payload)
    for err in report.errors:
        print(err)
    if not report.ok:
        return 1
    atoms_val = _dict_get(payload, "atoms") or []
    rules_val = _dict_get(payload, "rules") or []
    print(f"OK: atomspace {path} passes ({len(atoms_val)} atoms, "
          f"{len(rules_val)} rules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
