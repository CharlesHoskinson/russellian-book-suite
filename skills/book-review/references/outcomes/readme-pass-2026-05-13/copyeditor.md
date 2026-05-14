---
persona: copyeditor
chapter_id: readme-v6.1
verdict: NEEDS_WORK
critical_count: 6
important_count: 5
minor_count: 4
reviewed_at: 2026-05-13T03:00:00Z
---

## Critical findings

1. **README pipeline diagram vs README defect-taxonomy section:** Diagram says `book-qa` "hard-gate: D1-D8 == 0"; later section says D9, D10, D11 are critical and hard-gate. The diagram understates the hard-gate.

2. **README vs russellian-style SKILL.md:** README says "twenty-eight principles across six domains"; SKILL.md says "26 principles across 5 domains". Numbers and grouping diverge.

3. **README vs book-qa SKILL.md:** README says the QA gate runs "twelve mechanical checks"; SKILL.md says `lint_artifact.py` covers D1-D8 only (eight). D9-D12 come from book-thesis. README conflates the two.

4. **README vs book-knowledge SKILL.md:** README enumerates a five-state machine including `refuted`; SKILL.md still describes four states (no `refuted`). SKILL.md is stale post-Bundle C.

5. **README vs book-knowledge SKILL.md:** README claims `book-knowledge` "22 scripts"; SKILL.md lists ~20. Tight match needed.

6. **README framing vs Bermuda manifest:** README claims the proof passes a "claim ledger validated against sources"; manifest shows `sources_bibliography: [thesis]` — single synthetic source. Soften or contextualize.

## Important findings
- **Terminology drift:** "release gate" / "post-build gate" / "QA gate" / "defect gate" all used.
- **Hyphenation drift:** "soft-gate" vs "soft-gates", "hard-fail" vs "hard-gate".
- **Capitalization:** "Sentinel-Healer" mixed case across the document.
- **Cadence run, line 30:** Five consecutive short declaratives, word counts 9-15.
- **Parallel-structure violation, lines 275-280:** Six bolded domain headings mix noun-phrase fragments with imperatives.

## Minor findings
- Em-dash overuse: >1 em-dash per paragraph in prose sections.
- "PROV-O" vs "W3C PROV vocabulary" — inconsistent.
- "claim-ledger" (CLAUDE.md) vs "claim ledger" (README).
- Manifest YAML excerpt uses ellipsis where the real file is block-style.

## Notes on voice and cadence
Test arithmetic 59+127+94+19+41+16=356 checks out, but the per-skill counts need re-verification per the Domain Expert finding.
