# Halmos QA review

Verdict: GREEN

Disposition: the two important findings (code-3, tests-2) are fixed with regression tests on branch `halmos-qa-fix`. Re-verify gate green — halmos suite 14 passed, book-compose gate 3 passed, deterministic book re-run 0 broken seams, ch-13 agent path halmos_critical_count 0. Two findings refuted on verification (listed at the end). The 20 minor findings below are accepted as accurate but not auto-fixed; they remain open for triage.

## important

### build_linkage reads draft.md and _load_concepts parses JSONL with no error handling — crashes the conductor  `[code]`
- Location: C:/russellian-book-suite/skills/halmos/scripts/build_linkage.py:51 and :40
- Problem: build_linkage reads the target draft with no existence check, and _load_concepts calls json.loads on every line with no try/except. A missing draft.md or a single malformed line in concepts.jsonl raises an uncaught exception that propagates through run_halmos and aborts the whole review.
- Evidence: Line 51: body = (workspace / "chapters" / "drafts" / chapter_id / "draft.md").read_text(encoding="utf-8")  (no is_file guard -> FileNotFoundError). Line 40: return [json.loads(l) for l in ...] (a bad line -> JSONDecodeError, confirmed). The same unguarded json.loads pattern recurs in dispatch_halmos_review.py:31 (_concepts_by_chapter). run_halmos (conductor.py:18-19) has no try/except, so the failure crashes the gate rather than degrading.
- Fix: Check is_file() before reading the draft (raise a clear domain error if truly required), and wrap per-line json.loads in try/except to skip/report malformed lines instead of aborting.

### Stale-verdict mtime sentinel (verdict older than draft -> 999) is untested  `[tests]`
- Location: C:/russellian-book-suite/skills/book-compose/tests/test_halmos_gate.py::_draft / test_halmos_metric_absent_is_failing_sentinel
- Problem: The only sentinel path tested is verdict ABSENT. The verdict-PRESENT-but-STALE branch (`verdict.stat().st_mtime < draft_path.stat().st_mtime -> 999` in chapter_contract_check.py line 129) is never exercised. The _draft helper does the opposite: it sleeps 0.01s then writes the verdict, guaranteeing the verdict is always newer than the draft.
- Evidence: _draft: writes draft.md, then `if verdict is not None: time.sleep(0.01); (d/'halmos-verdict.json').write_text(...)`. So verdict mtime >= draft mtime always. _read_halmos_critical has two ways to return 999 (not-a-file, and stale mtime); only not-a-file is covered. A bug that flipped the comparison or dropped the mtime check would still pass both tests.
- Fix: Add a test that writes halmos-verdict.json with halmos_critical_count==0, then re-touches/rewrites draft.md afterward (or os.utime the verdict to an older time), and asserts _compute_metrics returns halmos_critical_count == 999.

## minor

### _chapter_n grabs first digit run anywhere in the id, not the ch-NN index  `[code]`
- Location: C:/russellian-book-suite/skills/halmos/scripts/build_linkage.py:20-22 (and identical copy concept_ledger.py:21-23)
- Problem: _chapter_n returns the first integer found anywhere in the id, so any id richer than 'ch-NN' yields a wrong chapter number.
- Evidence: def _chapter_n(cid: str) -> int:\n    m = re.search(r"(\d+)", cid)\n    return int(m.group(1)) if m else 0  — tested: 'ch-2024-recap' -> 2024, 'chapter-3' -> 3, 'ch-01-intro' -> 1 (only accidentally right). A non-conforming id silently produces a bogus n that drives the entire priors range and prev-chapter lookup.
- Fix: Anchor the pattern to the chapter slot, e.g. re.match(r"ch-?(\d+)", cid), and treat a non-match as an explicit error rather than silently returning 0.

### _slug collapses distinct concepts to identical or empty slugs  `[code]`
- Location: C:/russellian-book-suite/skills/halmos/scripts/concept_ledger.py:17-18
- Problem: _slug strips every non-alphanumeric char to '-', so distinct concepts collide, and punctuation-only concepts produce an empty slug. Slugs are used as the cross-chapter linkage keys (references/introduces lists), so collisions silently merge unrelated concepts.
- Evidence: def _slug(t): return re.sub(r"[^a-z0-9]+", "-", _norm(t)).strip("-")  — tested: _slug('C++') == _slug('C#') == 'c'; _slug('Web 3.0') == _slug('Web 3 0') == 'web-3-0'; _slug('!!!') == ''. Two seed concepts differing only in punctuation get the same slug, and an empty slug is emitted into concepts.jsonl and then matched against in build_linkage.references.
- Fix: Detect and reject/disambiguate empty or duplicate slugs when building the ledger (e.g. append a discriminator or warn), rather than emitting colliding keys.

### harvest_title_case ignores ALL-CAPS, splits hyphenated terms, and mis-handles mid-sentence articles/stop-phrases  `[code]`
- Location: C:/russellian-book-suite/skills/halmos/scripts/concept_ledger.py:6-40
- Problem: The regex requires [A-Z][a-z]+ per word, so ALL-CAPS terms are never harvested and hyphenated terms are split mid-word; the _ARTICLES strip and _STOP filtering are only meaningful for the leading word, so a stop-word phrase or article appearing mid-sentence is harvested verbatim.
- Evidence: TITLE_CASE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b") — tested: 'The AUTHORITY AIRGAP' -> [] (caps lost); 'Self-Sovereign Identity' -> ['Sovereign Identity'] (the hyphen breaks the first token, harvesting a wrong phrase); 'A New Hope and The Empire' -> ['New Hope', 'The Empire'] ('The Empire' kept because the _ARTICLES strip at line 31 only fires when words[0] is an article — a mid-sentence 'The' is index 0 of its own match, so it survives). Footnote-title text picked up the same way. These mis-harvested phrases become first-class concepts with slugs.
- Fix: Allow ALL-CAPS and intra-word hyphens in the token class, and apply article/stop filtering to the whole phrase (not just the first word) before accepting it.

### rollup._key can merge two agent findings that share check+detail but differ in severity/fix  `[code]`
- Location: C:/russellian-book-suite/skills/halmos/scripts/aggregate_halmos.py:7-28
- Problem: _key falls back to detail text when both concept and prior_chapter are absent. Two agent findings with the same check and the same detail string but different severities (or one with no concept/prior set) hash to the same key, so the second is dropped at line 22-24 (it only copies fix and continues), losing its severity and any distinct fields.
- Evidence: _key: return (f.get("check"), f.get("concept") or f.get("prior_chapter") or f.get("detail") or ""). In rollup, when k in merged the branch only does merged[k]["fix"]=f["fix"] then continue (lines 21-24) — the colliding finding's severity is never reconciled, so a 'critical' duplicate of an already-recorded 'important' finding silently keeps 'important' and is not counted separately.
- Fix: Include severity in _key (or, on collision, keep the higher severity) so same-check/same-detail findings of differing severity are not silently merged into the first-seen one.

### _contract_purpose matches the first 'purpose:' anywhere, including nested YAML keys  `[code]`
- Location: C:/russellian-book-suite/skills/halmos/scripts/dispatch_halmos_review.py:18-22
- Problem: The purpose extractor scans line by line with a loose regex that allows arbitrary leading whitespace, so any indented sub-key named 'purpose:' (e.g. under some other block) is matched as the chapter thesis, and a multi-line/quoted YAML value is truncated to its first physical line at 200 chars.
- Evidence: m = re.match(r"\s*purpose:\s*(.*)", line) — the \s* permits any indentation, so it does not distinguish a top-level purpose from a nested one, and block scalars ('purpose: >' / '|') yield an empty or wrong capture rather than the folded value.
- Fix: Parse the contract with a YAML loader and read the top-level purpose key, or at minimum anchor to a non-indented 'purpose:' and handle block scalars.

### introduced_in = earliest-mention artifact is encoded as a premise, not flagged as a limitation  `[doctrine]`
- Location: halmos-doctrine.md, '## Checks and severities', orphan-reference bullet, lines 17-21
- Problem: The doctrine bakes the earliest-mention recording rule into the orphan-reference logic without warning that a chapter which only *previews* a device (ch-1 previews, defines later) gets introduced_in=ch-01. This silently defeats continuity-gap and premature-definition detection: if N relies on a device that was merely name-dropped in ch-1 but defined nowhere, the deterministic record shows it 'introduced' in ch-01, so neither the reviewer nor the layer flags the missing rung.
- Evidence: "the deterministic layer cannot decide it, since any concept that appears in N is recorded as introduced no later than N" and "if N relies on a concept that is in none of the priors' introduced lists and N does not itself define it, flag it." The rule keys off the *introduced list*, which (per the known limitation) marks earliest mention, not first definition. A previewed-but-undefined device is therefore in an introduced list and escapes orphan-reference.
- Fix: Add an explicit caveat: introduced_in marks earliest *mention*, which may be a forward-reference/preview, not a definition. Instruct the reviewer to verify that the chapter recorded as introducing a concept actually *defines* it (not merely teases it) before clearing an orphan-reference, and to raise continuity-gap/orphan-reference when a relied-on concept was only previewed.

### Footnote-title harvest noise is never addressed; orphan-reference can fire on or be masked by garbage concepts  `[doctrine]`
- Location: halmos-doctrine.md, '## Checks and severities', orphan-reference bullet (lines 17-21) and intro 'concepts it introduced with glosses' (lines 10-11)
- Problem: The doctrine treats the priors' introduced lists as ground truth, but harvesting captures footnote/section titles like 'Safety Gridworlds' or 'Existential Risk' as concepts. Two failures: (1) such noise inflates the introduced lists, so a genuine orphan term that happens to collide with a noise concept gets falsely cleared; (2) the reviewer may waste a critical orphan-reference finding on a noise token that no human would treat as a book device. The doctrine gives no instruction to sanity-check concepts against the curated device set.
- Evidence: Doctrine: "the concepts it introduced with glosses" (line 10-11) and orphan-reference keys entirely on "in none of the priors' introduced lists" (line 20). seed-concepts.txt header: "# Curated book devices. Format: Canonical Term | alias | alias" — a clean curated list exists, but the doctrine never tells the reviewer to prefer it or to discount non-device concepts.
- Fix: Instruct the reviewer to treat the curated device list (seed-concepts) as the authority for what counts as a book 'concept/device,' and to ignore harvested entries that are plainly footnote/section titles rather than load-bearing devices before deciding orphan-reference.

### orphan-reference and continuity-gap overlap with no precedence rule  `[doctrine]`
- Location: halmos-doctrine.md, orphan-reference (lines 17-21) and continuity-gap (lines 25-26)
- Problem: A relied-on-but-unbuilt concept can satisfy both orphan-reference ('leans on a concept as if established' but no chapter introduced it) and continuity-gap ('assumes a step the prior chapters never built'). The checks are not cleanly disjoint and the doctrine gives no rule for which to file, risking double-counting or inconsistent severity (both can be critical).
- Evidence: orphan-reference: "N leans on a concept or term as if established, but no earlier chapter (nor N) introduced it." continuity-gap: "N's argument assumes a step the prior chapters never built — a rung skipped in the cumulative argument." An undefined-but-relied-on device fits both descriptions.
- Fix: Add a one-line precedence note: file orphan-reference when a *named concept/term* is unestablished; file continuity-gap when a *reasoning step* (not a named concept) is unbuilt. Do not file both for the same item.

### missed-recall and spiral-stall are adjacent; boundary unstated  `[doctrine]`
- Location: halmos-doctrine.md, missed-recall (lines 27-28) and spiral-stall (lines 29-30)
- Problem: missed-recall (reuses a concept with no recall cue) and spiral-stall (repeats a concept verbatim without refining) describe neighboring conditions — verbatim repetition with no advancement can read as both a stalled spiral and an absent/degenerate recall. Both are 'important', so the reviewer has no severity tiebreaker and may pick arbitrarily.
- Evidence: missed-recall: "N reuses an earlier concept without any recall cue." spiral-stall: "N merely repeats a prior concept verbatim instead of refining or extending it." Verbatim repetition is simultaneously 'no recall cue' (it does not re-orient the reader) and 'does not advance.'
- Fix: Distinguish explicitly: missed-recall = the concept is used with *no* re-introduction, forcing reconstruction; spiral-stall = the concept *is* re-introduced but only restated, not deepened. Note that the two are mutually exclusive for a given occurrence.

### Gate is never shown to BLOCK on non-zero halmos_critical_count  `[tests]`
- Location: C:/russellian-book-suite/skills/book-compose/tests/test_halmos_gate.py (whole file)
- Problem: No test calls check_draft with an acceptance test such as `halmos_critical_count == 0`, so the suite never proves the gate fails when the count is non-zero. Both tests only call _compute_metrics and read the raw metric value.
- Evidence: The file imports only `_compute_metrics` (line 7). Grep for `check_draft`, `acceptance_tests`, and `halmos_critical_count ==` in the file returns no matches. test_halmos_metric_reads_verdict asserts count==0; test_halmos_metric_absent_is_failing_sentinel asserts count==999. Neither feeds metrics through check_draft/_evaluate_test, so a regression that, e.g., dropped halmos_critical_count from the contract evaluation or mis-evaluated `==` would not be caught here.
- Fix: Add a test that builds metrics with a non-zero halmos_critical_count and runs check_draft(draft, {"acceptance_tests": ["halmos_critical_count == 0"]}), asserting result.passes is False and the test string is in failed_tests; plus the mirror case (count 0 -> passes True). Optionally also assert 999 fails the same gate.

### Article-stripping assertion is too weak to catch a regression  `[tests]`
- Location: C:/russellian-book-suite/skills/halmos/tests/test_concept_ledger.py::test_harvest_title_case_finds_multiword_devices
- Problem: The test only asserts that 'Authority Airgap' and 'Bounded Polis' are IN the result. It does not assert the un-stripped forms 'The Authority Airgap' / 'The Bounded Polis' are ABSENT, so the leading-article-drop behavior (concept_ledger.py lines 30-32) is not actually pinned.
- Evidence: Input is 'The Authority Airgap... The Bounded Polis...'. Asserts: `'Authority Airgap' in got` and `'Bounded Polis' in got`. If harvest_title_case stopped stripping articles and returned ['The Authority Airgap', 'The Bounded Polis'], these substring/membership assertions would still... actually membership would fail, but a broken impl returning BOTH 'The Authority Airgap' and 'Authority Airgap' would pass. The dedup/slug pipeline would then mis-key the concept.
- Fix: Add `assert 'The Authority Airgap' not in got` and `assert 'The Bounded Polis' not in got`, and assert the result has exactly the two expected entries (len/sorted equality).

### rollup dedup fix-merge branch is untested  `[tests]`
- Location: C:/russellian-book-suite/skills/halmos/tests/test_aggregate_halmos.py::test_rollup_dedupes_and_counts
- Problem: When a deterministic flag and an agent finding collapse to the same key, aggregate_halmos.rollup copies the agent's `fix` onto the merged record (lines 23-25). The dedupe test exercises the collapse and the count, but the agent duplicate has no `fix` field, so the fix-promotion branch is never verified.
- Evidence: test_rollup_dedupes_and_counts agent dup: `{"check": "orphan-reference", ..., "detail": "dup"}` with no `fix`. The test asserts halmos_critical_count==1 but never inspects merged['findings'][i]['fix'], so the `if f.get('fix'): merged[k]['fix'] = f['fix']` line is dead in tests. A regression dropping that line would not be caught.
- Fix: Give the agent's duplicate finding a `fix` string and assert the merged deterministic finding now carries that fix text.

### seam_status 'unknown' (empty side) and rollup target-collapse cases untested  `[tests]`
- Location: C:/russellian-book-suite/skills/halmos/tests/test_build_linkage.py / test_aggregate_halmos.py
- Problem: seam_status returns 'unknown' when prev_close or this_open is empty (build_linkage.py line 30-31); this is the realistic case for chapter 1 with no prior. No test covers it. Likewise rollup's intended COLLAPSE of two identical target-less findings (same check + same detail) is not tested, only the non-collapse case is.
- Evidence: test_seam_status covers only clean and broken. test_rollup_keeps_distinct_targetless_findings covers two findings with DIFFERENT detail (kept distinct). The complementary case (same check, same detail, no concept/prior -> should collapse to 1) is absent, so the detail-fallback key could over- or under-collapse without detection.
- Fix: Add seam_status('', 'x') -> ('unknown', []) test and a ch-01 build_linkage test asserting seam status 'unknown' with no broken-seam flag; add a rollup test with two identical-detail target-less findings asserting count collapses to 1.

### Malformed/unreadable halmos-verdict.json -> 999 path untested  `[tests]`
- Location: C:/russellian-book-suite/skills/book-compose/tests/test_halmos_gate.py
- Problem: _read_halmos_critical catches ValueError/OSError on a corrupt verdict and returns 999 (chapter_contract_check.py lines 131-135). No test writes invalid JSON or a verdict missing the key to exercise this fallback.
- Evidence: Both tests write either valid JSON or no file. The `data.get('halmos_critical_count', 999)` default and the except branch are untested.
- Fix: Add a test writing 'not json' (or '{}') to halmos-verdict.json (newer than draft) and assert _compute_metrics yields 999.

### dispatcher=None error path and run_halmos clean-pass not asserted  `[tests]`
- Location: C:/russellian-book-suite/skills/halmos/tests/test_conductor_integration.py
- Problem: dispatch_halmos_review raises ValueError when dispatcher is None (dispatch_halmos_review.py line 64); untested. The integration tests only cover the broken-seam path of run_halmos; the all-clean path (critical_count==0 end to end) is never asserted through the conductor.
- Evidence: test_run_halmos_gates_on_broken_seam uses a stub returning empty findings but a broken seam, asserting count==1. There is no run_halmos case producing count==0, and no pytest.raises for the missing-dispatcher contract.
- Fix: Add pytest.raises(ValueError) for dispatcher=None, and a run_halmos test with a clean seam + empty agent findings asserting halmos_critical_count==0 and reviews_complete True.

### Plan still describes the eliminated deterministic forward-reference flag  `[fidelity]`
- Location: plan lines 7, 319, 387, 483, 699-705, 935
- Problem: Defect 2 fixed in code but plan still instructs building a deterministic forward-reference flag.
- Evidence: Plan 7 two flags; Task3 319/387/483 and Task8 935 say forward-reference; Task6 699-705 keys on it. Shipped emits only broken-seam; doctrine 18 gives it to agent; test keys orphan-reference.
- Fix: Edit plan so broken-seam is the only deterministic flag, orphan/forward agent-owned.

### Spec promises claim-ledger concepts that never ship  `[fidelity]`
- Location: spec 47-57 vs concept_ledger.py 102
- Problem: Spec says claim-ledger source but the ledger only emits device.
- Evidence: Spec 48/50-53 require claim-ledger harvest; ledger uses seed+Title-Case only and hardcodes device at 102. Plan 1067 deferred; README 21 still overstates.
- Fix: Mark deferred in spec, or note device-only for v0.1.

### README claims 10 tests; suite has 11  `[fidelity]`
- Location: README.md 31
- Problem: README says 10 tests but tests has 11.
- Evidence: 11 functions: aggregate 3, build_linkage 3, concept_ledger 3, conductor 2; extra beyond plan 10 (881).
- Fix: Drop the count or update to 11.

### halmos gate lacks a reviews-complete metric unlike persona gate  `[fidelity]`
- Location: chapter_contract_check.py 125-135, 186 vs 92-93, 121
- Problem: Persona gate exposes a boolean; halmos exposes only an int 999 sentinel.
- Evidence: _read_halmos_critical returns int, absent/stale=999. ==0 safe, but less-than-1000 passes on never-run; verdict reviews_complete (55) unsurfaced.
- Fix: Surface halmos_reviews_complete; ==0 default already safe.

### Rule-of-three cadence in docs  `[fidelity]`
- Location: SKILL.md, README 4, spec 20
- Problem: Two AI-slop triples recur in every doc.
- Evidence: Recall/reuse/build and linkage/seams/coherence triples in SKILL, README 4, spec 20.
- Fix: Flatten one triple per doc.

## Refuted (raised, dismissed on verification)

- **prev_id underflows to 'ch--1' when n==0, and assumes 2-digit zero padding** `[code]` — Read C:/russellian-book-suite/skills/halmos/scripts/build_linkage.py:48-74 and traced both claims. (1) The 'ch--1' underflow is real as a string but harmless. prev_id is only used to build prev_file (line 66); when n==0 the resulting 'ch--1' directory does not exist, so prev_file.is_file() is False (line 68), prev_close stays "" and seam_status returns "unknown" with no broken-seam flag and no crash (lines 30-31, 71-74). n==0 occurs only for an undigited/malformed chapter_id, which has no defined predecessor, so "unknown" is the correct graceful outcome, not a defect. For a genuine first chapter ch-01, prev_id is 'ch-00' which likewise does not exist and correctly yields "unknown" — there is no predecessor to check. The reviewer's framing that the seam is "silently reported unknown instead of being checked" mischaracterizes correct behavior as a bug. (2) The ':02d padding mismatch for ch-9-style naming' is purely hypothetical: every chapter id across the codebase — tests (ch-01, ch-06, ch-07, ch-09), README (ch-09), and the doctrine reference (ch-01) — uses uniform two-digit zero-padded ids, so f"ch-{n-1:02d}" exactly reproduces the on-disk directory names. No single-digit ch-9 scheme exists, so there is no real mismatch and prev_file is found whenever a true predecessor exists. No crash, no wrong predecessor match, no incorrect flag is produced in any real scenario. The claimed "important" severity is unjustified; at most this is a cosmetic robustness nit on an internal string that never surfaces.
- **Seam-overlap stoplist failure modes unguarded: no caution against a false-clean seam of pure filler** `[doctrine]` — The finding misreads the sentence at lines 23-24: "Use the seam in the linkage record (status `broken` is a strong signal) plus your own reading of the two paragraphs." The own-reading instruction is NOT gated behind the `broken` branch — "(status `broken` is a strong signal)" is a parenthetical aside, while "plus your own reading of the two paragraphs" is attached to the whole check and applies unconditionally, regardless of seam status. So the reviewer is already told to read both paragraphs whether the seam is clean or broken. The claimed asymmetry ("only the broken branch gets an own-reading instruction") does not exist in the text.

The "rubber-stamp clean seams" failure mode is also contradicted by the surrounding doctrine: line 13 states the reviewer receives the linkage record but "Confirm or extend those flags; you own the judgments below," and line 8 says "you own this." The seam status is explicitly framed as one input, not a verdict — the reviewer owns the broken-handoff judgment. A false-clean seam from a too-narrow stoplist is therefore already backstopped by the mandatory own-reading, so the asserted "silent false-clean seam suppresses a real broken-handoff" cannot occur as described.

The complaint that "how overlap is computed is never defined" is correct on its face but is appropriate scoping, not a defect: this file is a reviewer brief (line 1), and the deterministic overlap/stoplist computation belongs to a separate deterministic layer that produces the linkage record. A reviewer brief need not specify the algorithm of the upstream layer; it tells the reviewer to use the record as a signal plus independent reading, which it does.

The suggested fix (make the own-reading explicitly symmetric and discount filler overlap) is a marginal wording polish, but the substantive defect claimed — gated own-reading and rubber-stamped clean seams enabling a suppressed broken-handoff — is refuted by the actual text and its unconditional own-reading plus reviewer-owns-the-judgment framing.
