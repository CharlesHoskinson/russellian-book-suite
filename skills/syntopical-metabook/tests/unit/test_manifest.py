import json
from pathlib import Path
import pytest
from scripts.acquire.manifest import (
    append_run_record, AcquireHaltedError, halt_check, read_pending_seeds,
    append_pending_seeds,
)

def test_append_run_record_writes_jsonl(tmp_path):
    path = tmp_path / "manifest.jsonl"
    record = {"run_id": "r1", "started_at": "...", "downloaded": []}
    append_run_record(path, record)
    append_run_record(path, {"run_id": "r2", "started_at": "..."})
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["run_id"] == "r1"

def test_halt_check_raises_if_file_present(tmp_path):
    halt = tmp_path / "HALT"
    halt.write_text("stop")
    with pytest.raises(AcquireHaltedError):
        halt_check(tmp_path)

def test_halt_check_silent_if_absent(tmp_path):
    halt_check(tmp_path)  # no file, no raise

def test_pending_seeds_round_trip(tmp_path):
    p = tmp_path / "pending-seeds.txt"
    append_pending_seeds(p, ["finality SHALL be irreversible", "validators are honest"])
    seeds = read_pending_seeds(p)
    assert seeds == ["finality SHALL be irreversible", "validators are honest"]
    # Appending more accumulates
    append_pending_seeds(p, ["new seed"])
    assert read_pending_seeds(p) == ["finality SHALL be irreversible",
                                     "validators are honest", "new seed"]
