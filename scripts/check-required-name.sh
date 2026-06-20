#!/usr/bin/env bash
# scripts/check-required-name.sh — guard against drift between the required
# aggregator job's `name:` in ci.yml and the `context` the ruleset marks as
# required (scripts/ruleset-apply.sh). A mismatch wedges every merge, so we
# assert equality at PR time. The expected name is ASCII `ci-required`.
set -euo pipefail

EXPECTED="ci-required"

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
ci_yml="$repo_root/.github/workflows/ci.yml"
ruleset="$repo_root/scripts/ruleset-apply.sh"

# The aggregator job is the one whose steps run the `aggregate` gate. Its
# `name:` is the required-check context GitHub reports. Pull it out of the
# `required:` job block.
job_name="$(awk '
  /^  required:/ { inblock=1; next }
  inblock && /^    name:/ {
    sub(/^    name:[[:space:]]*/, "")
    print
    exit
  }
' "$ci_yml")"

# The ruleset required context.
ruleset_ctx="$(grep -oE '"context":[[:space:]]*"[^"]*"' "$ruleset" | head -n1 | sed -E 's/.*"context":[[:space:]]*"([^"]*)".*/\1/')"

fail=0
if [ "$job_name" != "$EXPECTED" ]; then
  echo "DRIFT: ci.yml required job name is '$job_name', expected '$EXPECTED'" >&2
  fail=1
fi
if [ "$ruleset_ctx" != "$EXPECTED" ]; then
  echo "DRIFT: ruleset required context is '$ruleset_ctx', expected '$EXPECTED'" >&2
  fail=1
fi
if [ "$fail" -ne 0 ]; then
  exit 1
fi
echo "required-check name OK: ci.yml job and ruleset context both '$EXPECTED'"
