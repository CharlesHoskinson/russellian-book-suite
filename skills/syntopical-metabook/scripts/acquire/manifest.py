"""Append-only audit manifest for Acquire runs, plus HALT and feed-acquire helpers."""
from __future__ import annotations
import json
from pathlib import Path

class AcquireHaltedError(RuntimeError):
    pass

def append_run_record(manifest_path: Path, record: dict) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

def halt_check(acquisition_dir: Path) -> None:
    """Raise AcquireHaltedError if a HALT file exists (REQ-ACQ-8)."""
    halt = Path(acquisition_dir) / "HALT"
    if halt.exists():
        raise AcquireHaltedError(f"HALT file present at {halt}")

def append_pending_seeds(path: Path, seeds: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for s in seeds:
            f.write(s.strip() + "\n")

def read_pending_seeds(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
