# Branch hygiene runbook

## Current state

As of 2026-06-19, the remote repository has one branch:

- `main`

The cleanup retired 44 non-main branches. Thirty-eight were already reachable
from `main`. Six had commits not reachable from `main`; those tips were
preserved as lightweight archive tags before branch deletion:

- `archive/2026-06-19/codex/phase-1-audit`
- `archive/2026-06-19/docs/ci-fix-gemini-brief`
- `archive/2026-06-19/feat/russell-pass-agentic-civ`
- `archive/2026-06-19/feat/rust-axum-v2-architecture`
- `archive/2026-06-19/plan/tier5-metta-runtime`
- `archive/2026-06-19/update_flake_lock_action`

Restore an archived branch only when work is deliberately resumed:

```bash
git fetch --tags
git switch -c <branch-name> <archive-tag>
git push -u origin <branch-name>
```

## Policy

- Keep `main` as the only long-lived branch.
- Use short-lived PR branches only; delete them after merge or closure.
- Before deleting an unmerged branch, preserve the tip with an
  `archive/YYYY-MM-DD/<branch>` tag or record an explicit decision that the work
  can be discarded.
- Do not keep planning branches open as storage. Plans belong in `docs/`,
  `openspec/changes/`, or issues.
- Run `gh api repos/CharlesHoskinson/russellian-book-suite/branches --paginate --jq '.[].name'`
  during weekly maintenance. The expected output is `main`.
- Keep GitHub's `delete_branch_on_merge` setting enabled. Verify with
  `gh api repos/CharlesHoskinson/russellian-book-suite --jq '.delete_branch_on_merge'`;
  the expected value is `true`.

## Pre-delete checks

```bash
git fetch --prune --tags
git branch -r --merged origin/main
git branch -r --no-merged origin/main
gh api -X GET repos/CharlesHoskinson/russellian-book-suite/pulls -F state=open --paginate --jq '.[].head.ref'
```

Only delete a branch with an open PR after closing the PR or retargeting the
work.
