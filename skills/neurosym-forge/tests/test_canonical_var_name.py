"""REQ-EDN-042: Python canonical_var_name matches the golden vectors."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._canonical import canonical_var_name
from scripts._edn_reader import Keyword, read_edn

GOLDEN = ROOT / "tests" / "golden" / "canonical_var_name.edn"


def _extract(row: dict, key: str):
    """Read a value from a golden row, accepting Keyword or str keys."""
    for k in (Keyword(key), key, f":{key}"):
        if k in row:
            return row[k]
    raise KeyError(key)


def test_python_matches_golden():
    rows = read_edn(GOLDEN.read_text(encoding="utf-8"))
    for row in rows:
        pred = _extract(row, "predicate")
        subj = _extract(row, "subject")
        want = _extract(row, "want")
        pred_in = pred.name if isinstance(pred, Keyword) else pred
        subj_in = subj.name if isinstance(subj, Keyword) else subj
        got = canonical_var_name(pred_in, subj_in)
        assert got == want, (
            f"({pred_in!r}, {subj_in!r}) -> {got!r} (expected {want!r})"
        )
