# skills/neurosym-forge/scripts/lint_rewrite_coverage.py
"""Verify every rewrite rule has a fixture test and on-disk checksums match."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, file_checksum
from scripts.sort_registry import _dict_get

RULES_KEY = Keyword("rules")
CHECKSUMS_KEY = Keyword("checksums")
ID_KEY = Keyword("id")


@dataclass
class CoverageReport:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def lint_rewrite_coverage(project_root: Path) -> CoverageReport:
    report = CoverageReport()
    rules_dir = project_root / "rules"
    tests_dir = project_root / "tests" / "rules"

    if not rules_dir.exists():
        report.errors.append(f"missing rules/ at {rules_dir}")
        return report

    checksums_path = rules_dir / ".checksums.edn"
    expected_checksums: dict[str, str] = {}
    if checksums_path.exists():
        parsed = read_edn_file(checksums_path)
        raw = _dict_get(parsed, "checksums") or {}
        # Normalise keys: string or Keyword → string
        for k, v in raw.items():
            k.name if hasattr(k, "name") else str(k)
            # But checksums keys are file names like "seed.edn" — plain strings
            expected_checksums[str(k)] = v

    for path in sorted(rules_dir.glob("*.edn")):
        if path.name.startswith("."):
            continue
        actual = file_checksum(path)
        expected = expected_checksums.get(path.name)
        if expected is None:
            report.errors.append(f"no checksum recorded for {path.name}; "
                                 f"use add_rewrite_rule to update")
        elif actual != expected:
            report.errors.append(
                f"checksum mismatch on {path.name}: manual edit detected. "
                f"Reapply via add_rewrite_rule or restore the file."
            )
        try:
            payload = read_edn_file(path)
        except Exception:
            report.errors.append(f"{path.name}: cannot parse as EDN")
            continue
        if not isinstance(payload, dict):
            report.errors.append(f"{path.name}: expected a map at top level")
            continue
        rules_val = _dict_get(payload, "rules") or []
        for rule in rules_val:
            rid_raw = _dict_get(rule, "id")
            rid = str(rid_raw) if rid_raw is not None else None
            if not rid:
                report.errors.append(f"{path.name}: rule missing id")
                continue
            fixture = tests_dir / f"test_{rid}.cljs"
            if not fixture.exists():
                report.errors.append(
                    f"rule {rid} ({path.name}): missing fixture test {fixture.relative_to(project_root)}"
                )

    return report


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m scripts.lint_rewrite_coverage <project-root>",
              file=sys.stderr)
        return 2
    root = Path(argv[1])
    report = lint_rewrite_coverage(root)
    for err in report.errors:
        print(err)
    if not report.ok:
        return 1
    print(f"OK: rule coverage at {root} is clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
