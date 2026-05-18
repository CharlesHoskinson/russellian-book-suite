"""Streaming EDN writer for ingest_ledger output.

REQ-PERF-050, REQ-PERF-051, REQ-PERF-053.

Writes `work/claims.edn` incrementally as a sequence of atoms rather
than materialising the full atom list in memory. The output document
is byte-equivalent (as parsed EDN) to the previously-batched form:

    {:version 1 :atoms [
    <atom-0>
    <atom-1>
    ...
    ]}

Atomic-write pattern: writes go to `path.with_suffix(path.suffix + ".partial")`.
On clean __exit__ the file is fsynced and renamed to `path`. If the
process is killed mid-write the `.partial` sibling remains on disk,
which signals to the next ingest invocation that the previous run
crashed and the in-flight document is corrupt.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from scripts._edn_writer import write_edn


class StreamingAtomWriterError(RuntimeError):
    """Raised when the streaming writer detects an orphan `.partial`."""


def partial_path_for(out_path: Path) -> Path:
    """Return the sibling `.partial` marker path for the given output path."""
    return out_path.with_suffix(out_path.suffix + ".partial")


def check_no_orphan_partial(out_path: Path) -> None:
    """REQ-PERF-053: refuse to continue if a stale `.partial` exists.

    A leftover `<out>.partial` means a previous ingest was killed
    mid-write and the on-disk document is presumed corrupt. The
    framework refuses to silently overwrite or append — the operator
    must delete the marker (and the truncated `<out>` if present) to
    acknowledge the prior failure.
    """
    partial = partial_path_for(out_path)
    if partial.exists():
        raise StreamingAtomWriterError(
            f"previous ingest was interrupted; orphan marker at {partial}. "
            f"Delete {partial} (and {out_path} if it exists) and rerun from "
            f"a clean state."
        )


class StreamingAtomWriter:
    """Context-managed streaming EDN writer for atom sequences.

    Opens the output with `{:version N :atoms [`, accepts atoms via
    `.write(atom)`, closes with `]}` on __exit__. Each atom is
    serialised via the existing `_edn_writer.write_edn` compact form.

    REQ-PERF-050, REQ-PERF-051, REQ-PERF-053.

    Usage::

        with StreamingAtomWriter(out_path) as w:
            for atom in compute_atoms_iter(...):
                w.write(atom)
        # out_path now exists; .partial sibling is gone.
    """

    def __init__(self, path: Path, version: int = 1) -> None:
        self._path = Path(path)
        self._version = int(version)
        self._partial = partial_path_for(self._path)
        self._fh: Any = None
        self._count = 0

    def __enter__(self) -> "StreamingAtomWriter":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Open the .partial sibling. Its presence on disk during the
        # write is the corruption marker; we only rename to the final
        # path once we've successfully written the closing `]}`.
        self._fh = self._partial.open("w", encoding="utf-8", newline="\n")
        self._fh.write(f"{{:version {self._version} :atoms [\n")
        return self

    def write(self, atom: dict) -> None:
        if self._fh is None:
            raise RuntimeError("StreamingAtomWriter.write() outside context")
        self._fh.write(write_edn(atom))
        self._fh.write("\n")
        self._count += 1

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        fh = self._fh
        self._fh = None
        if fh is None:
            return
        try:
            if exc_type is None:
                # Successful run: close the vector + map, fsync, then
                # atomically rename to the final path.
                fh.write("]}\n")
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except (OSError, AttributeError):
                    # fsync unsupported on some platforms / file types;
                    # the flush + rename is still our atomicity story.
                    pass
                fh.close()
                # os.replace is atomic on POSIX and Windows.
                os.replace(self._partial, self._path)
            else:
                # Exception path: close the (truncated) .partial and
                # leave it on disk as the corruption marker. The next
                # ingest's check_no_orphan_partial() will refuse to
                # continue until the operator clears it.
                try:
                    fh.close()
                except Exception:
                    pass
                # Do NOT delete .partial — that's the whole point of the
                # marker. Do NOT touch self._path either; the previous
                # `claims.edn` (if any) stays where it was.
        finally:
            # Don't suppress the original exception.
            pass

    @property
    def count(self) -> int:
        """Number of atoms written so far."""
        return self._count


def _emit_progress(n: int, *, stream: Any = sys.stderr) -> None:
    """REQ-PERF-052: print a progress line every 1000 atoms."""
    print(f"ingest: {n} atoms processed", file=stream)
