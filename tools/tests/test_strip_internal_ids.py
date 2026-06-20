"""4.4: BARE_CLM_RE must not over-match past an unparenthesised clm id."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

from strip_internal_ids import strip_ids  # noqa: E402


def test_bare_clm_does_not_overmatch_rest_of_sentence():
    out = strip_ids("The board clm-2026-000148 was verified.")
    assert out == "The board was verified."


def test_parenthesised_clm_is_stripped():
    out = strip_ids("The board (clm-2026-000148; status: verified) acted.")
    assert "clm-" not in out
    assert "The board" in out and "acted." in out
