# Change: tier4-streaming-ingest

**Tier:** 4 of 4
**Branch:** `feat/tier4-streaming-ingest`
**Depends on:** none

## Why

`verifiers/*/scripts/ingest_ledger.py::ingest()` currently materialises
the full atom list in memory before handing it to `write_edn_file`:

```python
def ingest(ledger_path, predicates_path, out_path, return_atoms=False):
    atoms = compute_atoms(ledger_path, predicates_path)   # full list in RAM
    write_edn_file(out_path, {_KW_VERSION: 1, _KW_ATOMS: atoms})
    ...
```

`compute_atoms` itself reads the entire JSONL into `rows`, then
deduplicates into `latest`, then maps to `atoms`. At today's
verifier scale (Bermuda: ~50 claims, Osmotic: ~12 claims) this is
fine. At book-knowledge scale (10,000+ claims × ~100 predicates) the
peak RAM is dominated by `atoms`, a Python `list` of ~10k dicts each
holding the canonical text (200-byte truncation) plus source-spans,
support arrays, etc. — easily 100s of MB before the writer even starts.

The framework is positioned as general-purpose: any future verifier
operating on a corpora-scale ledger (a multi-book domain, a wiki-scale
knowledge graph) will OOM on ingest. Stream the ingest: read JSONL
line-by-line, emit each atom incrementally to the EDN writer, never
hold more than one atom in flight.

## What

- Rewrite `ingest_ledger.ingest()` to stream JSONL line-by-line via a
  generator rather than `compute_atoms` materialising the full list.
- Add a streaming EDN writer that opens the file with the framing
  `{:version 1 :atoms [`, emits one atom per line as the generator
  yields, and closes with `]}` on generator exhaustion.
- Add a progress indicator (every 1000 claims) when the input JSONL
  exceeds 100 MB.
- Write a `.partial` sibling marker before the streaming write begins
  and unlink it on clean completion; if a future ingest sees the
  `.partial` marker it knows the previous run crashed mid-write and
  starts fresh rather than appending.

## Capabilities touched

- `ingest-trace` — MODIFY (adds REQ-PERF-050..053)

## Implementation notes

See `docs/plans/2026-05-18-tier234-and-usefulness.md`, Phase J.

## Acceptance

- A 100k-claim synthetic JSONL ingests with peak RSS under 200 MB
  (vs. the current ~2 GB it would take with full materialisation).
- The produced `work/claims.edn` parses identically to the
  previously-batched form (golden round-trip preserved).
- Killing the ingest process mid-write leaves a `.partial` marker;
  the next ingest detects it, deletes the stale file, and starts
  fresh rather than appending to a corrupt EDN document.
- The progress line `ingested N/M claims (P%)` appears every 1000
  claims when the input exceeds 100 MB and is suppressed otherwise.
