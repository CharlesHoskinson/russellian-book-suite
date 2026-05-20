# Gemini 3.5 Flash prompt — russellian-book-suite CI fix

This prompt is designed for **Gemini 3.5 Flash** (Google I/O 2026 release, agentic Flash model with 1M context, 65k max output, default `thinking_level: medium`). It follows Google's published prompting guidance: context first, instruction last; direct and concise; no `temperature` / `top_p` / `top_k`; system instructions for budget/determinism; structured output for the deliverable.

---

## How to send this

1. Open Google AI Studio (or Antigravity) and pick `gemini-3.5-flash`.
2. **Do not** set `temperature`, `top_p`, or `top_k`. Leave them at model defaults.
3. Set `thinking_level: medium` (default). Bump to `high` only if the model returns a first draft that misses a failure class.
4. In the **system instruction** field, paste the system instruction block below.
5. As **part 1** of the user message, attach the comprehension context: `docs/ci-fix-context.md`. (If pasting inline, paste the entire file verbatim — do not summarise.)
6. As **part 2** of the user message, also attach the contents of these files (verbatim, in this order). The model has 1M context — fit them all in one turn:
   - `.github/workflows/ci.yml`
   - `.github/actions/setup-book-python/action.yml`
   - `skills/neurosym-forge/scripts/_provenance.py`
   - `skills/neurosym-forge/scripts/_agm_revision.py`
   - `skills/neurosym-forge/scripts/_induction_proposer.py`
   - `skills/neurosym-forge/scripts/_induction_orchestrator.py`
   - `skills/neurosym-forge/tests/test_agm_revision.py`
   - `skills/neurosym-forge/tests/test_failure_modes.py`
   - `skills/neurosym-forge/tests/test_seed_template_annotations.py`
   - `skills/neurosym-forge/assets/project-template/rules/booklogic/induced-theory.prov.edn.tmpl`
   - `verifiers/bermuda/rust-verifier/src/smt.rs`
   - `Makefile`
7. As **part 3** of the user message, paste the task block below verbatim. Keep it at the end — Gemini 3 docs explicitly recommend "place your specific instructions or questions at the end of the prompt, after the data context."

If you prefer one upload, bundle everything into a single archive and attach.

---

## System instruction (paste into the system field)

```
You are a senior CI / Python / Rust engineer working on the russellian-book-suite
repository. You produce small, reviewable PR-sized patches; you never refactor
beyond what the task requires; you do not invent function names, file paths, or
APIs that are not present in the supplied source. You have a limited action
budget — produce the deliverable in one turn and stop. Do not ask for
clarification. If a piece of information is missing, state the missing
information explicitly in your output and continue with the most defensible
assumption.

You must not:
- Add AI attribution to commit messages or code comments.
- Use --no-verify, --no-gpg-sign, or otherwise skip git hooks.
- Add @pytest.mark.skip to make a red test green.
- Introduce new third-party dependencies unless the task names them as required.
- Loosen the :prov/* closed schema or the 5-fold held-out validation contract.

You must:
- Treat the supplied ci-fix-context.md as ground truth for repository conventions.
- Quote exact file paths and line numbers when proposing patches.
- Emit unified diffs that apply cleanly with `git apply --3way`.
- Keep commit messages terse (one line), in lowercase imperative mood.
```

---

## User message — task block (place this LAST, after all attached files)

```
Based on the information above, return a complete fix plan plus patches for
the russellian-book-suite CI pipeline. The pipeline currently has 22 failing
pytest tests and one nix-preflight job stuck on rustfmt drift, all of which
were merged onto main via admin-bypass during the Tier 6 release sequence.
Goal: make every job green AND substantially faster.

Deliver your answer in this exact JSON shape so a downstream agent can apply
it without further parsing:

{
  "summary": "<one paragraph: what is broken, what you are about to fix, expected wall-time delta>",
  "fix_plan": [
    {
      "pr_title": "<terse, lowercase imperative, no AI attribution>",
      "pr_branch": "<kebab-case>",
      "failure_class": "A_agm_prov_schema | B_missing_imports | C_seed_template | D_rustfmt | E_ci_speedup",
      "rationale": "<why this approach, why not the alternatives>",
      "patches": [
        {
          "file": "<absolute repo path>",
          "intent": "<one sentence>",
          "unified_diff": "<git-apply-compatible diff, ---/+++ headers included>"
        }
      ],
      "test_plan": [
        "<exact command 1>",
        "<exact command 2>"
      ],
      "risk_notes": "<things a reviewer should check>"
    }
  ],
  "speed_plan": {
    "total_wall_minutes_before": "<integer, from §2 of the context doc>",
    "total_wall_minutes_target": "<integer>",
    "ordered_levers": [
      {
        "lever": "<one of: pip wheel cache, pytest tb-short, paths-filter, nix store cache, split preflight, pytest-xdist, slow-mark gating>",
        "expected_delta_seconds": "<integer>",
        "implementation_diff": "<unified diff>"
      }
    ]
  },
  "open_questions": [
    "<list any information you needed but the context did not provide>"
  ]
}

Constraints when producing patches:

1. For Class A, prefer a from_partial helper in _provenance.py that
   default-fills the 5 missing required keys with [], {}, 0, or the empty
   string as appropriate, then have the test helper call it. Do NOT relax
   _REQUIRED_KEYS, _validate_prov_dict, or any production validator.

2. For Class B, first grep the supplied _induction_proposer.py and
   _induction_orchestrator.py for symbols that look like rename candidates
   (e.g. propose_with_repair, holdout_validate, validate_documents). If a
   rename-fit exists, prefer adding a public alias over inventing a new
   implementation. If no fit exists, write the minimum viable function that
   makes the test exercise the documented contract — and say so explicitly
   in the rationale.

3. For Class C, the seed template needs (a) a commented-out example map
   entry whose comment line contains `(def...` or `{...}`, and (b) a
   "common silent failures" block whose first line literally contains
   that phrase (case-insensitive). Look at the seven existing templates
   alongside it for the canonical voice and copy that style.

4. For Class D, run rustfmt mentally over verifiers/bermuda/rust-verifier/src/smt.rs:409
   and :446 and emit the canonical-formatted diff.

5. For the speed_plan, use only levers listed in §5 of the context doc.
   Do not propose self-hosted runners, cross-compilation, or other
   infrastructure changes. The current Python 3.13 + GitHub-hosted matrix
   constraint stands.

6. Cite the specific REQ-IDs from the context doc whenever your patch
   touches code governed by one (REQ-PROV-040..047 for prov schema,
   REQ-REVISE-040..046 for AGM revision, REQ-CI-040..044 for CI shape).

7. If you propose to delete or restructure a test, justify in risk_notes
   why that test was wrong, not why your change is right.

Use thinking_level: medium. Anchor every claim in supplied source. Where you
make an assumption, prefix it with `ASSUMPTION:` so a human reviewer can
audit it. Place your structured output between fenced code blocks tagged
```json so a downstream parser can extract it directly.
```

---

## Notes for the human running this

- **Why this prompt structure.** Gemini 3 docs explicitly recommend "context first, question last" with anchoring phrases like "Based on the information above." The task block uses that exact wording. The system instruction enforces an action budget (Google's own example) and rules out the most likely failure modes (skipping tests, adding deps, loosening contracts).
- **Why structured output.** The model has been benchmarked at 83.6 % on MCP Atlas (tool-use) and 76.2 % on Terminal-Bench 2.1 (agentic coding); both lean on structured output. Asking for a JSON envelope makes the deliverable mechanically applicable.
- **Why include the test files verbatim.** Class B requires the model to grep the production scripts for rename candidates; without the actual source it would hallucinate function names. The 1M context window absorbs the bundle without issue.
- **What to do with the output.** Apply each PR's diffs to a fresh branch with `git apply --3way`, run the listed test_plan, push, open a PR. The 4 bug PRs are independent and can land in parallel; the 3 speed-up PRs are also independent but should follow once main is green.
- **If the first response is incomplete.** Don't lengthen the prompt — bump `thinking_level` to `high` and re-send the same prompt. Google's guidance: change reasoning level, not prompt verbosity.

---

## Quick reference: which file fixes which failure

| Failure class | Test file | Production file to patch |
|---|---|---|
| A — AGM revision (15 tests) | `tests/test_agm_revision.py` | `scripts/_provenance.py` (add `from_partial`) |
| B — Missing imports (2 tests) | `tests/test_failure_modes.py` | `scripts/_induction_proposer.py`, `scripts/_induction_orchestrator.py` |
| C — Seed template (3 tests) | `tests/test_seed_template_annotations.py` | `assets/project-template/rules/booklogic/induced-theory.prov.edn.tmpl` |
| D — Rustfmt (1 job) | n/a (preflight `make lint`) | `verifiers/bermuda/rust-verifier/src/smt.rs` |

All four classes are independent. There is no shared code path.
