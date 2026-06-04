# Branch Protection (`main`) — Operational Notes

This repo uses a **GitHub Ruleset** (not legacy branch protection) for `main`. Applied via `scripts/ruleset-apply.sh`.

## What's required

For a PR to merge into `main`:
1. A pull request is open (no direct push)
2. The branch is up to date with `main`
3. At least one approving review, and the last push is approved (`require_last_push_approval`)
4. Every check below is green:
   - `ci-required`

   Required contexts must match `ci.yml` job `name:` values exactly, so when CI jobs are renamed, update both this doc and `scripts/ruleset-apply.sh` in the same change. The `lint` always-run job runs `scripts/check-required-name.sh` to assert this name has not drifted.
5. The PR enters the **merge queue**; the queue re-runs CI on the merged-base before pressing Merge

## Bypass

The repository admin (currently `@CharlesHoskinson`) can bypass via `gh pr merge --admin`. **Every bypass leaves an audit comment on the PR** (`bypass_mode: pull_request`). Use bypass only when:
- A production incident requires a fix faster than the merge queue can land it
- The required checks themselves are broken and the fix can't go through them

After every bypass, add a brief comment on the PR explaining why.

## Disabling temporarily

If the merge queue or required checks ever block emergency work, temporarily disable the ruleset:

```bash
RULESET_ID=$(gh api repos/CharlesHoskinson/russellian-book-suite/rulesets --jq '.[] | select(.name=="ci-cleanup-main-protection") | .id')
gh api -X PUT "repos/CharlesHoskinson/russellian-book-suite/rulesets/$RULESET_ID" \
  -f enforcement=evaluate   # logs but doesn't block
# … do the emergency work …
gh api -X PUT "repos/CharlesHoskinson/russellian-book-suite/rulesets/$RULESET_ID" \
  -f enforcement=active     # re-enable
```

## Re-applying

If the ruleset is ever deleted (or you need to update the required-check list):

```bash
RULESET_ID=$(gh api repos/CharlesHoskinson/russellian-book-suite/rulesets \
  --jq '.[] | select(.name=="ci-cleanup-main-protection") | .id')
[ -n "$RULESET_ID" ] && gh api -X DELETE "repos/CharlesHoskinson/russellian-book-suite/rulesets/$RULESET_ID"
bash scripts/ruleset-apply.sh
```
