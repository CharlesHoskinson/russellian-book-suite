---
persona: first-time-visitor
chapter_id: readme-v6.1
verdict: NEEDS_WORK
critical_count: 2
important_count: 4
minor_count: 2
reviewed_at: 2026-05-13T03:00:00Z
---

## First-impression timeline

- **0-15s:** Scanned title and opening paragraph. Picked up "six-skill pipeline," "non-fiction books," "claim ledger," "Russellian linter," "five personas," "no paid APIs." Brain stalls on "claim ledger" and "Russellian" — unexplained jargon in line one.
- **15-30s:** Kept reading, barely. Second paragraph mentions the Bermuda manual as proof (78 pages, 10 chapters, 36,762 words) — that lands. ToC has 11 sections; intimidating but signals depth.
- **30-90s:** "What this is" finally explains the why: LLM prose has a fingerprint, this enforces five disciplines. That is the hook — but it is at line 30, not line 1. The skill table at line 94 is the clearest artifact. The pipeline ASCII diagram is genuinely useful.

## Critical findings

1. **First paragraph fails the gate.** It describes the machine before saying what it does for me. A reader who does not already know what a "claim ledger" or "SHACL" is bounces here. The Bermuda proof — the strongest concrete hook — is sentence three, half-buried.

2. **No one-sentence "for whom."** By line 50 I cannot tell whether this is for solo non-fiction authors, research teams, AI-pipeline builders, or hobbyists. The README addresses none by name.

## Important findings

- Lead is buried: "LLMs write recognisably bad prose; this pipeline forces facts and style discipline" is the actual hook and it is at line 30.
- Jargon density: PROV-O, SHACL, Datalog, Bayesian propagation, abductive counter-claims all appear before any output example.
- No sample of the prose the pipeline produces — only counts and manifests. A two-paragraph before-and-after excerpt would close the sale.
- Quickstart is 30+ lines of cp/venv/python invocations with no "you'll see this when it works" payoff.

## Minor findings

- "Bundle C" is named four times before being explained.
- Acknowledgements section is longer than the value proposition.

## One-sentence project summary

After reading, this README is about: a local, six-skill Claude Code pipeline that drafts non-fiction books from a fact-checked claim ledger and lints the prose against Bertrand Russell's style rules so the output does not read like LLM slop.
