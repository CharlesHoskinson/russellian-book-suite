# Codex GPT-5.5 — bootstrap prompt

Paste the prompt below into the Codex CLI to start each session. The first session also runs the worktree-setup commands above the prompt.

---

## One-time setup (run before the first Codex session only)

```powershell
# From C:\Users\charl\code
cd C:\Users\charl\code\russellian-book-suite
git fetch origin
git worktree add C:\Users\charl\code\russellian-book-suite-codex -b codex/phase-0-bootstrap origin/main
cd C:\Users\charl\code\russellian-book-suite-codex
gh auth status                          # verify gh is logged in
node --version                          # expect v22 or v24
npm --version
python --version                        # expect 3.13.x
```

Junction-link the skill venvs from your installed copies if any are missing:

```powershell
# Per skill — repeat for book-knowledge, book-qa, book-compose, neurosym-forge,
# book-thesis, russellian-style, book-review, review-conductor.
cmd /c mklink /J skills\<skill>\.venv C:\Users\charl\.claude\skills\<skill>\.venv
```

If `book-qa` lacks a `pyproject.toml` (intentional), it uses the system Python; no venv needed.

---

## Codex CLI invocation

```powershell
cd C:\Users\charl\code\russellian-book-suite-codex
codex `
  --model gpt-5.5 `
  --sandbox workspace-write `
  --ask-for-approval on-failure `
  --cd C:\Users\charl\code\russellian-book-suite-codex
```

`AGENTS.md` is auto-loaded as the first-turn project doc. `--sandbox workspace-write` lets Codex edit the worktree freely without confirming each write but blocks outbound network (other than `gh` and `npm`). `--ask-for-approval on-failure` keeps Codex autonomous until something errors.

If a later Codex CLI version renames flags (sandbox modes were renamed in 0.124, telemetry options were added in 0.125, `codex remote-control` arrived in 0.130), check `codex --help` and substitute equivalents.

---

## Bootstrap prompt (paste this into Codex)

```
You are Codex, working on the russellian-book-suite repo. Your working directory is
C:/Users/charl/code/russellian-book-suite-codex, a fresh worktree off origin/main.

You are implementing the remaining four PRs of the BookLogic v0.4 mission, with a
mandatory deep audit first. A Claude session will review each PR you open. The user
will merge.

Read these files in order, then begin Phase 0 of the brief:

1. AGENTS.md                                                    (auto-loaded, also re-read for current state)
2. CLAUDE.md
3. docs/specs/2026-05-15-codex-handoff-design.md                (your mission spec)
4. docs/handoffs/2026-05-15-codex-deep-review-and-implementation-brief.md   (your working document)
5. docs/operations/codex-review-protocol.md                     (review protocol for Phase 1)
6. docs/specs/2026-05-14-booklogic-v0.4-mission-design.md       (overall mission)
7. docs/specs/2026-05-14-booklogic-v0.4-pr3-design.md           (most recent shipped phase, for tone)

The brief is your working document. It defines six phases (Phase 0 bootstrap, Phase 1
audit, Phase 2 remediation, Phase 3 PR-3.5, Phase 4 PR-4, Phase 5 PR-5, Phase 6 PR-6).
Each phase ends with a PR. You do not start the next phase until the previous PR is
merged.

You maintain a working wiki at docs/codex-wiki/. Read 00-index.md first, then the
in-progress per-phase file. Update both as you work. The wiki ships in the same PR
as the work it describes.

Hard constraints (the brief covers them in detail):
- One problem per PR. No grab-bags.
- Real QA (pytest, nbb integration, ruff) before opening any PR. Paste evidence in the
  PR body under `### Local QA evidence`.
- Never push to main. Never force-push. Never amend a pushed commit. Never --no-verify.
- No Co-Authored-By lines. No AI attribution anywhere. No AI smells (no `Main theorem:`,
  no `**Proof strategy:**`, no `key insight`, no numbered proof steps, no excessive
  formatting). Terse, human-style commits.
- No outbound network beyond `gh` and `npm install`.
- Apply minimal patches via apply_patch. Don't rewrite a 400-line file to change three
  lines.
- Skill ownership boundaries are sacred. See CLAUDE.md.

You can run any command in the worktree, edit any file in the worktree, push to your
own branches, and open PRs via `gh pr create`. You cannot merge or push to main.

If you get stuck or confused, surface to the user with a top-level PR comment
(@user: <one paragraph>) or, if no PR is open, update docs/codex-wiki/00-index.md with
a BLOCKED section and stop.

Begin Phase 0 of the brief. Confirm the worktree, verify the toolchain, run the
baseline tests, seed the wiki, and open a small bootstrap PR with just the seeded
wiki files. Then stop and let Claude review before starting Phase 1.
```

---

## Resume prompt (paste this for sessions 2 through N)

```
You are Codex, resuming work on the russellian-book-suite v0.4 mission. Worktree:
C:/Users/charl/code/russellian-book-suite-codex.

Re-read:
1. docs/codex-wiki/00-index.md                                            (current-phase pointer)
2. The in-progress per-phase file noted there.
3. The last five entries in docs/codex-wiki/99-lessons.md.
4. docs/handoffs/2026-05-15-codex-deep-review-and-implementation-brief.md (your working document).

Check the state of any open PR with `gh pr list --author @me --state open`. If there
are unresolved review comments on an open PR, address them first.

If the previous phase's PR was merged since your last session, advance to the next
phase per the brief. Update docs/codex-wiki/00-index.md to reflect the new
in-progress phase before beginning work.

All hard constraints from the original bootstrap prompt still apply.

Continue.
```

---

## Per-phase milestone checklist (for the user)

Use this to gate your reviews and merges.

- [ ] Phase 0: bootstrap PR opened with seeded `docs/codex-wiki/`. Claude reviewed.
- [ ] Phase 1: audit PR opened with `01-audit-findings.md`. User reads findings. Go / no-go on Phase 2.
- [ ] Phase 2: remediation PR opened. Every Critical and Important addressed. Claude reviewed. Merged.
- [ ] Phase 3: PR-3.5 opened. Python ingesters gone. Claude reviewed. Merged.
- [ ] Phase 4: PR-4 opened. Four active forms shipping. Claude reviewed. Merged.
- [ ] Phase 5: PR-5 opened. Bermuda on v0.4 vocabulary. Real Z3 invoked. Claude reviewed. Merged.
- [ ] Phase 6: PR-6 opened. osmotic-pressure showcase end-to-end. Claude reviewed. Merged.

After Phase 6 merges, the v0.4 mission is complete. Retrospective in `docs/retros/2026-MM-DD-booklogic-v0.4-retro.md`.

---

## Notes for the user

- **Cost.** Codex GPT-5.5 token usage is reported by `codex exec --json` per session. Expect Phase 1 (audit) to be the most expensive single phase (~broad read pass). Phases 3-6 each consume similar budgets to a typical Claude implementation session.
- **Cadence.** Each phase is a self-contained session. The user can pause arbitrarily between phases; Codex resumes via the resume prompt.
- **Trust calibration.** Treat Phase 0 and Phase 1 PRs as Codex demonstrating it understands the conventions. Once those land cleanly, raise trust for Phases 3-6.
- **Claude as reviewer.** Claude's review style is documented in user memory `feedback_pr_review_style.md` — severity buckets, gate-replay discipline, no nitpicks. Claude mirrors each review at `openspec/changes/<phase>/PR-N-REVIEW.md`.
- **Fallback.** If Codex's output quality is materially worse than Claude's on any phase, the user pauses the handoff and either re-runs that phase with Claude or routes a refresh through a `gpt-5.5-codex` model spec change in `.codex/config.toml`.
