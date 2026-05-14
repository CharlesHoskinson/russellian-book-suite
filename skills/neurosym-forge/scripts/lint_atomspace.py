# skills/neurosym-forge/scripts/lint_atomspace.py
"""Lint an atomspace EDN file for shape, sort coverage, and rule balance.

Exits 0 if clean, 1 if any error is found. Emits human-readable lines on stdout.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts._io import read_edn_as_json
from scripts.atom import Atom
from scripts.rewrite_rule import RewriteRule
from scripts.sort_registry import Sort, SortRegistry


@dataclass
class LintReport:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _collect_sort_strings(s: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(s, str):
        out.add(s)
    elif isinstance(s, dict):
        if s.get("kind") == "fn":
            for a in s.get("args", []):
                out |= _collect_sort_strings(a)
            out |= _collect_sort_strings(s.get("ret"))
        elif s.get("kind") == "enum":
            out.add("enum:" + ",".join(s.get("members", [])))
    return out


def walk_atom_sorts(payload: dict[str, Any], collect: set[str]) -> None:
    if "sort" in payload:
        collect |= _collect_sort_strings(payload["sort"])
    if "head" in payload and isinstance(payload["head"], dict):
        walk_atom_sorts(payload["head"], collect)
    for a in payload.get("args", []) or []:
        if isinstance(a, dict):
            walk_atom_sorts(a, collect)


def lint_atomspace(payload: dict[str, Any]) -> LintReport:
    report = LintReport()

    if "sorts" not in payload:
        report.errors.append("atomspace missing 'sorts' field")
        return report
    if not isinstance(payload["sorts"], list):
        report.errors.append("atomspace 'sorts' must be a list")
        return report
    try:
        registry = SortRegistry.from_dict({"sorts": payload["sorts"]})
    except ValueError as e:
        report.errors.append(f"sort registry: {e}")
        return report
    known_primitives = {s.value for s in registry._sorts if isinstance(s.value, str)}

    for i, raw in enumerate(payload.get("atoms", [])):
        if not isinstance(raw, dict):
            report.errors.append(f"atoms[{i}]: not an object")
            continue
        if "sort" not in raw:
            report.errors.append(f"atoms[{i}] ({raw.get('name', '?')}): missing 'sort'")
            continue
        try:
            Atom.from_dict(raw)
        except ValueError as e:
            report.errors.append(f"atoms[{i}]: {e}")
            continue
        referenced: set[str] = set()
        walk_atom_sorts(raw, referenced)
        for s in referenced:
            if s.startswith(":") and s not in known_primitives:
                report.errors.append(
                    f"atoms[{i}] ({raw.get('name', '?')}): unknown sort {s!r}"
                )

    for i, raw in enumerate(payload.get("rules", [])):
        try:
            rule = RewriteRule.from_dict(raw)
        except ValueError as e:
            report.errors.append(f"rules[{i}]: {e}")
            continue
        try:
            rule.check_variable_balance()
        except ValueError as e:
            report.errors.append(f"rules[{i}] {rule.id}: {e}")
        referenced: set[str] = set()
        walk_atom_sorts(raw["lhs"], referenced)
        walk_atom_sorts(raw["rhs"], referenced)
        for s in referenced:
            if s.startswith(":") and s not in known_primitives:
                report.errors.append(f"rules[{i}] {rule.id}: unknown sort {s!r}")

    return report


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m scripts.lint_atomspace <atomspace.edn>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    payload = read_edn_as_json(path)
    report = lint_atomspace(payload)
    for err in report.errors:
        print(err)
    if not report.ok:
        return 1
    print(f"OK: atomspace {path} passes ({len(payload.get('atoms', []))} atoms, "
          f"{len(payload.get('rules', []))} rules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
