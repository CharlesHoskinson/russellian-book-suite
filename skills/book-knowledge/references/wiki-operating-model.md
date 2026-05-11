# Wiki operating model

The wiki is the project's persistent epistemic state. It records what the book-author knows, where each piece of knowledge came from, and how that knowledge has changed over time.

## The Karpathy LLM-Wiki pattern

Three layers of artifact, each with different mutability rules:

1. **Raw sources** (`raw/`) — immutable. The bytes of every PDF and markdown file that ever entered the workspace, plus their manifests. Never edited, never deleted.
2. **Wiki** (`wiki/`) — cumulative editable synthesis. Hand-written notes, concept summaries, and entity descriptions that span multiple sources. Edits happen via small append-and-revise deltas, not rewrites.
3. **Navigators** (`wiki/index.md`, `wiki/log.md`, `wiki/current-status.md`) — generated or append-only files that point readers and agents at the current frontier of work.

Raw is the ground truth. Wiki is the synthesis. Navigators are the table of contents. Confusing the layers — editing raw, treating wiki as throwaway, ignoring navigators — destroys the audit trail.

## Page taxonomy

Every wiki page is exactly one of three kinds:

- **`wiki/sources/<doc_id>.md`** — auto-generated per-file summary. One page per ingested document. Contains heading tree (markdown) or page-by-page extract (PDF). NEVER hand-edited; regenerated on every ingest.
- **`wiki/concepts/<slug>.md`** — cross-source idea. Examples: `proof-of-stake.md`, `coroutine-effects.md`, `merkle-mountain-range.md`. Concept pages synthesize across multiple sources. Hand-edited.
- **`wiki/entities/<slug>.md`** — named system, library, product, or person. Examples: `cardano.md`, `tokio.md`, `bertrand-russell.md`. Entity pages describe a referent that exists outside the book. Hand-edited.

Decision rule: if the topic exists only inside one source, leave it in `sources/`. If it spans sources but is an idea, file it in `concepts/`. If it spans sources and is a named referent, file it in `entities/`.

## Backlinks

Use `[[name]]` to refer to other wiki pages by their stem. The link target is the slug, not a full path. Resolution rules:

- `[[cardano]]` resolves to `wiki/entities/cardano.md` if it exists, else `wiki/concepts/cardano.md`, else dangles.
- `[[my-paper-v2]]` resolves to `wiki/sources/my-paper-v2.md`.

`wiki_index_regen.py` collects backlinks during regeneration and surfaces orphans (pages that no other page links to) and dangles (links with no target).

## Page naming

- Source pages: stem matches doc_id exactly. `compute_doc_id` already produces a valid slug.
- Concept and entity pages: kebab-case noun phrases. Lowercase, hyphen-separated, ASCII only. No prepositions or articles unless meaning demands them. `proof-of-stake` not `the-proof-of-stake-protocol`.

## Regeneration cadence

`scripts/wiki_index_regen.py` runs after every ingest. It rebuilds `wiki/index.md` to list all source, concept, and entity pages with their last-modified timestamps and a one-line summary parsed from each page's first paragraph. The index is fully derived; never hand-edited.

`wiki/current-status.md` updates after:

- Every ingest
- Every claim verification batch (one or more `verify_claim` runs)
- Every chapter release
- Every release-gate failure

Status entries summarize "where the book stands now": which chapters are draft-ready, which sources have unverified claims, which concept pages need revision after a recent ingest. The status file is short — one screen — and rewritten in place rather than appended.

## Append-only log

`wiki/log.md` is the audit trail. Every script that mutates workspace state appends a single timestamped entry. Format:

```
- 2026-05-08T12:34:56Z <action> <subject> <key=value pairs>
```

Examples:

```
- 2026-05-08T09:00:01Z ingest my-paper-v2 sha256=a1b2c3d4 nodes=12
- 2026-05-08T09:05:14Z append-claim clm-2026-000017 status=proposed
- 2026-05-08T09:10:42Z verify-claim clm-2026-000017 -> verified
- 2026-05-08T11:22:30Z release-gate chapter-3 result=fail unsupported=2
```

Rules:

- Lines are appended, never re-ordered, never deleted.
- Timestamps are ISO 8601 UTC with seconds precision.
- Each line is self-contained; readers can grep `log.md` and understand state changes without cross-referencing other files.
- If a script mutates workspace state but fails to log, the bug is in the script, not in the log.

## Anti-patterns

- **Editing source pages by hand.** They are regenerated; edits are lost. Put your synthesis in a concept or entity page that links back to the source.
- **Rewriting log entries.** The log is the workspace's memory. Rewriting it destroys the ability to reconstruct past state.
- **Treating wiki as a notes folder.** The wiki is structured: sources / concepts / entities. Free-form notes belong in a scratchpad, not the wiki.
- **One concept page per source citation.** Concept pages are cross-source by definition. If a topic appears in only one source, leave the synthesis on the source page until a second source arrives.
