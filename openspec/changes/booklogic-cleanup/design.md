# Design: booklogic-cleanup

## Architecture pointer

Full architectural detail and TDD-shaped task instructions live in the
implementation-notes plan at:

`docs/plans/2026-05-17-booklogic-cleanup.md`

That file walks each of the 20 tasks with five-step TDD instructions
(failing test → run+FAIL → implement → run+PASS → commit), exact file
paths, full source for each new file, and the exact `Edit` calls for
each modification.

## Why a separate plan file

The TDD plan is verbose by design — it ships as instructions for a Claude
session with zero context. The OpenSpec `tasks.md` in this directory is
the lightweight checklist version; agents executing the change consult
the TDD plan when they need exact source bodies.

## Key decisions locked in the TDD plan

- AGENTS.md doesn't actually contain "two-agent" language; the cleanup
  edit is minimal accordingly.
- Only two `2026-05-15-codex-*.md` handoff files exist (not four).
- The `nl_to_fol` bug is the `:keyword`-schema collision against the
  `~?pred` binding in the meander rule.
- The `shadow-cljs :test` target uses `:node-test` (Node-driven
  `cljs.test`), not browser-driven testing.

## Open questions

None — fully designed.
