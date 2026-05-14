"""Append a (=) rewrite rule to seed.edn and emit a fixture test."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, write_edn_file, file_checksum
from scripts.lint_atomspace import walk_atom_sorts
from scripts.rewrite_rule import RewriteRule
from scripts.sort_registry import SortRegistry

SORTS_KEY = Keyword("sorts")
RULES_KEY = Keyword("rules")
CHECKSUMS_KEY = Keyword("checksums")
ID_KEY = Keyword("id")
LHS_KEY = Keyword("lhs")
RHS_KEY = Keyword("rhs")
DOC_KEY = Keyword("doc")
TAGS_KEY = Keyword("tags")


def _validate_against_registry(rule_payload: dict[str, Any], registry: SortRegistry) -> None:
    primitives = {s.value for s in registry._sorts if isinstance(s.value, str)}
    referenced: set[Any] = set()
    walk_atom_sorts(rule_payload[LHS_KEY], referenced)
    walk_atom_sorts(rule_payload[RHS_KEY], referenced)
    # Each referenced sort may be a string ":foo" or a Keyword; normalise to string for comparison
    unknown = set()
    for s in referenced:
        s_str = str(s) if hasattr(s, "name") else s
        if isinstance(s_str, str) and s_str.startswith(":") and s_str not in primitives:
            unknown.add(s_str)
    if unknown:
        raise ValueError(f"unknown sort(s): {sorted(unknown)}")


def add_rewrite_rule(project_root: Path, rule_payload: dict[str, Any]) -> None:
    seed = project_root / "rules" / "seed.edn"
    try:
        payload = read_edn_file(seed)
    except Exception as exc:
        raise ValueError(f"cannot parse seed at {seed}: {exc}") from exc
    registry = SortRegistry.from_dict({SORTS_KEY: payload.get(SORTS_KEY, [])})
    _validate_against_registry(rule_payload, registry)

    rule = RewriteRule.from_dict(rule_payload)
    rule.check_variable_balance()

    rules = payload.get(RULES_KEY, [])
    if any(r.get(ID_KEY) == rule.id for r in rules):
        raise ValueError(f"duplicate rule id: {rule.id}")
    rules.append(rule.to_dict())
    payload[RULES_KEY] = rules
    write_edn_file(seed, payload)

    fixture_dir = project_root / "tests" / "rules"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixture_dir / f"test_{rule.id}.cljs"
    fixture.write_text(_fixture_text(rule), encoding="utf-8", newline="\n")

    checksums_path = project_root / "rules" / ".checksums.edn"
    checksums = read_edn_file(checksums_path)[CHECKSUMS_KEY] if checksums_path.exists() else {}
    checksums["seed.edn"] = file_checksum(seed)
    write_edn_file(checksums_path, {CHECKSUMS_KEY: checksums})


def _fixture_text(rule: RewriteRule) -> str:
    return (
        f"(ns rules.test-{rule.id.lower()}\n"
        f"  (:require [cljs.test :refer-macros [deftest is]]\n"
        f"            [meander.epsilon :as m]))\n\n"
        f"(deftest {rule.id}-applies\n"
        f"  ;; rule: {rule.doc or rule.id}\n"
        f"  (is (some? :TODO-supply-input-form-for-{rule.id})))\n"
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--rule-file", required=True,
                    help="JSON/EDN file containing a single rule payload")
    args = ap.parse_args(argv)
    project = Path(args.project)
    rule_payload = json.loads(Path(args.rule_file).read_text(encoding="utf-8"))
    add_rewrite_rule(project, rule_payload)
    print(f"appended rule {rule_payload.get('id')} to {project}/rules/seed.edn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
