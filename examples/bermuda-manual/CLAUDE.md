# Bermuda Manual Workspace

This is a book-knowledge workspace for the bermuda-manual non-fiction book.

## Project name

bermuda-manual

## Style

inherit: russellian-style

## Notes for Claude

- All sources live in `raw/`. Never edit raw files.
- All synthesis lives in `wiki/`. Append, don't rewrite.
- Claims promotion requires `verify_claim.py` to confirm source-span existence.
- Graph audit must pass before any chapter compiles.
- The book's intent substrate lives in `thesis/bermuda-manual.yaml` (book-thesis owns it).
- The book's fact substrate (claim ledger) was synthesized from the thesis on 2026-05-12 as part of Bundle C rollout; see commit history for details.
