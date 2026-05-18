"""Tests for the streaming ingest path (REQ-PERF-050..053).

Covers:
  * StreamingAtomWriter atomic-write: `.partial` cleared on success.
  * Memory-bounded ingest of a large synthetic JSONL: peak RSS stays
    well under the threshold the materialise-everything path would hit.
  * Corruption-recovery: an interrupted ingest leaves `.partial` on
    disk, the final output is NOT renamed into place, and the next
    ingest refuses to continue with a clear error pointing at the
    orphan marker.
"""
from __future__ import annotations

import gc
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

import psutil
import pytest

# The streaming writer + check live in neurosym-forge's scripts/.
# The pyproject sets pythonpath=["."], so `from scripts.foo import ...`
# resolves against skills/neurosym-forge/scripts/.
from scripts._edn_reader import Keyword, read_edn
from scripts._edn_streaming import (
    StreamingAtomWriter,
    StreamingAtomWriterError,
    check_no_orphan_partial,
    partial_path_for,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_osmotic_ingest_module() -> ModuleType:
    """Load `verifiers/osmotic_pressure/scripts/ingest_ledger.py` as a
    sibling module without colliding with neurosym-forge's `scripts`
    package (which is already loaded as the top-level `scripts`).
    """
    src = REPO_ROOT / "verifiers" / "osmotic_pressure" / "scripts" / "ingest_ledger.py"
    spec = importlib.util.spec_from_file_location(
        "osmotic_ingest_ledger_under_test", src,
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# StreamingAtomWriter unit tests (REQ-PERF-050, 051)
# ---------------------------------------------------------------------------

def _atom(i: int) -> dict:
    return {
        Keyword("id"): f"a-{i:06d}",
        Keyword("doc"): f"atom number {i}",
        Keyword("kind"): Keyword("symbol"),
        Keyword("sort"): Keyword("formula"),
        Keyword("name"): Keyword("OPAQUE"),
    }


def test_streaming_writer_emits_well_formed_edn(tmp_path: Path) -> None:
    """A streamed claims.edn parses back to {:version 1 :atoms [...]}."""
    out = tmp_path / "claims.edn"
    with StreamingAtomWriter(out, version=1) as w:
        for i in range(5):
            w.write(_atom(i))
    assert out.exists()
    payload = read_edn(out.read_text(encoding="utf-8"))
    assert payload[Keyword("version")] == 1
    atoms = payload[Keyword("atoms")]
    assert len(atoms) == 5
    assert atoms[0][Keyword("id")] == "a-000000"
    assert atoms[4][Keyword("id")] == "a-000004"


def test_streaming_writer_clears_partial_on_success(tmp_path: Path) -> None:
    """REQ-PERF-053: a clean run renames `.partial` into the final path."""
    out = tmp_path / "claims.edn"
    partial = partial_path_for(out)
    with StreamingAtomWriter(out) as w:
        w.write(_atom(0))
        # Mid-write the partial exists and the final does NOT.
        assert partial.exists()
        assert not out.exists()
    # Post-close: partial gone, final there.
    assert not partial.exists()
    assert out.exists()


def test_streaming_writer_leaves_partial_on_exception(tmp_path: Path) -> None:
    """REQ-PERF-053: an exception mid-write leaves `.partial` as the
    corruption marker and does NOT rename to the final path."""
    out = tmp_path / "claims.edn"
    partial = partial_path_for(out)

    class _Boom(RuntimeError):
        pass

    with pytest.raises(_Boom):
        with StreamingAtomWriter(out) as w:
            w.write(_atom(0))
            w.write(_atom(1))
            raise _Boom("simulated mid-ingest crash")

    # Partial sticks around as the corruption marker; final never appeared.
    assert partial.exists(), "expected `.partial` corruption marker on disk"
    assert not out.exists(), "expected final output NOT to be renamed on crash"


def test_check_no_orphan_partial_raises_on_existing_marker(tmp_path: Path) -> None:
    """REQ-PERF-053: ingest must refuse when an orphan `.partial` exists."""
    out = tmp_path / "claims.edn"
    partial = partial_path_for(out)
    partial.write_text("", encoding="utf-8")  # simulate a prior crash
    with pytest.raises(StreamingAtomWriterError) as excinfo:
        check_no_orphan_partial(out)
    msg = str(excinfo.value)
    # Error must point at the orphan marker by name so the operator
    # knows exactly what to delete.
    assert str(partial) in msg
    assert "interrupted" in msg.lower() or "previous" in msg.lower()


def test_check_no_orphan_partial_is_noop_when_clean(tmp_path: Path) -> None:
    out = tmp_path / "claims.edn"
    # No marker; must not raise.
    check_no_orphan_partial(out)


# ---------------------------------------------------------------------------
# Memory-bounded ingest (REQ-PERF-050)
# ---------------------------------------------------------------------------

def _build_large_jsonl(path: Path, n_claims: int, padding_kb: int = 1) -> None:
    """Write a JSONL ledger with `n_claims` verified rows. Each row
    carries ~`padding_kb` KB of canonical_text payload so the ledger
    grows to a realistic on-disk size."""
    pad = "x" * (padding_kb * 1024)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for i in range(n_claims):
            row = {
                "claim_id": f"c-{i:07d}",
                "claim_type": "fact",
                "canonical_text": f"fact-{i} {pad}",
                "status": "verified",
                "confidence": 1.0,
                "source_spans": [{"doc_id": "synthetic", "locator_text": f"row {i}"}],
                "supports_chapters": [],
            }
            f.write(json.dumps(row) + "\n")


def _build_minimal_predicates(path: Path) -> None:
    """Write an empty predicates.edn. The ingester accepts an empty
    predicates map: every claim becomes an OPAQUE atom, which still
    exercises the streaming path through `_claim_to_atom`."""
    path.write_text("{:predicates {}}\n", encoding="utf-8")


@pytest.mark.slow
def test_streaming_ingest_peak_rss_bounded(tmp_path: Path) -> None:
    """REQ-PERF-050: a 10MB+ JSONL streams without materialising the
    full atom list. Peak RSS over the streaming run stays under a
    threshold the materialise-everything path would routinely blow
    past at corpus scale.

    Threshold-choice notes: we measure the RSS delta from baseline,
    not absolute RSS (the interpreter + already-loaded modules push
    absolute RSS to 80-150 MB before we do anything). A streaming
    ingest of 10k claims @ 1KB padding writes ~12 MB to disk; the
    streaming peak-delta should be a few MB. We set the bar at 200 MB
    delta — generous to absorb interpreter quirks while still being
    well under the ~2 GB the materialise path would hit at 10x the
    fixture size.
    """
    # Import inside the test so the import cost doesn't show up in
    # baseline-RSS measurement noise.
    ingest_mod = _load_osmotic_ingest_module()
    ingest = ingest_mod.ingest

    ledger = tmp_path / "ledger.jsonl"
    predicates = tmp_path / "predicates.edn"
    out = tmp_path / "claims.edn"

    # 10k claims * ~1KB padding ≈ 10-12 MB on disk.
    _build_large_jsonl(ledger, n_claims=10_000, padding_kb=1)
    _build_minimal_predicates(predicates)
    assert ledger.stat().st_size >= 10 * 1024 * 1024, (
        f"fixture too small: {ledger.stat().st_size} bytes"
    )

    gc.collect()
    proc = psutil.Process(os.getpid())
    baseline_rss = proc.memory_info().rss

    n = ingest(ledger, predicates, out)

    gc.collect()
    peak_rss = proc.memory_info().rss
    delta = peak_rss - baseline_rss

    assert n == 10_000, f"expected 10_000 atoms, got {n}"
    assert out.exists()
    assert not partial_path_for(out).exists(), (
        "streaming run left an orphan .partial behind"
    )

    threshold = 200 * 1024 * 1024  # 200 MB RSS delta
    assert delta < threshold, (
        f"streaming ingest peak-RSS delta {delta / 1024 / 1024:.1f} MB "
        f"exceeded threshold {threshold / 1024 / 1024:.1f} MB; the streaming "
        f"path may be materialising the atom list"
    )


# ---------------------------------------------------------------------------
# Corruption-recovery (REQ-PERF-053)
# ---------------------------------------------------------------------------

def test_interrupted_ingest_leaves_partial_and_next_run_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REQ-PERF-053: simulate ingest interruption mid-stream. Verify:
      (a) `.partial` exists on disk after the crash;
      (b) final `claims.edn` does NOT exist;
      (c) the next ingest invocation refuses to continue and the
          error message points at the orphan marker.
    """
    ingest_mod = _load_osmotic_ingest_module()

    ledger = tmp_path / "ledger.jsonl"
    predicates = tmp_path / "predicates.edn"
    out = tmp_path / "claims.edn"
    _build_large_jsonl(ledger, n_claims=100, padding_kb=1)
    _build_minimal_predicates(predicates)

    # Monkey-patch the writer to raise on the 5th atom: simulate
    # SIGKILL / Ctrl-C during the streaming write.
    real_write = StreamingAtomWriter.write
    state = {"calls": 0}

    def boom_write(self: StreamingAtomWriter, atom: dict) -> None:
        state["calls"] += 1
        if state["calls"] == 5:
            raise RuntimeError("simulated mid-ingest crash")
        real_write(self, atom)

    monkeypatch.setattr(StreamingAtomWriter, "write", boom_write)

    with pytest.raises(RuntimeError, match="simulated mid-ingest crash"):
        ingest_mod.ingest(ledger, predicates, out)

    partial = partial_path_for(out)
    assert partial.exists(), "expected `.partial` marker after simulated crash"
    assert not out.exists(), "final claims.edn should not exist after crash"

    # Restore the real writer; the next ingest must refuse because of
    # the orphan marker (no need to actually attempt writing).
    monkeypatch.setattr(StreamingAtomWriter, "write", real_write)

    with pytest.raises(StreamingAtomWriterError) as excinfo:
        ingest_mod.ingest(ledger, predicates, out)
    msg = str(excinfo.value)
    assert str(partial) in msg, (
        f"recovery-refusal error must name the orphan marker; got: {msg!r}"
    )

    # After the operator clears the marker, the next ingest succeeds.
    partial.unlink()
    n = ingest_mod.ingest(ledger, predicates, out)
    assert n == 100
    assert out.exists()
    assert not partial_path_for(out).exists()
