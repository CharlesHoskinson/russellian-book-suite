# Production-readiness audit — design

**Date:** 2026-05-16
**Branch:** `audit/2026-05-16-production-readiness`
**Driver:** Charles Hoskinson

## Goal

Verify the eight skills, the Bermuda end-to-end example, the documentation, and the supply chain meet a "production-ready" bar — installable on a clean machine, deterministic offline tests, no AI-attribution leakage, no broken cross-skill interfaces, no hardcoded secrets.

## Scope

In scope:
- The eight skill packages under `skills/`.
- The Bermuda manual workspace under `examples/bermuda-manual/`.
- `README.md`, `AGENTS.md`, `CLAUDE.md`, the Quickstart, the cross-skill claims.
- `tools/` Python scripts at repo root.
- Supply chain: `pyproject.toml` deps, secret scan.

Out of scope:
- Rewriting any skill's core algorithm.
- Improving the prose of the Bermuda manual.
- Network-dependent integration tests.

## Audit dimensions

Six orthogonal dimensions. Each gets a dedicated test agent so findings don't bleed across.

| # | Dimension | Pass criterion |
|---|---|---|
| A | Package metadata + installability | Every skill has `pyproject.toml`; `pip install -e .[dev]` succeeds on Python 3.11 Windows in a clean venv. |
| B | Per-skill pytest | Every skill's `pytest tests/ -q` exits 0 with no flaky tests. |
| C | Cross-skill interface contracts | Every `invokes:` / `imports` claim in one skill resolves to an actual public surface in the sibling skill. |
| D | Quickstart reproduction | The README Quickstart commands, run verbatim on the clone, produce the artefacts they promise. |
| E | Documentation truth | README claims (skill counts, file paths, command names, the eight-skill table) match the repo. |
| F | Security + supply chain | No hardcoded secrets, no surprising network egress in tests, deps free of known-bad pins. |

## Test-agent fleet

Six agents run in parallel; each returns a punchlist of findings classified `must-fix`, `nice-to-have`, or `note`.

```
                  ┌──────────────────────────────┐
                  │  audit driver (this session) │
                  └────┬─────────┬────────────┬──┘
                       │         │            │
        ┌──────────────┼─────────┼────────────┼──────────────┐
        ▼              ▼         ▼            ▼              ▼
   ┌─────────┐    ┌─────────┐ ┌─────────┐ ┌─────────┐  ┌──────────┐
   │ Agent A │    │ Agent B │ │ Agent C │ │ Agent D │  │ Agent E  │
   │  pkg    │    │ pytest  │ │ x-skill │ │ quickst │  │ doc-truth│
   └─────────┘    └─────────┘ └─────────┘ └─────────┘  └──────────┘
                                              ┌──────────┐
                                              │ Agent F  │
                                              │ security │
                                              └──────────┘
```

Agents A and F are static-only (read the tree, run greps, parse `pyproject.toml` / `SKILL.md`). Agents B, D run shell commands and may install. Agents C and E read code + docs and cross-check.

## Already-known finding

Pre-audit grep found one defect that the agents will confirm but I'm naming up front:
- **`skills/book-qa/pyproject.toml` is missing.** The README Quickstart's `pip install -e .[dev]` cannot install `book-qa`, so the post-build defect gate is uninstallable through the documented path.

## Triage and remediation

After the six punchlists land, I aggregate them and classify:
- **must-fix:** blocks installation, breaks the Quickstart, fails an advertised invariant (e.g., "no network egress at runtime"), or exposes a secret. Fixed on this branch.
- **nice-to-have:** stylistic, missing docstring, README polish. Captured in the PR description as follow-up but not fixed.
- **note:** observation worth recording but not actionable (e.g., "Python 3.13 not yet exercised by CI").

## Deliverables

1. This design doc, committed.
2. An audit report at `docs/specs/2026-05-16-production-readiness-audit-findings.md` listing every finding and its classification.
3. Fix commits on `audit/2026-05-16-production-readiness`.
4. A PR with the audit report as the body.

## Non-goals

- I will not modify any of the released Bermuda content under `examples/bermuda-manual/`.
- I will not bump version numbers or cut a release tag.
- I will not introduce CI workflows unless the audit finds CI broken.
