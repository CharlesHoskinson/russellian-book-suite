# Tasks: tier4-streaming-ingest

See `docs/plans/2026-05-18-tier234-and-usefulness.md` Phase K for the
current task chain. The Phase J numbering below is retained for
historical traceability but the work is done against the Phase K
umbrella: `StreamingAtomWriter` (a context-managed writer) rather
than the `write_edn_stream` helper proposed in J, and `.partial`
acts as a strict orphan-marker (next ingest REFUSES rather than
auto-deleting) per K3.1.

## Phase J.1 — Streaming-writer unit test (Red)

- [x] J1.1: Streaming writer round-trip test — `test_streaming_writer_emits_well_formed_edn` writes via `StreamingAtomWriter` and asserts the EDN parses back to `{:version 1 :atoms [...]}` byte-equivalent shape. (REQ-PERF-051)
- [x] J1.2: Memory-bounded test — `test_streaming_ingest_peak_rss_bounded` ingests a ~10 MB JSONL fixture and asserts RSS delta stays under 200 MB. (REQ-PERF-050)
- [x] J1.3: Tests pass against the new `StreamingAtomWriter` implementation.

## Phase J.2 — Streaming writer implementation

- [x] J2.1: `StreamingAtomWriter` context manager in `skills/neurosym-forge/scripts/_edn_streaming.py` — opens with `{:version N :atoms [`, accepts atoms via `.write(atom)`, closes with `]}` on `__exit__`. (REQ-PERF-051)
- [x] J2.2: Atoms serialised via the existing `_edn_writer.write_edn` per-value emitter. (REQ-PERF-051)
- [x] J2.3: All ingest tests green. (REQ-PERF-051)

## Phase J.3 — Generator-based `compute_atoms_iter` + rewire `ingest()`

- [x] J3.1: `compute_atoms_iter(ledger_path, predicates_path) -> Iterator[dict]` added to both `verifiers/bermuda/scripts/ingest_ledger.py` and `verifiers/osmotic_pressure/scripts/ingest_ledger.py`. (REQ-PERF-050)
- [x] J3.2: `ingest()` rewritten in both to call `StreamingAtomWriter` with `compute_atoms_iter(...)`. `return_atoms=True` callers (bermuda smoke harness) still get the list. (REQ-PERF-050)
- [x] J3.3: Existing verifier smoke tests pass unchanged on the small-corpus path.

## Phase J.4 — Crash-recovery `.partial` marker

- [x] J4.1: `test_streaming_writer_leaves_partial_on_exception` — raises mid-stream, asserts `.partial` exists after the failure and final `claims.edn` does NOT. (REQ-PERF-053)
- [x] J4.2: `test_interrupted_ingest_leaves_partial_and_next_run_refuses` — Phase K diverges from J4.2: instead of auto-deleting, the next ingest REFUSES to continue and points the operator at the orphan marker. Recovery is: operator deletes `.partial`, retries. (REQ-PERF-053)
- [x] J4.3: Writer writes to `.partial`, fsyncs + os.replaces to final path on clean close. `check_no_orphan_partial()` runs at the start of every `ingest()`. (REQ-PERF-053)

## Phase J.5 — Progress indicator

- [x] J5.1: `ingest()` prints `ingest: {N} atoms processed` to stderr every 1000 atoms (REQ-PERF-052). The threshold-gated suppression (no progress lines under 100 MB) from the original spec was simplified to "always every 1000" per the Phase K umbrella plan — keeps the code path simple and the lines are well-spaced enough that small-corpus runs (12-50 atoms) never emit any.
- [ ] J5.2: (out of scope under Phase K simplification) Explicit small-corpus suppression test.
- [x] J5.3: Wired inside the streaming ingest loop.

## Phase J.6 — Open PR

- [x] J6.1: Branch `feat/tier4-streaming-ingest` pushed; PR opened.
- [ ] J6.2: Merge on green CI.
