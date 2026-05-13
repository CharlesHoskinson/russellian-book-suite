# Bundle C Runbook — Phase 4 operational steps

Bundle C's code is shipped on `spec/bundle-c-closed-loop-ledger`. Phases 1–3 plus Task 4.1 and Task 4.6 are merged-ready code. Phase 4's remaining tasks (4.2, 4.3, 4.4, 4.5) are *operational* — they run against a real workspace and require operator judgment. This runbook walks through them.

Run order: 4.1 → 4.2 → 4.3 → 4.4 → 4.5. Each step assumes a working `.venv` exists in `skills/book-knowledge/` per the skill's existing convention.

---

## 4.1 — Tag load-bearing claims

```
cd <repo-root>
python tools/tag_load_bearing.py examples/bermuda-manual
```

Output: `tagged N claims as load_bearing`. The tool marks any claim referenced by 2 or more chapter contracts via `supports_chapters` as load-bearing. Idempotent — re-running is a no-op.

**Note on Bundle C contract integration.** The chapter contracts under `examples/bermuda-manual/chapters/contracts/ch-NN.yaml` predate Bundle C. They do not have a `claims:` field listing the cited claim IDs. `load_brief()` only emits `must_address` entries for claims that appear in the contract's `claims:` list. To make Bundle C must-address active for an existing chapter, edit its contract YAML and add:

```yaml
claims:
  - clm-2026-000142
  - clm-2026-000167
  # ... all load-bearing claims cited in this chapter
```

The `claims` field is optional and was added in Phase 2 (commit `f880e0d`).

---

## 4.2 — Generate counter-claims

Bundle C's `generate_counter_claims.generate_for_all_load_bearing(workspace, llm_call)` walks every claim tagged `load_bearing` and dispatches a counter-claim prompt to the LLM. The `llm_call: Callable[[str], str]` parameter is what you wire to your LLM of choice.

**For the bermuda example:** a ready-made adapter exists at `tools/run_bermuda_counter_claim_gen.py`. It has hard-coded rivals for the 3 load-bearing bermuda claims. Run:

```
python tools/run_bermuda_counter_claim_gen.py
```

**For any other book:** there is no general-purpose CLI adapter yet. Write one that:
1. Reads `<workspace>/claims/ledger.jsonl`
2. Filters to claims with `load_bearing: true` and no `counter_claim_ids`
3. For each, dispatches an LLM call (your preferred mechanism) with `generate_counter_claims.PROMPT_TEMPLATE.format(claim_text=claim["canonical_text"])`
4. Calls `generate_counter_claims.generate_for_claim(workspace, claim_id, llm_call=lambda p: response)` to write the records

The `tools/run_bermuda_counter_claim_gen.py` script is a worked example of this pattern.

After running, the workspace should contain:
- `claims/counter-claims.jsonl` with 2–3 records per load-bearing claim
- Updated ledger records with `counter_claim_ids: [...]`

Spot-check:
```
wc -l examples/bermuda-manual/claims/counter-claims.jsonl
```

---

## 4.3 — Run belief propagation + inspect histogram

```
cd skills/book-knowledge
.venv\Scripts\python.exe -m scripts.propagate_belief <repo-root>/examples/bermuda-manual
```

Output artifacts:
- `examples/bermuda-manual/claims/snapshots/<utc-iso>.jsonl` — pre-propagation ledger snapshot
- `examples/bermuda-manual/graph/reports/belief-propagation-<run-id>.md` — top-20 deltas plus histogram
- Appended ledger records carrying `p_posterior`

**Reading the report.** Open the markdown. Look for:
- **Top-20 deltas** — are any claims dropping below 0.4 unexpectedly?
- **Histogram** — is the distribution clustering at the floor 0.05 or ceil 0.95?

If the distribution is degenerate (clustered at extremes), tune the damping factors in `skills/book-knowledge/scripts/propagate_belief.py`:
- `COUNTER_OPEN_DAMP` (current 0.95) — raise toward 0.97 if open counter-claims drop load-bearing claims too far.
- `COUNTER_ADDRESSED_DAMP` (current 0.85) — lower toward 0.80 if addressed counter-claims do not damp enough.

Commit any tuning with a `tune:` prefix and a one-liner explaining the chosen values.

---

## 4.4 — Rebuild Bermuda v6 with Bundle C wired in

```
cd skills/book-knowledge
.venv\Scripts\python.exe -m scripts.build_book <workspace> v6 "Life in Bermuda" bermuda-manual
```

What to verify:

1. **Must-address coverage.** Each chapter brief used during draft should include `must_address` entries for open counter-claims of cited load-bearing claims. The chapter-draft pipeline logs these. Check `examples/bermuda-manual/reports/V6.md` (or the equivalent build report).

2. **Writeback proposals.** After QA stage:
   ```
   ls examples/bermuda-manual/claims/proposed-transitions.jsonl
   ls examples/bermuda-manual/qa/ledger-writeback-v6.md
   ```

3. **Refuted-claim exclusion.** Any claim that previously transitioned to `refuted` should not appear in the v6 chapter slices unless its contract pins it via `force_include_refuted`.

Commit any updated reports:
```
git add examples/bermuda-manual/reports/V6.md \
        examples/bermuda-manual/qa/ledger-writeback-v6.md \
        examples/bermuda-manual/qa/swarm-findings.md
git commit -m "Bermuda v6 build with Bundle C enabled"
```

---

## 4.5 — Promote defeasible queries to hard-gate

Once the v6 build is clean (no false-positive defeasible fires; rebuttal-presence and posterior-floor fire only on legitimate gaps), flip the runtime flag in `skills/book-knowledge/scripts/run_competency_queries.py`:

```python
BLOCKING_DEFEASIBLE = True
```

Severity `critical` defeasible fires (currently `rebuttal-presence` and `posterior-floor`) then escalate from warnings to a `RuntimeError` that halts the QA pipeline. Severity `important` fires (currently `contested-rebuttal-window`) remain warnings.

Re-run QA after the flip and confirm no critical defeasible fires on a clean book. Commit:

```
git commit -am "Promote defeasible queries to hard-gate (BLOCKING_DEFEASIBLE=True)"
```

---

## Pre-flight checklist

Before starting 4.2 (the LLM-cost step), confirm:

- [ ] `tools/tag_load_bearing.py` has run; bermuda ledger has load-bearing-tagged records.
- [ ] At least one bermuda chapter contract has a `claims:` field populated, so the wiring is exercised.
- [ ] You have decided which LLM endpoint will service the counter-claim prompts and have a cost estimate (~2–3 prompts per load-bearing claim; the bermuda book typically has 20–40 load-bearing claims by the 2-chapter threshold).

## Acceptance criteria recap

Spec items 1–5 hold from Phase 3 onward (covered by integration test in `tests/test_bundle_c_integration.py`).

Spec items 6–8 only become evaluable after Phase 4 promotion. Re-run the integration test plus a `python -m scripts.run_competency_queries examples/bermuda-manual` after each Phase 4 step to confirm.
