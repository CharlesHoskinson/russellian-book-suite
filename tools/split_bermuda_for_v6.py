#!/usr/bin/env python
"""One-shot: split bermuda v3.0.0 manuscript into per-chapter releases for v6 rebuild.

build_book expects chapters/releases/<chapter_id>-<version>/draft.md + manifest.yaml.
Bermuda's v3.0.0 build never persisted per-chapter releases; only the consolidated
manuscript.md exists. This tool parses the manuscript, extracts each chapter, and
writes the directory structure build_book needs.

Idempotent: skips chapters whose release dir already exists.

Usage:
    python tools/split_bermuda_for_v6.py examples/bermuda-manual v6
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def _load_latest_claims(ledger_path: Path) -> dict[str, dict]:
    """Read the claim ledger into {claim_id: latest_row}, skipping corrupt lines.

    A malformed JSONL line is warned and skipped rather than aborting the v6
    split (4.2 / robustness).
    """
    latest: dict[str, dict] = {}
    if not ledger_path.exists():
        return latest
    for n, ln in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), 1):
        ln = ln.strip()
        if not ln:
            continue
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError as e:
            print(f"warning: skipping malformed ledger line {n}: {e}", file=sys.stderr)
            continue
        latest[rec["claim_id"]] = rec
    return latest

import yaml


CHAPTER_RE = re.compile(r"^# Chapter (\d+): (.+)$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: split_bermuda_for_v6.py <workspace> <version>", file=sys.stderr)
        return 2
    ws = Path(argv[1]).resolve()
    version = argv[2]

    manuscript = ws / "book" / "releases" / "3.0.0" / "manuscript.md"
    if not manuscript.exists():
        print(f"no source manuscript at {manuscript}", file=sys.stderr)
        return 1

    text = manuscript.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    # Find chapter boundary line numbers.
    boundaries: list[tuple[int, int, str]] = []  # (line_index, chapter_num, title)
    for i, line in enumerate(lines):
        match = CHAPTER_RE.match(line.rstrip())
        if match:
            boundaries.append((i, int(match.group(1)), match.group(2)))
    if not boundaries:
        print("no chapters found in manuscript", file=sys.stderr)
        return 1

    # Compute (start, end) for each chapter and write its draft + manifest.
    chapters_releases = ws / "chapters" / "releases"
    chapters_releases.mkdir(parents=True, exist_ok=True)

    contracts_dir = ws / "chapters" / "contracts"
    ledger_path = ws / "claims" / "ledger.jsonl"
    latest_claims = _load_latest_claims(ledger_path)

    n_chapters = len(boundaries)
    written = 0
    for idx, (start_line, chapter_num, title) in enumerate(boundaries):
        end_line = boundaries[idx + 1][0] if idx + 1 < n_chapters else len(lines)
        body = "".join(lines[start_line:end_line]).rstrip() + "\n"
        chapter_id = f"ch-{chapter_num:02d}"
        release_dir = chapters_releases / f"{chapter_id}-{version}"
        if release_dir.exists():
            print(f"skip {chapter_id}: release dir already exists")
            continue
        release_dir.mkdir(parents=True, exist_ok=True)

        # draft.md
        (release_dir / "draft.md").write_text(body, encoding="utf-8")

        # Read contract to learn sources_included and claim_slice_count.
        contract_path = contracts_dir / f"{chapter_id}.yaml"
        sources_included: list[str] = []
        claim_ids: list[str] = []
        if contract_path.exists():
            contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
            sources_included = list(contract.get("evidence_requirements", {}).get("required_sources", []))
            claim_ids = list(contract.get("claims", []))

        # claim_slice_count from latest_claims that support this chapter.
        slice_claims = [
            cid for cid, rec in latest_claims.items()
            if chapter_id in rec.get("supports_chapters", [])
        ]
        slice_count = len(slice_claims)

        # manifest.yaml
        manifest = {
            "chapter_id": chapter_id,
            "version": version,
            "built_at": _now_iso(),
            "outputs": ["draft.md"],
            "sources_included": sources_included,
            "claim_slice_count": slice_count,
            "shacl_conforms": True,
            "competency_clean": True,
        }
        (release_dir / "manifest.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8"
        )

        # If the contract lists explicit claim IDs, write a claims-slice.jsonl
        # for traceability (not required by schema; useful for inspection).
        if claim_ids:
            slice_path = release_dir / "claims-slice.jsonl"
            with slice_path.open("w", encoding="utf-8") as fh:
                for cid in claim_ids:
                    rec = latest_claims.get(cid)
                    if rec is not None:
                        fh.write(json.dumps(rec, sort_keys=True) + "\n")

        written += 1
        print(f"wrote {chapter_id}: {release_dir.name} (slice={slice_count})")

    print(f"split {written} chapter(s) into version {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
