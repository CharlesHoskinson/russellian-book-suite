"""4.2: _load_latest_claims skips a corrupt ledger line instead of crashing."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import split_bermuda_for_v6 as tool  # noqa: E402


def test_load_latest_claims_skips_corrupt_line(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"claim_id": "clm-1", "v": 1}) + "\n"
        + "{ corrupt line\n"
        + json.dumps({"claim_id": "clm-2", "v": 2}) + "\n",
        encoding="utf-8",
    )
    latest = tool._load_latest_claims(ledger)
    assert set(latest) == {"clm-1", "clm-2"}


def test_load_latest_claims_missing_file_is_empty(tmp_path):
    assert tool._load_latest_claims(tmp_path / "nope.jsonl") == {}
