---
persona: ai-slop-detector
chapter_id: readme-v6.1
verdict: NEEDS_WORK
critical_count: 3
important_count: 5
minor_count: 4
reviewed_at: 2026-05-13T03:00:00Z
---

## Critical findings

1. **[Line 30, "Sentences cluster around eighteen words. Paragraphs deliver three points each."]:** Listicle abstract describing the very pattern. Three terse declaratives in series — itself rule-of-three. Fold into one sentence.

2. **[Line 32, "Source ingest extracts ... Drafting reads ... Russellian linters enforce ... Five editorial personas read ... A deterministic post-build gate runs ..."]:** Five parallel subject-verb openers — listicle-as-paragraph. Break the rhythm; subordinate two.

3. **[Line 34, "append-only ledgers, immutable raw sources, SHACL-validated RDF graph, version-tagged chapter releases"]:** Four-item adjective-noun listicle. Same shape four times. Replace with prose.

## Important findings
- **[Line 269, "Bertrand Russell wrote prose that survived a hundred years"]:** Promotional framing. Cut or qualify.
- **[Lines 275-280, six numbered domains]:** Rule-of-three saturation in the discipline section.
- **[Line 90, "by construction"]:** Appears 3x — tic.
- **[Lines 103, 231, 342, 437]:** Aphoristic one-liner pattern recurs four times. Twice is style; four times is fingerprint.
- **[Multiple lines]:** Em-dash count > 1 per paragraph in prose sections.

## Minor findings
- **[Line 297, "intent substrate / fact substrate"]:** Italicised coinage drift toward jargon.
- **[Line 437, "Bundle C closes the loop."]:** Short declarative-as-section-thesis pattern, used 4+ times.
- No "navigate", "delve", "tapestry", "harness", "unlock" — vocabulary is clean.
- "comprehensive" appears once inside a quote — allowed.

## Score
AI-fingerprint score: **moderate**. The README is technically dense and concrete, but its paragraph-openers default to terse-declarative triads and parallel subject-verb chains — the exact cadence the suite claims to lint against.
