# BookLogic v0.4 PR-2 — Design

Date: 2026-05-14
Author: Charles
Status: Draft, pending user approval
Parent spec: `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md`

## Problem

Three concrete blockers remain after PR-1 of the v0.4 mission:

1. **The EDN reader/writer cannot handle the event-stream syntax the umbrella spec called for.** Symbols (`source/ingested` as a list head) and tagged literals (`#inst "2026-05-14T..."` for timestamps) are required for the trace shape; PR-1 deliberately excluded both to keep its scope contained.
2. **The exporter does not exist yet.** `book-knowledge` writes `claims/ledger.jsonl`, `claims/events.jsonl`, and `raw/manifests/*.json` but emits no symbolic event stream consumable by ClojureScript.
3. **The Rust verdict serialization still uses `serde_json::to_string`.** PR-1 fixed every other Python↔CLJS↔Rust boundary; the verdict return-trip is the last seam. CLJS reads the return value with `cljs.reader/read-string` (EDN), so the JSON output gets mis-parsed in the same way the forward direction did before PR-1.

Without all three, PR-5 (the real Bermuda Z3 run) cannot work and the umbrella spec's D2 deliverable cannot ship.

## What ships

A single PR-2 covering the three carry-overs:

- **D1.** EDN reader/writer extensions: `Symbol` dataclass; tagged-literal dispatch with `#inst` handling; matching writer emission for both
- **D2.** `book-knowledge/scripts/export_symbolic_trace.py` — reads ledger + events + manifests, emits a regenerable `analysis/ingest-trace.edn`
- **D3.** `book-knowledge/scripts/load_symbolic_trace.py` — mirror that re-parses the trace back to Python events (used by tests and downstream-skill validation)
- **D4.** `book-knowledge/assets/ingest-trace.schema.json` — closed-event-shape schema enumerating the valid event heads and their payload constraints
- **D5.** Rust verdict EDN emission — small `ir::emit_verdict_edn` helper, replaces the `serde_json::to_string` call on the return trip; emits keywords with leading `:` so CLJS reader returns keywords
- **D6.** Bermuda smoke: regenerate `examples/bermuda-manual/analysis/ingest-trace.edn` from the live ledger; commit the artifact as a worked example

## Component design

### EDN reader extensions

Add to `skills/neurosym-forge/scripts/_edn_reader.py`:

```python
@dataclass(frozen=True)
class Symbol:
    """An EDN symbol. Hashable; equal by value."""
    name: str
    namespace: str | None = None

    def __str__(self) -> str:
        if self.namespace:
            return f"{self.namespace}/{self.name}"
        return self.name
```

In `_Parser._parse_atom`, recognise bare identifiers (start with a letter or `_`, may contain `/` once) as Symbols rather than rejecting them with "unrecognised atom". `true`, `false`, `nil` keep their current literal handling — they take precedence over symbol parsing.

In `_Parser._parse_form`, replace the blanket `#` rejection with dispatch on the tag name:

```python
if c == "#":
    self._advance()
    if self._eof():
        raise EdnReadError("dangling #")
    tag_start = self.pos
    while not self._eof() and self._peek() not in " \t\n\r,()[]{}\";":
        self.pos += 1
    tag = self.src[tag_start:self.pos]
    if tag == "inst":
        # #inst "<ISO-8601 datetime>"
        self._skip_ws_and_comments()
        value = self._parse_form()
        if not isinstance(value, str):
            raise EdnReadError(f"#inst expects a string, got {type(value).__name__}")
        try:
            return _parse_inst(value)
        except ValueError as e:
            raise EdnReadError(f"invalid #inst literal: {e}")
    raise EdnReadError(f"unknown tag #{tag!r}")
```

`_parse_inst` parses an ISO-8601 string into a `datetime.datetime` (timezone-aware where present). Pythonic format like `"2026-05-12T16:13:51.630442Z"` parses via `datetime.fromisoformat` after a trivial `"Z" -> "+00:00"` substitution.

### EDN writer extensions

Add to `skills/neurosym-forge/scripts/_edn_writer.py`:

```python
def _emit_compact(value):
    # ... existing ...
    if isinstance(value, Symbol):
        return str(value)
    if isinstance(value, datetime.datetime):
        # Emit as #inst with ISO-8601 string
        iso = value.isoformat()
        # canonicalise +00:00 → Z for the common UTC case (optional)
        if iso.endswith("+00:00"):
            iso = iso[:-6] + "Z"
        return f'#inst "{iso}"'
```

Round-trip: `read_edn(write_edn(dt)) == dt` for any `datetime.datetime`.

### `export_symbolic_trace.py`

Lives at `skills/book-knowledge/scripts/export_symbolic_trace.py`. Reads:

- `<workspace>/raw/manifests/*.json` → emits `(source/ingested {:doc/id "..." :ingested-at #inst "..." :kind :... :sha256 "..." :path "..." :title "..."})` per file. The `:kind` is inferred from the manifest's source-type hint (`:pdf`, `:markdown`, `:thesis`, `:yaml`); falls back to `:unknown` if not derivable.
- `<workspace>/claims/ledger.jsonl` → for each claim's first appearance, emits `(claim/proposed {:claim/id "..." :text "..." :source/spans [...] :confidence 0.x :proposed-at #inst "..."})`. The `:proposed-at` instant comes from `created_at` in the ledger record.
- `<workspace>/claims/events.jsonl` (if present) → for each state transition, emits `(claim/<status> {:claim/id "..." :method :... :ticket-id "..." :transitioned-at #inst "..."})`. Status maps `verified → claim/verified`, `disputed → claim/disputed`, `superseded → claim/superseded`, `refuted → claim/refuted`. The `:method` defaults to the event's `cause_class`.

Output:

```clojure
{:version 1
 :book/id "<workspace-slug>"
 :events
 [(source/ingested {...})
  (claim/proposed {...})
  (claim/verified {...})
  ...]}
```

Events are ordered by timestamp. Idempotent: re-running produces the same output for an unchanged ledger + manifests.

CLI:

```
python -m scripts.export_symbolic_trace --workspace <path> --out <path>/analysis/ingest-trace.edn
```

`--out` defaults to `<workspace>/analysis/ingest-trace.edn`.

### `load_symbolic_trace.py`

The inverse: reads `ingest-trace.edn` and returns a structured Python dict:

```python
{
    "version": 1,
    "book_id": "bermuda-manual",
    "events": [
        {"head": Symbol("ingested", namespace="source"),
         "payload": {Keyword("doc-id"): "...", Keyword("ingested-at"): datetime(...), ...}},
        ...
    ],
}
```

Used by tests; potentially used by future skills (PR-3 BookLogic compiler will consume the trace).

### `ingest-trace.schema.json`

A JSON Schema describing the EDN structure as Python dicts (post-read). The closed-event-head set in v0.4 PR-2:

- `source/ingested`
- `claim/proposed`
- `claim/verified`
- `claim/disputed`
- `claim/superseded`
- `claim/refuted`

Each head has a required-keys payload schema; unknown keys are allowed (so future skills can attach metadata).

### Rust verdict EDN emission

In `rust-verifier/src/ir.rs` (Bermuda's file and the template):

Replace:

```rust
pub fn emit_verdict(v: &Verdict) -> String {
    serde_json::to_string(v).unwrap_or_else(|_| "{\"status\":\"unknown\"}".to_string())
}
```

with a hand-rolled EDN emitter:

```rust
pub fn emit_verdict(v: &Verdict) -> String {
    let mut out = String::from("{");
    out.push_str(":status :");
    out.push_str(&v.status);
    out.push_str(" :core [");
    for (i, claim_id) in v.core.iter().enumerate() {
        if i > 0 { out.push(' '); }
        out.push('"');
        out.push_str(&edn_escape(claim_id));
        out.push('"');
    }
    out.push_str("] :explanation \"");
    out.push_str(&edn_escape(&v.explanation));
    out.push('"');
    out.push('}');
    out
}

fn edn_escape(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}
```

The output is intentionally minimal: only the fields CLJS reads (`:status`, `:core`, `:explanation`). Future fields (`:verified`, `:proofs`, `:graph-summary`) are added incrementally; PR-5 verifies the actual round-trip and adds whatever CLJS needs.

The Rust template-shape test asserts the function uses no `serde_json::to_string` on the verdict path.

### Bermuda smoke artifact

Commit the regenerated trace to `examples/bermuda-manual/analysis/ingest-trace.edn` as part of this PR. Demonstrates the exporter on a real workspace; provides a fixture for future tests.

## Workspace mutation

- PR-2 writes to `skills/book-knowledge/` (new exporter, loader, schema; tests).
- Updates `skills/neurosym-forge/scripts/_edn_reader.py`, `_edn_writer.py`, and their tests.
- Updates `skills/neurosym-forge/assets/project-template/rust-verifier/src/ir.rs.tmpl` (verdict emission).
- Updates `verifiers/bermuda/rust-verifier/src/ir.rs` (verdict emission, lockstep with template).
- Creates `examples/bermuda-manual/analysis/ingest-trace.edn`.
- Touches no other Bermuda files.

The trace file under `analysis/` is a NEW subdirectory of the Bermuda workspace; doesn't conflict with `book-knowledge`'s `raw/`, `wiki/`, `claims/`, `graph/` ownership.

## Schema constraints

The `events.schema.json` already exists for the transition-log shape. PR-2 keeps it untouched and adds a SECOND schema at `ingest-trace.schema.json` for the EDN-event trace. Two schemas, two purposes; no merge.

## Non-goals

- BookLogic DSL forms (PR-3+)
- Atom emission events in the trace (the verifier emits those at run time; not book-knowledge's job)
- Real Z3 run against the trace (PR-5)
- Multi-book trace aggregation (deferred — v0.5)

## Workflow

Six tasks, ~2 days:

1. EDN reader: Symbol + #inst (TDD, ~12 new tests)
2. EDN writer: Symbol + datetime emission (TDD, ~6 new tests)
3. `export_symbolic_trace.py` + `load_symbolic_trace.py` + schema (TDD, ~10 new tests)
4. Bermuda trace generation + commit
5. Rust verdict EDN emission + template-shape test + Bermuda lockstep
6. Smoke + PR

## Open questions

1. **Should the trace include atom/emitted events from the verifier?** Decision: NO for PR-2. Those happen at verification time inside the verifier, not at ingestion time inside book-knowledge. Adding them would couple book-knowledge to the verifier. They go into a separate `verifiers/<slug>/work/verification-trace.edn` in PR-5 if needed.
2. **Idempotency: should the exporter overwrite or append?** Recommendation: regenerable (overwrite). The exporter derives every event from authoritative sources (ledger + manifests + events log); re-running produces the same output. Append-only would require careful "skip-already-emitted" logic that the ledger doesn't natively support.
3. **Sort order within a single timestamp?** Stable by source: manifests first (alphabetical by doc_id), then ledger entries (by claim_id), then transition events (by event line number). Ties broken deterministically.
4. **Should we extend the Python exporter to also emit a JSON-shaped trace alongside the EDN one?** No. EDN is the new canonical format. Skills that need to consume the trace use the Python `load_symbolic_trace` helper.

## Estimated effort

~2 days.

## Deliverables

- This spec
- PR-2 plan (next file, written by writing-plans skill)
- Merged PR
- New `examples/bermuda-manual/analysis/ingest-trace.edn` artifact
