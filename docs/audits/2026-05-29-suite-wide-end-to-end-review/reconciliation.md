# Reconciliation against the 2026-05-21 open recommendations

The eight rank-ordered recommendations in [`../2026-05-21-suite-wide-linter-review.md`](../2026-05-21-suite-wide-linter-review.md) were prose-linter ergonomics work. This review did not close any of them, and all eight remain open. What it changes is their priority: it surfaced correctness defects that sit underneath several of these recommendations and should be sequenced ahead of them.

| # | Recommendation | Status | This review's bearing |
|---|---|---|---|
| 1 | Automatic post-generation prose lint hook | Open | Still the right ergonomics fix. But the `[ci]` extra installs spaCy without `en_core_web_sm`, so the parser-dependent linters silently skip in CI today — a hook that fires them is only as good as that install path. Fix the model install alongside. |
| 2 | `lint_fragment(all=True)` / promote the 7 advisory rules | Open | Unchanged. No new evidence for or against; the coverage-gap argument still holds. |
| 3 | Unify the three ai-vocabulary detectors | Open | Confirmed as live duplication in the architecture findings. Worth doing, but lower severity than the gate and verifier defects. |
| 4 | Give `book-qa` a `skill_api.py` | Open | Reframed. Before exposing the gate through an API, fix what the gate does: the sentinel routes the D9–D13 criticals to the soft gate (critical finding). A `skill_api` over a gate that under-blocks would export the bug. |
| 5 | Prose linting in lefthook pre-commit | Open | Unchanged. |
| 6 | Master `make audit` target | Open | This review is a manual instance of exactly that target. The shard list here (skills + tools + ci + verifiers + CI/CD + security) is a concrete scope for what `make audit` should cover. |
| 7 | Refactor the `scripts.*` namespace collision | Open | Reinforced. The cross-tool import fragility shows up again in the tools/ci and security findings; the sys.modules workaround is still load-bearing. |
| 8 | `docs/skill-triggers.md` trigger index | Open | Unchanged. |

**Net:** none closed, none invalidated. The 2026-05-21 list stays valid as maintainability work; this review inserts a correctness tier ahead of it — the verifier chain, the `book-qa` gate routing, and the branch-protection drift.
