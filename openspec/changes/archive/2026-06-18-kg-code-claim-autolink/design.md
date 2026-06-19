# Design: kg-code-claim-autolink

## Schema

S6 adds one derived relation and one additive attribute:

- `link-evidence`: `id`, `code-id`, `claim-id`, `kind`, `score`, `witness`,
  `provenance`, `promoted`.
- `code-claim-link.kind`: the deterministic promotion kind for derived canonical
  links. Existing S1 consumers still query only `code-id` and `claim-id`, so the
  change is additive.

The code graph already carries graphify `source_file` in its JSON input. S6 adds
`code-node.source-file` and projects graphify `source_file` into that column so
module-path matching can be exact and replayable. These are derived graph
relations, not ledger record fields; no claim-record JSON Schema changes.

## Source-File Provenance

A claim source file is resolved conservatively from projected `source-span` rows:

1. If `source-span.doc-id` looks like a path with a source-file extension, use it.
2. If the span points at a projected `source` row and that source row has `path`,
   use the source `path`.

Paths are normalized only by replacing backslashes with `/`, removing a leading
`./`, and collapsing duplicate separators. There is no fuzzy, basename-only, or
case-insensitive match. A claim with no resolvable source file emits no file-path
candidate.

For a file-path link, the matched code node must be module-like: its `source-file`
matches the claim source file, and its label or id exactly names either the full
path or the path basename after the same normalization. This avoids promoting every
function node that shares a file.

## Symbol Mentions

Mention extraction is high precision only:

- backtick-quoted identifiers such as `` `Evictor.rebalance` ``;
- unquoted dotted identifiers such as `Evictor.rebalance`.

Bare words and substrings are ignored. A mention resolves to code nodes by exact
symbol identity against `code-node.label` or `code-node.id`, with one conservative
normalization: a label ending in `()` also exposes the label without that suffix.

## Exact-Symbol Trail

An exact-symbol candidate is promotable only when the resolved code node has an
incoming trail made solely of `contains` or `uses` code-edge relationships. The
trail is resolved by deterministic breadth-first search from the target node
backward over incoming `contains`/`uses` edges, then emitted in forward order.
The witness is canonical JSON containing the mention symbol and the trail.

If a mention resolves to a node but has no such trail, it is evidence-only with
score `0.5`. It is not canonical.

## Promotion Rule

Precision is the governing rule. A candidate becomes canonical only when it is:

- deterministic;
- unambiguous for the evidence kind and mention;
- structurally witnessed.

File-path candidates are canonical only when exactly one module-like code node
matches a claim source file. Exact-symbol candidates are canonical only when one
mention resolves to exactly one code node and that node has a `contains`/`uses`
trail. Ambiguous mentions store every candidate as `link-evidence` with
`promoted=false`; none becomes a canonical `code-claim-link`.

There are no learned signals, embeddings, GNNs, or LLM calls in S6. Learned ranking
is deferred to S9.

## Determinism

The linker reads an already-projected Cozo graph and writes derived rows to
`code-claim-link` and `link-evidence` in canonical sorted order. It does not write
the ledger or mutate graphify inputs. `canonical_autolink_result` serializes links
and evidence for result-set equality and golden comparison.
