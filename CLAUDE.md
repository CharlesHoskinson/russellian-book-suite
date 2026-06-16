# russellian-book-suite — conventions for AI collaborators

This file orients any AI agent working in this repo. Read it first.

## What this repo is

A family of nine core Claude Code skills that produces non-fiction books from a local claim-ledger and chapter contracts (`book-knowledge`, `russellian-style`, `feynman-style`, `halmos`, `book-compose`, `book-review`, `review-conductor`, `book-qa`, `book-thesis`), plus an optional verifier-scaffolder skill `neurosym-forge`, a standalone paragraph-threading skill `paragraph-weaver`, a standalone IACR writing aid `iacr-math-prose`, a standalone IACR review aid `iacr-review` (EC22 rubric, ten-persona dispatch, consolidation ledger), a standalone three-pass voice review `triadic-voice`, and the support skills `scrapling-fetch` (the sanctioned HTTP fetch surface) and `syntopical-metabook` (cross-source synthesis). See `README.md` for the architecture diagram and skill table. Source of truth for design decisions: `docs/specs/`; source of truth for operator workflows: `docs/operations/`.

## Per-skill conventions

Each `skills/<name>/` is self-contained: `SKILL.md`, `scripts/`, `tests/`, optional `assets/`, optional `personas/` / `checklists/`. Each skill has its own `.venv` and `pyproject.toml`.

Run tests for a single skill:

```
cd skills/<name>
.venv\Scripts\python.exe -m pytest tests/ -q
```

(Use `.venv/bin/python` on POSIX.)

The cloned repo's skill venvs are junction-linked to the installed-skill venvs under `~/.claude/skills/<name>/.venv` to avoid duplicating gigabytes of dependencies. If a skill is missing a venv, junction it or run `python -m venv .venv && .venv\Scripts\python.exe -m pip install -e .[dev]`.

## Cross-skill conventions

- **One workspace per book** (e.g., `examples/bermuda-manual/`). The workspace contains `raw/`, `wiki/`, `claims/`, `graph/`, `chapters/`, `book/`, `qa/`, `reports/`, `thesis/`. Plus a top-level `CLAUDE.md` (workspace marker).
- **Ledger ownership.** `book-knowledge` is the only writer of `claims/`, `wiki/`, `raw/`, `graph/`. `book-compose` is the only writer of `chapters/` and `book/`. `book-qa` writes `qa/`. Respect these boundaries.
- **Append-only ledgers.** `claims/ledger.jsonl`, `claims/counter-claims.jsonl`, `claims/events.jsonl` are all append-only. Use `read_jsonl` and `latest_per` from `book-knowledge/scripts/io_utils.py` to read them.
- **`WorkspaceLayout` is the canonical workspace-path abstraction.** Use `WorkspaceLayout(root)`. There is no `for_root` classmethod.
- **Cross-skill imports go through `sibling_skills.py`** (in `book-compose` and `book-review`). E.g., `load_book_knowledge_module("io_utils")` imports book-knowledge's `io_utils` under an aliased package namespace to avoid `scripts.*` collisions.

## Commit and PR style

Per the user's `~/.claude/CLAUDE.md`:

- No "Co-Authored-By" lines mentioning Claude or any AI
- No AI attribution in commits, files, or code comments
- No AI smells: no "Main theorem:", "**Proof strategy:**", "key insight", numbered proof steps, excessive formatting
- Terse, human-style commit messages
- One problem per PR

## Test discipline

- Tests are TDD-shaped: failing test → minimal impl → passing test → commit
- No live LLM calls in tests. Pass a callable (`llm_call=fake_llm`) and stub the response
- Append-only fixture tests use `tmp_path` and `init_workspace`
- Integration tests live alongside unit tests; suffix `_integration.py` makes them easy to find

## Schema and data discipline

- All schema changes touch BOTH the JSON Schema in `assets/` AND the validator in `scripts/`
- New optional fields with defaults are backward-compatible; required fields require migration
- The state machine for `tbf:status` is enforced in `claim_validator.VALID_TRANSITIONS`. Five states: `proposed`, `verified`, `disputed`, `superseded`, `refuted`. `superseded` and `refuted` are terminal.
- The SHACL `shapes.ttl` `sh:in` list must match the schema enum exactly. Off-by-one is a silent SHACL failure.

## Documentation contracts

- `SKILL.md` in each skill describes ownership, components, composes-with, and usage. Keep it accurate; broken commands here mislead operators.
- `docs/specs/<date>-<topic>-design.md` is the spec
- `docs/plans/<date>-<topic>.md` is the TDD plan
- `docs/operations/<date>-<topic>-runbook.md` is the operator runbook
- `docs/retros/<date>-<topic>.md` is the retrospective

## Known pitfalls (see `skills/book-compose/MEMORY.md` for full list)

- **Orphan citation tokens leak.** Strip on chapter draft AND assembled manuscript AND merged HTML.
- **HTML block break rule.** Every `</section>`, `</div>`, `</aside>` must be followed by a blank line before any markdown block can resume.
- **Tailwind preflight** resets `h1,h2,h3 { font-size: inherit }`. Heading-override CSS must live AFTER the preflight.
- **Middle-chapter quality dip.** Chapters 4-8 in a 10-chapter batch return lower-quality agent output. Mitigations: one fresh-context agent per chapter, randomised dispatch order, ≤500 words per prompt.
- **`proposed-transitions.jsonl` is overwritten per build.** Consumers (`apply_writeback`) must process it before the next sentinel run, or earlier proposals are silently lost.

## Bundle C specifics

The Bundle C closed-loop ledger landed in May 2026. Key invariants:

- `propagate_belief.run` deduplicates counter-claims to latest-per-id before damping; a promoted counter-claim must not damp twice
- `apply_writeback` is the only mutator of `claims/` outside of `book-knowledge`'s own ingest path; it lives in `book-knowledge` to preserve the ledger-ownership invariant
- `BLOCKING_DEFEASIBLE = True` is the default; severity=critical defeasible fires hard-fail the QA gate

## When in doubt

- Read `README.md` for the big picture
- Read `skills/<name>/SKILL.md` for skill-level conventions
- Read `skills/book-compose/MEMORY.md` for accumulated build lessons
- Read the most recent spec under `docs/specs/` for in-flight design context
