# Cross-phase lessons

last-updated: 2026-05-15

## Recent entries

- 2026-05-15 (Phase 0.5) — Always invoke pytest from the skill dir (`cd skills/$s && .venv/Scripts/python.exe -m pytest tests/`), never from repo root. Why: many tests in `book-knowledge` use cwd-relative fixture paths (e.g. `tests/fixtures/...`) that silently miss from the repo root, producing phantom failures (11 fakes in the PR-33 baseline). How to apply: every baseline, every audit, every Phase 8 evidence block. The brief at `docs/handoffs/2026-05-15-codex-deep-review-and-implementation-brief.md` lines 69-74 has the canonical command.
- 2026-05-15 (Phase 0.5) — Junction-linked skill venvs share state with `~/.claude/skills/<name>/.venv`. Installing a tool (ruff, pytest) in one worktree's `.venv` also installs it in every other worktree that junctions the same source. Why: junctions are pointers, not copies. How to apply: when a venv is missing a dep, fix it once from any worktree; don't replicate.
- 2026-05-15 (Phase 0.5) — `skills/book-thesis/.venv` was missing `pyyaml` and `pytest`. Installed via `pip install -e ".[dev]"` from inside the skill dir. Other skill venvs were already complete. How to apply: when a skill's tests error with `ModuleNotFoundError` on collection, run the editable install before assuming a real regression.
- 2026-05-15 - Phase 0 seeded the working wiki. No implementation lessons recorded yet.
