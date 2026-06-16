"""Vendored copies must stay byte-identical to their canonical source.

`scaffold_project.py` copies `_edn_reader.py` from neurosym-forge into each
verifier's `scripts/` dir. The three verifier copies (bermuda, epidemiology,
osmotic_pressure) silently drifted — they were missing the bare-`/` Symbol fix
the canonical had, so they mis-parsed a `/` Symbol (audit 2026-06-16, H-08).
This guard fails closed if any vendored copy diverges, so the next drift is
caught at PR time instead of by an audit.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL = REPO_ROOT / "skills" / "neurosym-forge" / "scripts" / "_edn_reader.py"
VERIFIERS = ("adsc-clinical", "bermuda", "epidemiology", "osmotic_pressure")
VENDORED = [REPO_ROOT / "verifiers" / v / "scripts" / "_edn_reader.py" for v in VERIFIERS]


def test_canonical_edn_reader_exists():
    assert CANONICAL.is_file(), f"canonical _edn_reader not found at {CANONICAL}"


def test_vendored_edn_readers_match_canonical():
    canonical = CANONICAL.read_bytes()
    drifted = [
        str(p.relative_to(REPO_ROOT))
        for p in VENDORED
        if not p.is_file() or p.read_bytes() != canonical
    ]
    assert not drifted, (
        f"vendored _edn_reader.py copies have drifted from "
        f"{CANONICAL.relative_to(REPO_ROOT)}: {drifted}. Re-sync by copying the "
        "canonical over them (scaffold_project.py is the source of the vendoring)."
    )
