"""Capture a byte-stable golden of the current Datalog D9/D10/D11 behaviour.

This freezes the pyDatalog consistency pass (``datalog_consistency.run``) result
for a workspace into a deterministic JSON golden, so the later pyDatalog -> EDN
-> Cozo port (Phase P3) can be proven equivalent (REQ-KG-014). It changes no
production behaviour -- it only calls ``run`` and serializes its canonical
payload.

The payload is ``DefectReport.as_payload()``: ``{"summary": {...}, "defects":
[...]}`` already sorted canonically by ``(class, rule, json.dumps(facts))``, so
the golden is byte-stable across runs and tmp_paths.

Determinism / LF discipline (same as book-knowledge's golden writers)
---------------------------------------------------------------------
The golden is written with ``json.dumps(payload, indent=2, sort_keys=True) +
"\\n"``, ``encoding="utf-8"``, ``newline="\\n"`` so LF is pinned on every
platform (the equivalence oracle must not drift on Windows CRLF translation).

Usage
-----
    python -m scripts.capture_consistency <workspace-dir> <out-path>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from datalog_consistency import run  # noqa: E402


def capture_consistency(workspace: Path) -> dict:
    """Return the canonical defect payload for ``workspace``.

    Delegates to ``datalog_consistency.run`` and returns
    ``report.as_payload()`` -- the same canonically-sorted dict the production
    pass writes to ``qa/datalog-defects.json``.
    """
    report = run(Path(workspace))
    return report.as_payload()


def write_consistency_golden(workspace: Path, out_path: Path) -> dict:
    """Capture the consistency payload for ``workspace`` and write it to
    ``out_path`` byte-stably. Returns the captured payload for reporting."""
    payload = capture_consistency(workspace)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: python -m scripts.capture_consistency <workspace-dir> <out-path>",
            file=sys.stderr,
        )
        return 2
    payload = write_consistency_golden(Path(argv[1]), Path(argv[2]))
    s = payload["summary"]
    print(
        f"captured consistency golden: contradictions={s['contradictions']} "
        f"orphans={s['orphans']} invariant_violations={s['invariant_violations']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
