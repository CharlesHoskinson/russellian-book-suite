"""Append a new sort to the project's seed.edn and refresh checksums."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, write_edn_file, file_checksum
from scripts.sort_registry import Sort, SortRegistry

SORTS_KEY = Keyword("sorts")
CHECKSUMS_KEY = Keyword("checksums")


def add_sort(project_root: Path, sort_value: Any) -> None:
    seed = project_root / "rules" / "seed.edn"
    payload = read_edn_file(seed)
    registry = SortRegistry.from_dict({SORTS_KEY: payload.get(SORTS_KEY, [])})
    new_sort = Sort.from_value(sort_value)
    if registry.contains(new_sort):
        raise ValueError(f"sort already present: {new_sort}")
    registry.add(new_sort)
    payload[SORTS_KEY] = registry.to_edn_sorts()
    write_edn_file(seed, payload)

    checksums_path = project_root / "rules" / ".checksums.edn"
    checksums = read_edn_file(checksums_path)[CHECKSUMS_KEY] if checksums_path.exists() else {}
    checksums["seed.edn"] = file_checksum(seed)
    write_edn_file(checksums_path, {CHECKSUMS_KEY: checksums})


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="Project root")
    ap.add_argument("--sort",    required=True,
                    help="Sort literal (':foo') or JSON object for fn/enum")
    args = ap.parse_args(argv)
    project = Path(args.project)
    try:
        value = json.loads(args.sort) if args.sort.startswith("{") else args.sort
    except json.JSONDecodeError as e:
        print(f"could not parse --sort: {e}", file=sys.stderr)
        return 2
    add_sort(project, value)
    print(f"added sort {args.sort} to {project}/rules/seed.edn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
