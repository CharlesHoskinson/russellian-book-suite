#!/usr/bin/env bash
# scripts/ruleset-apply.sh — idempotent ruleset + merge queue setup.
# Requires: gh CLI authenticated as a user with `admin` on the repo.
set -euo pipefail

REPO="${REPO:-CharlesHoskinson/russellian-book-suite}"

echo "==> Applying ruleset on $REPO …"

cat > /tmp/ruleset.json <<EOF
{
  "name": "ci-cleanup-main-protection",
  "target": "branch",
  "source_type": "Repository",
  "source": "$REPO",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["~DEFAULT_BRANCH"],
      "exclude": []
    }
  },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          { "context": "lint" },
          { "context": "scaffold-bake" },
          { "context": "regression (sprint-5)" },
          { "context": "verifier (bermuda)" },
          { "context": "verifier (osmotic-pressure)" },
          { "context": "ci required ✓" }
        ]
      }
    },
    {
      "type": "merge_queue",
      "parameters": {
        "check_response_timeout_minutes": 30,
        "grouping_strategy": "ALLGREEN",
        "max_entries_to_build": 5,
        "max_entries_to_merge": 5,
        "max_entries_to_merge_wait_minutes": 5,
        "merge_method": "SQUASH",
        "min_entries_to_merge": 1,
        "min_entries_to_merge_wait_minutes": 5
      }
    }
  ],
  "bypass_actors": [
    {
      "actor_id": $(gh api user --jq .id),
      "actor_type": "RepositoryRole",
      "bypass_mode": "pull_request"
    }
  ]
}
EOF

gh api -X POST "repos/$REPO/rulesets" --input /tmp/ruleset.json | \
  jq '{id, name, enforcement, target}'

echo "==> Ruleset applied. Confirm at https://github.com/$REPO/settings/rules"
