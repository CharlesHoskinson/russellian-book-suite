# Smoke Test — 2026-05-09

## Automated verification (passes)

- 42/42 pytest tests pass: 10 lint_common + 4 hedges + 4 passive + 4 signal + 3 parallel + 4 report + 4 trigger + 3 integration + 6 compliance.
- Skill is discoverable in Claude Code: confirmed in session-start skill registry as `russellian-style` with the description loaded from SKILL.md.
- All five reference files present in `references/`: russellian-style-guide.md (99 lines), how-i-write-maxims.md (36 lines), logical-atomism-for-writers.md (54 lines), before-after-examples.md (77 lines), negative-triggers.md (28 lines).
- All five scripts present in `scripts/`: lint_hedges.py, lint_passive_voice.py, lint_signal_density.py, lint_parallel_structure.py, style_pass_report.py.
- Frontmatter passes Anthropic compliance: kebab-case name, ≤1024-char description, no XML brackets, no reserved words, includes positive trigger phrases and negative-trigger language.
- spaCy `en_core_web_sm` 3.8.0 loads and POS-tags as expected.

## Live-session triggering tests (pending user validation)

These tests require a fresh Claude Code session because the running session has the skill discoverable but cannot reliably test trigger behavior from inside the same conversation.

| Test | Prompt | Expected behavior | Status |
|---|---|---|---|
| Positive 1 | "Apply Russell style to this passage: The script might fail under heavy load." | Skill activates; emits rewritten prose + style-pass-report | PENDING |
| Positive 2 | "Atomize this paragraph: [nested-conditional sentence]" | Skill activates; produces IF/AND IF/THEN refactor | PENDING |
| Negative 1 | "Write a launch announcement for our new database engine." | Skill does NOT activate | PENDING |
| Negative 2 | "Compose a casual Slack update about the deployment." | Skill does NOT activate | PENDING |
| Refusal | "Apply Russell style to this fiction passage." | Skill activates then refuses per negative-triggers reference | PENDING |

## Latency baseline (from automated suite)

- Full pytest suite: 1.94s wall-clock on Windows 11 with spaCy en_core_web_sm cached.
- Single-file linter run: ~0.05s (regex-only) to ~0.4s (spaCy parse) per file.
- Style-pass-report generation: ~0.5s end-to-end on a 200-line markdown file.

## Issues found

- One implementation detail worth noting: spaCy's POS tagger occasionally mis-classifies sentence-initial imperatives as compound nouns (specifically "Load configuration."). The parallel-structure linter compensates by prepending "Please " to the input before re-tagging, which reliably nudges spaCy to read the verb as imperative. Documented in scripts/lint_parallel_structure.py.

## Next steps

1. Run the five live-session tests above in a fresh Claude Code window.
2. Update this document with PASS/FAIL for each.
3. If any positive trigger fails to activate, expand the description's keyword list. If any negative trigger over-triggers, harden the negative phrasing.
