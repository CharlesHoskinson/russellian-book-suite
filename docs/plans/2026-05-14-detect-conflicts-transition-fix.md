# detect_conflicts: transition conflicting claims to disputed

> **For agentic workers:** Small single-file fix. Execute inline with TDD discipline. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `detect_conflicts.py` actually transition conflicting `verified` claims to `disputed`, as the README documents and the five-state machine in `claim_validator.VALID_TRANSITIONS` requires.

**Architecture:** Single-file fix in `skills/book-knowledge/scripts/detect_conflicts.py`. Adds an 8-line block after the `conflicts.jsonl` write that walks the set of claim IDs appearing in any conflict pair and calls the existing `ledger.transition_status(layout, claim_id, "disputed", note="...")` helper. Backed by one new pytest case in `tests/test_detect_conflicts.py` that asserts post-call status is `disputed`.

**Tech Stack:** Python 3.13, pytest. No new dependencies.

---

## Problem statement

The README's state-machine diagram explicitly says:

> `detect_conflicts.py` flips a verified claim to `disputed` when it finds an antonym-pair contradiction; if a later ingest resolves the contradiction, the claim returns to `verified`.

The actual `detect_conflicts.py` does no such thing. It writes to `claims/conflicts.jsonl` and returns. The claim's `status` field in `claims/ledger.jsonl` remains `verified`. Downstream consequences:

- The competency query `contradiction_scan` returns claims by `status == "disputed"`, so it silently reports zero rows on a workspace with real conflicts.
- The Bayesian belief-propagation prior for `disputed` (0.2 in `belief_graph.prior_for_status`) is never applied to a claim flagged by the conflict scan.
- The README's "if a later ingest resolves the contradiction, the claim returns to `verified`" path is unreachable, because no claim ever leaves `verified` in the first place.

The test suite at `tests/test_detect_conflicts.py` covers (1) detection returns conflicts, (2) negative case, (3) `conflicts.jsonl` is written. None assert the status transition — which is why the gap went unnoticed.

Discovered while running an end-to-end ingest of the *Proving Nothing* (sevenlayer) book through the suite; the five surfaced antonym-pair conflicts left all five claims at `status: verified` rather than `disputed`.

---

## Tasks

### Task 1: Failing regression test

**File:** `C:\russellian-book-suite\skills\book-knowledge\tests\test_detect_conflicts.py`

- [ ] **Step 1: Add a new test case at the end of the file**

```python
def test_conflicting_claims_transition_to_disputed(tmp_path):
    """After detect_conflicts, both conflicting claims should be status=disputed,
    per the documented five-state machine and the README's state diagram."""
    from scripts.ledger import latest_status

    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _verified("clm-2026-000001", "Operation X is allowed."))
    append_claim(layout, _verified("clm-2026-000002", "Operation X is forbidden."))

    conflicts = detect_conflicts(layout)
    assert len(conflicts) >= 1

    assert latest_status(layout, "clm-2026-000001") == "disputed"
    assert latest_status(layout, "clm-2026-000002") == "disputed"
```

- [ ] **Step 2: Run the test, verify it fails**

```powershell
Set-Location C:\russellian-book-suite\skills\book-knowledge
.\.venv\Scripts\python.exe -m pytest tests/test_detect_conflicts.py::test_conflicting_claims_transition_to_disputed -v
```

Expected: FAIL with `AssertionError: assert 'verified' == 'disputed'`.

### Task 2: Apply the fix

**File:** `C:\russellian-book-suite\skills\book-knowledge\scripts\detect_conflicts.py`

- [ ] **Step 1: Add `transition_status` to the imports**

Change:
```python
from .ledger import read_claims
```

To:
```python
from .ledger import read_claims, transition_status
```

- [ ] **Step 2: After the existing `conflicts.jsonl` write block, add the status-transition block**

Inside `detect_conflicts`, locate the existing block:

```python
    if conflicts:
        with layout.conflicts.open("a", encoding="utf-8") as fh:
            for c in conflicts:
                fh.write(json.dumps(c, sort_keys=True) + "\n")

    return conflicts
```

Insert the status-transition block before `return conflicts`:

```python
    if conflicts:
        with layout.conflicts.open("a", encoding="utf-8") as fh:
            for c in conflicts:
                fh.write(json.dumps(c, sort_keys=True) + "\n")

        conflicting_ids: set[str] = set()
        for c in conflicts:
            conflicting_ids.update(c["claims"])
        for claim_id in sorted(conflicting_ids):
            transition_status(
                layout, claim_id, "disputed",
                cause_class="detect_conflicts",
                note="Antonym-pair conflict detected with another claim.",
            )

    return conflicts
```

Notes on the chosen `transition_status` arguments:
- `cause_class="detect_conflicts"` lets the events log distinguish these transitions from manual ones (default is `"manual"`).
- `cause_ticket_id` left at default `"manual"` — no ticket system for in-skill detections.
- `operator` left at default `"unknown"` — no operator identity inside the script.
- Iterate over `sorted(conflicting_ids)` so the events-log is deterministic across runs.

### Task 3: Verify the test passes and full suite is green

- [ ] **Step 1: Re-run the new test**

```powershell
Set-Location C:\russellian-book-suite\skills\book-knowledge
.\.venv\Scripts\python.exe -m pytest tests/test_detect_conflicts.py -v
```

Expected: 4 PASS (3 existing + 1 new).

- [ ] **Step 2: Run the full book-knowledge test suite**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: all previously-passing tests still pass; total count is `(previous + 1) passed`. If any pre-existing test now fails, stop — the fix has an unexpected side effect.

### Task 4: Commit on a feature branch

- [ ] **Step 1: Create and check out a feature branch**

```powershell
Set-Location C:\russellian-book-suite
git checkout -b fix/detect-conflicts-transition-disputed
```

- [ ] **Step 2: Stage the two files**

```powershell
git add skills/book-knowledge/scripts/detect_conflicts.py skills/book-knowledge/tests/test_detect_conflicts.py docs/plans/2026-05-14-detect-conflicts-transition-fix.md
```

- [ ] **Step 3: Commit**

```powershell
git commit -m "fix(book-knowledge): detect_conflicts transitions claims to disputed

The README and five-state machine docs say detect_conflicts.py flips
conflicting verified claims to disputed. The script only wrote
conflicts.jsonl and never called transition_status, so claims stayed
verified and the contradiction_scan competency query returned zero rows
on workspaces with real conflicts.

Add the transition_status call after the conflicts.jsonl write, plus a
regression test asserting both conflicting claims are status=disputed
post-call. Discovered while ingesting a 849-claim sevenlayer corpus
end-to-end."
```

No AI attribution. No Co-Authored-By line.

### Task 5: Push and open PR

- [ ] **Step 1: Push the branch to the user's fork (origin)**

```powershell
Set-Location C:\russellian-book-suite
git push -u origin fix/detect-conflicts-transition-disputed
```

- [ ] **Step 2: Open a PR via `gh`**

```powershell
gh pr create --title "fix(book-knowledge): detect_conflicts transitions claims to disputed" --body @"
## Problem

The README documents the five-state machine:

> ``detect_conflicts.py`` flips a verified claim to ``disputed`` when it finds an antonym-pair contradiction

But the script only writes ``claims/conflicts.jsonl`` and never calls ``transition_status``. Consequences:

- ``contradiction_scan`` competency query returns zero rows even when conflicts exist (it filters on ``status == "disputed"``)
- Bayesian propagation never applies the ``disputed`` prior (0.2 in ``belief_graph.prior_for_status``)
- The README's ``disputed → verified`` resolution path is unreachable

Existing tests cover detection, the negative case, and the ``conflicts.jsonl`` write — none assert the status transition. That is the test gap that hid the bug.

Discovered while running an end-to-end ingest of the 849-claim *Proving Nothing* sevenlayer corpus.

## Fix

Two-file change:

- ``skills/book-knowledge/scripts/detect_conflicts.py`` — after writing ``conflicts.jsonl``, walk the union of claim IDs in the detected pairs and call ``transition_status(layout, claim_id, "disputed", cause_class="detect_conflicts", note="...")``.
- ``skills/book-knowledge/tests/test_detect_conflicts.py`` — regression test asserting ``latest_status`` returns ``"disputed"`` for both claims after detection.

Iteration order is ``sorted(conflicting_ids)`` so the events-log is deterministic.

## Test plan

- [x] new regression test fails before the fix, passes after
- [x] full ``book-knowledge`` test suite remains green
- [ ] reviewer confirms the ``cause_class`` value is acceptable (default is ``"manual"``; this PR uses ``"detect_conflicts"``)
"@
```

If `gh` is not available or not authenticated, fall back to printing the branch name + the PR body content and let the human open the PR via the web UI.

---

## Self-review

- **Spec coverage:** README's documented behavior is now implemented; state machine reachability restored.
- **Placeholder scan:** no TBDs.
- **Backwards compatibility:** the new transitions go through `claim_validator.VALID_TRANSITIONS` so any disallowed transition (e.g., from `superseded` or `refuted`) will raise — that's a feature, not a bug, but worth flagging if any downstream caller currently expects `detect_conflicts` to silently accept terminal-state claims.
- **One problem per PR:** yes — single behavior, single fix, single test.
