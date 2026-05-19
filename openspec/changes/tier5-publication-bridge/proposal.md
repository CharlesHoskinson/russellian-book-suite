# Change: tier5-publication-bridge

**Tier:** 5 of 5 (scale + author-facing tier)
**Branch:** `plan/tier5-scale-author`
**Depends on:** Tier 1-4 landed; composes with tier5-semantic-retrieval
(Phase Q) for `:semantic-neighbours`

## Why

Verdicts land in `work/verdict.edn` and `qa/verification-defects.json`.
Both are machine-readable; neither is visible to a human author reading
the manuscript. An author who runs `make ci` and sees `:status :unsat`
has to cross-reference the verdict's claim ids against the source
markdown by hand to figure out which paragraph the defect is about.
That's the friction that keeps the framework from feeling useful.

The fix is a publication bridge: emit a per-defect annotation record
that maps `claim_id -> source_span -> severity -> message`, plus a
`forge render` command that overlays the annotations onto the source
markdown as colorised HTML. The author edits the manuscript, runs
`make ci`, opens `work/<manuscript>-annotated.html`, and sees the
defects highlighted in context. The loop closes.

## What

- Both verifiers' `verdict_to_qa.py` emit
  `work/manuscript-annotations.json` with a versioned schema linking
  claim ids to source spans and severity-tagged messages.
- A new `skills/neurosym-forge/scripts/render_annotations.py` takes
  the annotations JSON plus the source markdown and produces
  annotated HTML with `<mark class="severity-...">` spans.
- `forge render <manuscript.md> --annotations <annotations.json>`
  exposes the renderer at the CLI surface; `make render` from a
  verifier project wires it.
- A `defect-index.html` summary lists every defect with clickable
  jumps to the in-context position.
- Stale spans (manuscript edited after verification) emit warnings
  and skip rather than crash.

## Capabilities touched

- `publication-bridge` — NEW (adds REQ-PUB-040..046)

## Implementation notes

See `docs/plans/2026-05-19-tier5-scale-author.md`, Phase T.

## Acceptance

- 7 REQ-PUB IDs ship in `specs/publication-bridge/spec.md`.
- A round-trip fixture (small manuscript → ingest → verify →
  annotate → render) produces HTML whose `<mark>` count equals the
  defect count.
- Stale-span fixture (manuscript edited mid-pipeline) emits the
  expected warning and skips the affected annotation.
- `forge render --help` exposes the command and its flags.
