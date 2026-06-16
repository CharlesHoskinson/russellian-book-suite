"""4.4: a footnote reference with no definition is warned, not silently placeheld."""
import logging
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import process_footnotes as pf  # noqa: E402


def test_missing_footnote_def_warns(caplog):
    body = "Prose with a ref[^a].\n\n## Notes\n\n[^b]: a defined note.\n"
    with caplog.at_level(logging.WARNING):
        out = pf._process_chapter(body, 1)
    assert any("[^a]" in rec.getMessage() for rec in caplog.records)
    # Placeholder still emitted so the build does not break.
    assert "missing" in out
