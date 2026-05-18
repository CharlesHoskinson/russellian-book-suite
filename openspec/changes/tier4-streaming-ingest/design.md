# Design: tier4-streaming-ingest

## Streaming EDN shape

The output `work/claims.edn` today looks like:

```edn
{:version 1 :atoms [{:id "c-001" ...} {:id "c-002" ...} ...]}
```

A streaming-readable variant of the same document — byte-equivalent for
the downstream Rust EDN parser — is produced by writing the framing
tokens around an incrementally-emitted atom sequence:

```
OPEN   = "{:version 1 :atoms [\n"
ATOM   = "<edn-repr-of-atom>\n"   (one atom per line)
CLOSE  = "]}\n"
```

Whitespace between vector elements is legal EDN. One atom per line
gives a trivial line-oriented reader on the Python side and preserves
the existing parser's `for atom in edn[":atoms"]` shape.

## Generator-based producer

Replace `compute_atoms` (returns `list[dict]`) with `iter_atoms`
(`Generator[dict, None, None]`):

```python
def iter_atoms(ledger_path: Path, predicates_path: Path) -> Iterator[dict]:
    predicates_data = read_edn_file(predicates_path)
    predicates = predicates_data.get(_KW_PREDICATES, {})
    _validate_against_schema(predicates_path, predicates)

    seen: dict[str, dict] = {}
    with ledger_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            cid = row.get("claim_id") or row.get("id")
            if cid:
                seen[cid] = row   # late-write wins, matches latest_per_id semantics

    for claim in seen.values():
        if not _is_verified(claim):
            continue
        yield _claim_to_atom(claim, predicates)
```

Note: `latest_per_id` dedup still requires reading the whole JSONL
because a later line may supersede an earlier `claim_id`. But the
intermediate `seen` map holds raw JSONL rows (already in RAM as
strings before json.loads), not the post-`_claim_to_atom` enrichment.
The post-mapping is what dominates peak RSS today; deferring it into
the generator is the win.

A future optimisation could push the dedup into a two-pass scan
(pass 1: build `(claim_id → byte_offset)`, pass 2: random-access the
keepers) to drop the `seen` dict entirely, but that's a separate
improvement and not required by the REQs.

## Streaming writer

`scripts/_io.py` gains `write_edn_stream(path, version, atoms_iter)`:

```python
def write_edn_stream(path: Path, version: int, atoms: Iterator[dict]) -> int:
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text("")                           # mark in-flight
    count = 0
    with path.open("w", encoding="utf-8") as f:
        f.write(f"{{:version {version} :atoms [\n")
        for atom in atoms:
            f.write(_write_edn_value(atom))
            f.write("\n")
            count += 1
        f.write("]}\n")
    partial.unlink()                                 # mark clean
    return count
```

`_write_edn_value` reuses the existing EDN serialiser for a single
value (refactor-extract from the current bulk `write_edn_file`).

## Crash recovery (REQ-PERF-053)

A `.partial` sibling marker file is written before the open brace and
deleted after the close brace. The next `ingest()` invocation checks
for `out_path.with_suffix(out_path.suffix + ".partial")`; if it
exists, the previous run did not complete and `out_path` is presumed
corrupt:

```python
partial = out_path.with_suffix(out_path.suffix + ".partial")
if partial.exists():
    print(f"ingest_ledger: previous run crashed mid-write; "
          f"deleting stale {out_path}", file=sys.stderr)
    out_path.unlink(missing_ok=True)
    partial.unlink()
```

The check runs at the start of `ingest()`, before the writer opens.

## Progress indicator (REQ-PERF-052)

```python
ledger_bytes = ledger_path.stat().st_size
verbose = ledger_bytes > 100 * 1024 * 1024  # 100 MB threshold
...
for atom in atoms:
    count += 1
    if verbose and count % 1000 == 0:
        print(f"ingested {count} claims", file=sys.stderr)
```

100 MB chosen because that's the rough JSONL volume where wall-clock
ingest crosses 30 s and operators start wondering whether it hung.

## Atom-streaming vs full-batch trade-offs

| dimension     | full-batch (current)           | streaming (this change)            |
|---------------|--------------------------------|------------------------------------|
| peak RSS      | O(corpus) post-enrichment      | O(corpus) raw JSONL only           |
| crash safety  | atomic — partial output empty  | `.partial` marker, recovery branch |
| append-mode   | trivial (rewrite list, dump)   | requires re-stream                 |
| determinism   | order = list order             | order = JSONL order                |

Append-mode is the only regression: today you can `compute_atoms`,
patch the list, and re-`write_edn_file`. After this change, the
producer is one-shot. The framework doesn't currently use append-mode
anywhere in the verifier scripts (each ingest rebuilds from scratch),
so the regression is acceptable. If a future workflow needs append,
it can call `iter_atoms` itself and stitch the iterators.
