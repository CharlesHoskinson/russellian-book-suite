# skills/neurosym-forge/scripts/lint_atomspace.py
"""Lint an atomspace EDN file for shape, sort coverage, and rule balance.

Exits 0 if clean, 1 if any error is found. Emits human-readable lines on stdout.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts._edn_reader import EdnList, EdnVector, Keyword
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
    if not isinstance(sorts_val, (list, EdnList, EdnVector)):
        report.errors.append("atomspace 'sorts' must be a list")
        return report
    sorts_val = list(sorts_val)
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


def _lint_booklogic_sorts(sorts_path: Path) -> list[str]:
    """Validate rules/booklogic/sorts.edn shape.

    Expects ``{:forms [(defsort :name) ...]}``.  Returns a list of error
    strings (empty means clean).
    """
    from scripts._edn_reader import EdnList, EdnVector, Symbol

    errors: list[str] = []
    try:
        payload = read_edn_file(sorts_path)
    except Exception as exc:
        return [f"sorts.edn: cannot parse: {exc}"]

    forms_val = _dict_get(payload, "forms")
    if forms_val is None:
        errors.append("sorts.edn: missing ':forms' key")
        return errors
    if not isinstance(forms_val, (list, EdnList, EdnVector)):
        errors.append("sorts.edn: ':forms' must be a vector/list")
        return errors

    for i, form in enumerate(forms_val):
        if not isinstance(form, (list, EdnList, EdnVector)):
            errors.append(f"sorts.edn: forms[{i}]: expected a list, got {type(form).__name__}")
            continue
        elems = list(form)
        if len(elems) != 2:
            errors.append(
                f"sorts.edn: forms[{i}]: defsort takes exactly 1 argument, got {len(elems) - 1}"
            )
            continue
        head = elems[0]
        if not (isinstance(head, Symbol) and head.name == "defsort"):
            errors.append(f"sorts.edn: forms[{i}]: expected 'defsort' head, got {head!r}")
        arg = elems[1]
        if not isinstance(arg, Keyword):
            errors.append(f"sorts.edn: forms[{i}]: sort name must be a keyword, got {arg!r}")

    return errors


def _lint_project(project_root: Path) -> int:
    """Lint a neurosym-forge project directory.

    Validates every booklogic EDN file that has been authored (non-empty
    :forms).  Returns 0 on success, 1 on any error.
    """
    errors: list[str] = []
    booklogic = project_root / "rules" / "booklogic"

    if not booklogic.is_dir():
        print(f"ERROR: {booklogic} is not a directory", file=sys.stderr)
        return 1

    sorts_path = booklogic / "sorts.edn"
    if sorts_path.exists():
        errs = _lint_booklogic_sorts(sorts_path)
        errors.extend(errs)
    else:
        errors.append(f"sorts.edn: file not found at {sorts_path}")

    seed_path = project_root / "rules" / "seed.edn"
    if seed_path.exists():
        try:
            payload = read_edn_file(seed_path)
            report = lint_atomspace(payload)
            errors.extend(report.errors)
        except Exception as exc:
            errors.append(f"seed.edn: {exc}")

    for err in errors:
        print(err)

    if errors:
        return 1

    sorts_path2 = booklogic / "sorts.edn"
    payload2 = read_edn_file(sorts_path2)
    forms_val = _dict_get(payload2, "forms") or []
    print(f"OK: project {project_root} passes ({len(list(forms_val))} sorts declared in sorts.edn)")
    return 0


def main(argv: list[str]) -> int:
    # Support --project <dir> for project-level linting.
    if len(argv) == 3 and argv[1] == "--project":
        return _lint_project(Path(argv[2]))

    if len(argv) != 2:
        print(
            "usage: python -m scripts.lint_atomspace <atomspace.edn>\n"
            "       python -m scripts.lint_atomspace --project <project-root>",
            file=sys.stderr,
        )
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
