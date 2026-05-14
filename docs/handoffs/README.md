# docs/handoffs/

Cross-session work orders. Each handoff is a pair of files:

- `<date>-<topic>-brief.md` — the comprehensive work order. Lives in git as the contract between sessions.
- `<date>-<topic>-prompt.md` — the pasteable text the operator drops into a fresh Claude session to kick off the work.

A handoff is the right tool when work needs to span sessions and the context of one session is not portable to the next. The brief replaces that context by stating the mission, sources, deliverables, and acceptance criteria explicitly.

Briefs persist in git after the work is done. They are useful as templates for similar future handoffs.

## How to use a handoff

1. Open a fresh Claude Code session in this repo.
2. Paste the contents of the `*-prompt.md` file as your opening message.
3. The session reads the corresponding `*-brief.md` and proceeds.

## Adding a new handoff

Two files at this directory: the brief and the prompt. The prompt points at the brief by path; the brief is self-contained — anything the next session needs to know about scope, sources, deliverables, and style must be in the brief.
