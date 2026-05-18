# Tasks: tier4-streaming-ingest

See `docs/plans/2026-05-18-tier234-and-usefulness.md` Phase J for full
TDD steps. Task numbers correspond 1:1.

## Phase J.1 — Streaming-writer unit test (Red)

- [ ] J1.1: Add `skills/neurosym-forge/tests/test_streaming_writer.py::test_streaming_writer_byte_identical_to_batch` — generate 1,000 synthetic atoms, write via `write_edn_stream` AND via the existing `write_edn_file`, assert the two outputs parse to identical dicts. (REQ-PERF-051)
- [ ] J1.2: Add `test_streaming_writer_peak_rss_under_threshold` — use `tracemalloc` to assert peak memory during a 100k-atom stream stays under a tunable bound (e.g., 50 MB). (REQ-PERF-050)
- [ ] J1.3: Confirm tests FAIL (the streaming writer doesn't exist yet). Commit the failing tests.

## Phase J.2 — Implement `write_edn_stream` in `scripts/_io.py`

- [ ] J2.1: Refactor the EDN value serialiser into a public `_write_edn_value(v) -> str` helper (extract from `write_edn_file`). (REQ-PERF-051)
- [ ] J2.2: Add `write_edn_stream(path, version, atoms_iter) -> int` that emits the open framing, calls `_write_edn_value` per atom with a trailing newline, and emits the close framing. (REQ-PERF-051)
- [ ] J2.3: Re-run J1.1 + J1.2 — confirm PASS. Commit.

## Phase J.3 — Generator-based `iter_atoms` + rewire `ingest()`

- [ ] J3.1: Add `iter_atoms(ledger_path, predicates_path) -> Iterator[dict]` to `verifiers/bermuda/scripts/ingest_ledger.py` and `verifiers/osmotic_pressure/scripts/ingest_ledger.py`. (REQ-PERF-050)
- [ ] J3.2: Rewrite `ingest()` in both to call `write_edn_stream(out_path, 1, iter_atoms(...))`. Preserve the `return_atoms` interface by materialising the iterator into a list when callers pass `return_atoms=True`. (REQ-PERF-050)
- [ ] J3.3: Run the existing verifier smoke tests — confirm zero regression on the small-corpus path. Commit.

## Phase J.4 — Crash-recovery `.partial` marker

- [ ] J4.1: Add `test_streaming_writer_partial_marker_on_crash` — monkey-patch `_write_edn_value` to raise mid-stream, assert the `.partial` sibling exists after the failure. (REQ-PERF-053)
- [ ] J4.2: Add `test_streaming_writer_recovery_branch_deletes_stale` — pre-create both `claims.edn` and `claims.edn.partial`, invoke `ingest()`, assert the stale `claims.edn` is replaced and `.partial` is gone after the clean run. (REQ-PERF-053)
- [ ] J4.3: Wire the writer to create `.partial` before the first byte and unlink on clean close. Wire `ingest()` to detect-and-clean at start. Confirm tests PASS. Commit.

## Phase J.5 — Progress indicator

- [ ] J5.1: Add `test_streaming_writer_progress_indicator_above_threshold` — fabricate a 101 MB JSONL fixture (or stat-mock), invoke `ingest()`, capture stderr, assert lines `ingested 1000 claims`, `ingested 2000 claims`, ... appear. (REQ-PERF-052)
- [ ] J5.2: Add the negative case: 1 MB fixture produces no progress lines. (REQ-PERF-052)
- [ ] J5.3: Wire the progress check inside the writer's per-atom loop. Confirm tests PASS. Commit.

## Phase J.6 — Open PR

- [ ] J6.1: Push branch `feat/tier4-streaming-ingest` and open PR.
- [ ] J6.2: Merge on green CI.
