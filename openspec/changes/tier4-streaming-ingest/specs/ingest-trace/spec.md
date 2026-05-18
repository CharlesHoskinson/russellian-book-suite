# Capability delta: ingest-trace — change: tier4-streaming-ingest

## ADD

### REQ-PERF-050 — Ubiquitous

The `ingest_ledger.ingest()` function in every verifier's
`scripts/ingest_ledger.py` SHALL stream the input JSONL through a
generator (`iter_atoms`) rather than materialising the full
post-enrichment atom list in memory before writing.

**Rationale:** At book-knowledge scale (10,000+ claims), the
post-enrichment atom list — each holding canonical-text, source-spans,
support-chapters, and predicate-derived fields — dominates peak RSS
and OOMs the ingest process. Streaming reduces post-enrichment peak
memory to O(1). **Tested by:**
`skills/neurosym-forge/tests/test_streaming_writer.py::test_streaming_writer_peak_rss_under_threshold`
(added in J1.2)

### REQ-PERF-051 — Ubiquitous

The output `work/claims.edn` produced by streaming ingest SHALL be a
streaming-readable EDN document of the form
`{:version N :atoms [<atom>\n<atom>\n...]}` where each atom occupies
its own line, written incrementally as the generator yields, and the
resulting file SHALL parse byte-equivalently to the previous batched
form when compared as parsed EDN values.

**Rationale:** The downstream Rust EDN parser already accepts
whitespace between vector elements; one-atom-per-line gives a
streaming-readable shape on the Python side without forking the EDN
grammar. Byte-equivalence-as-parsed preserves every existing golden
test. **Tested by:**
`skills/neurosym-forge/tests/test_streaming_writer.py::test_streaming_writer_byte_identical_to_batch`
(added in J1.1)

### REQ-PERF-052 — Optional feature

WHERE the input JSONL exceeds 100 MB on disk, the streaming ingest
SHALL print a progress indicator line `ingested N claims` to stderr
every 1000 atoms yielded. WHERE the input JSONL is at most 100 MB,
the framework SHALL NOT emit progress lines.

**Rationale:** Beyond ~100 MB JSONL, the ingest wall-clock exceeds
30 s and operators start wondering whether the process is hung.
Suppressing the progress line below the threshold keeps the
small-corpus smoke tests silent and stable. **Tested by:**
`skills/neurosym-forge/tests/test_streaming_writer.py::test_streaming_writer_progress_indicator_above_threshold`
(added in J5.1)

### REQ-PERF-053 — Unwanted behaviour

IF the streaming writer's process is killed mid-write (so
`work/claims.edn` is left truncated, missing the closing `]}`), the
framework SHALL leave a sibling `work/claims.edn.partial` marker file
on disk during the write; on the next ingest invocation, the
framework SHALL detect that marker, delete the corrupt
`work/claims.edn`, and start fresh rather than appending to a
truncated document.

**Rationale:** A truncated EDN document is a hard-parse-failure
downstream; without the marker, an operator who re-runs ingest after
a crash gets an obscure parse error from the Rust verifier rather
than an obvious "previous run was killed, restarting cleanly"
message. The marker turns silent corruption into a self-healing
recovery branch. **Tested by:**
`skills/neurosym-forge/tests/test_streaming_writer.py::test_streaming_writer_partial_marker_on_crash`
(added in J4.1) and
`test_streaming_writer_recovery_branch_deletes_stale` (added in J4.2)
