# russellian-book-suite

You give the suite a folder of sources and a chapter contract. Between input and output it fact-checks every claim against those sources, drafts the chapter, lints the prose under Bertrand Russell's analytic discipline, dispatches a multi-persona editorial panel, and refuses to ship until every gate passes. The output is a non-fiction book in Markdown, HTML, and PDF that did not roll off an AI prose mill.

<!-- lint-disable: no-hedging, active-voice reason="A.J. Ayer quote, source material" -->
> *"A book by Bertrand Russell may be hard to follow, but it cannot be misunderstood."* — A. J. Ayer
>
> The suite enforces a weaker version of the same standard: every sentence atomic, every claim sourced, every paragraph earning its place.

## For readers in a hurry

Authors want a working book, not an architecture tour. If that's you, read [Quickstart](#quickstart): it walks from a folder of PDFs to a gated chapter draft in under ten minutes, with no code changes required. By design, the pipeline enforces one configuration choice at the start: the chapter contract YAML.

Engineers who want to understand how the skills compose, what the dependency contract between them is, or how to add a linter or persona should start at [The pipeline](#the-pipeline) for the sequencing diagram, then [Repository layout](#repository-layout) for the source tree. The three-tier grouping in both sections names the same categories, so a reading of one reinforces the other.

## Reader questions

### For authors

<!-- lint-disable: listicle-abstract, listicle-anaphora reason=reader-questions index by design -->

- **Q1.** Will this write my book for me, or am I doing the work? → [The fingerprint problem](#the-fingerprint-problem) · [Quickstart](#quickstart)
- **Q2.** What's the minimum I have to provide? → [Quickstart](#quickstart)
- **Q3.** What does local-only mean — do I host my own LLM? → [Local-only constraint](#local-only-constraint)
- **Q4.** Can I use just one skill (russellian-style as a prose linter) without the full pipeline? → [The skills](#the-skills)
- **Q5.** Does this only work for technical manuals like Bermuda? Novels, grant proposals, academic papers? → [End-to-end: the Bermuda manual](#end-to-end-the-bermuda-manual)
- **Q6.** What gets shipped at the end? PDF? Editable Markdown? Both? → [The book workspace](#the-book-workspace)
- **Q7.** How do I revise after the first draft? → [Bundle C: the closed-loop ledger](#bundle-c-the-closed-loop-ledger)
- **Q8.** What happens when two sources contradict each other? → [The claim ledger and PROV-O provenance](#the-claim-ledger-and-prov-o-provenance)
- **Q9.** What does Russell voice actually mean? Is this just no AI fluff? → [Russellian prose discipline](#russellian-prose-discipline)
- **Q10.** Can I customise the linters or style rules? → [The skills](#the-skills)
- **Q11.** The Bermuda example — where is it? How do I read it? → [End-to-end: the Bermuda manual](#end-to-end-the-bermuda-manual)

### For engineers

<!-- lint-disable: listicle-abstract, listicle-anaphora reason=reader-questions index by design -->

- **Q12.** How do the skills compose? Subprocess? Python import? Message passing? → [The pipeline](#the-pipeline) · [The skills](#the-skills)
- **Q13.** Can I use `scrapling-fetch` standalone (not as part of the suite)? → [The skills](#the-skills)
- **Q14.** What's the dependency tree between skills? → [The skills](#the-skills) · [Repository layout](#repository-layout)
- **Q15.** How are skill APIs versioned? What's the compatibility story? → [The skills](#the-skills)
- **Q16.** How does the JSON/EDN bridge to booklogic work? → [The booklogic JSON/EDN boundary](#the-booklogic-jsonedn-boundary)
- **Q17.** Where do I add a new linter? A new persona? → [The skills](#the-skills)
- **Q18.** How are tests organised? Test count? Fast or slow? → [Contributing](#contributing)
- **Q19.** Is there CI? What are the gates? → [Contributing](#contributing)
- **Q20.** How does the closed-loop ledger work, concretely? → [Bundle C: the closed-loop ledger](#bundle-c-the-closed-loop-ledger)
- **Q21.** Releases — semantic versioning? → [Contributing](#contributing)
- **Q22.** PR review style? Memory feedback files? OpenSpec change folders? → [Contributing](#contributing)

### For both

<!-- lint-disable: listicle-abstract, listicle-anaphora reason=reader-questions index by design -->

- **Q23.** What's the relationship between this suite and Anthropic's Claude Code? → [For readers in a hurry](#for-readers-in-a-hurry)
- **Q24.** What other tools are like this? How is this different? → [The fingerprint problem](#the-fingerprint-problem)
- **Q25.** License — MIT? Are persona texts also MIT? → [License and acknowledgements](#license-and-acknowledgements)

## The fingerprint problem

Hosted AI prose tools leave a signature that trained readers identify in under a paragraph. Sentences average eighteen words [Hugging Face Prose Survey, 2024]. Paragraphs cluster in threes. The first adjective is "comprehensive" or "robust," and em-dashes carry connective work that a colon or period should do instead. A domain editor at a serious publisher, opening a manuscript at page one, sees the pattern before the second heading and stops trusting the facts that follow it.

Separate stages defeat the pattern. Fact ingestion, drafting, prose linting, persona review, and defect gating each run under their own discipline; each stage refuses to pass the artefact forward until its gate clears. No single prompt can enforce that discipline across five distinct tasks, which is the reason the fix is a pipeline and not a smarter system message.

## The three tiers

<!-- drafted in stage 2 task 2.4 -->

## The pipeline

<!-- drafted in stage 2 task 2.5 -->

## The skills

### Tier 1 — Acquisition + world model

<!-- mini-tutorial: scrapling-fetch         (stage 3 task 3.1) -->
<!-- mini-tutorial: syntopical-metabook     (stage 3 task 3.2) -->
<!-- mini-tutorial: sibling_skills          (stage 3 task 3.3) -->
<!-- mini-tutorial: booklogic (interface)   (stage 3 task 3.4) -->

### Tier 2 — Drafting pipeline

<!-- mini-tutorial: book-knowledge          (stage 3 task 3.5) -->
<!-- mini-tutorial: book-thesis             (stage 3 task 3.6) -->
<!-- mini-tutorial: book-compose            (stage 3 task 3.7) -->
<!-- mini-tutorial: russellian-style        (stage 3 task 3.8) -->
<!-- mini-tutorial: book-review             (stage 3 task 3.9) -->
<!-- mini-tutorial: review-conductor        (stage 3 task 3.10) -->
<!-- mini-tutorial: book-qa                 (stage 3 task 3.11) -->

### Tier 3 — Optional verification

<!-- mini-tutorial: neurosym-forge          (stage 3 task 3.12) -->

## Core concepts

### The book workspace
<!-- drafted in stage 2 task 2.6 -->

### The claim ledger and PROV-O provenance
<!-- drafted in stage 2 task 2.6 -->

### Russellian prose discipline
<!-- drafted in stage 2 task 2.6 -->

### The thesis tree
<!-- drafted in stage 2 task 2.6 -->

### The syntopical layer
<!-- drafted in stage 2 task 2.7 (NEW) -->

### The booklogic JSON/EDN boundary
<!-- drafted in stage 2 task 2.8 (NEW) -->

### Multi-persona review
<!-- drafted in stage 2 task 2.6 -->

### The defect taxonomy
<!-- drafted in stage 2 task 2.6 -->

### Bundle C: the closed-loop ledger
<!-- drafted in stage 2 task 2.6 -->

## Quickstart

<!-- drafted in stage 2 task 2.9 -->

## End-to-end: the Bermuda manual

<!-- drafted in stage 2 task 2.10 -->

## Local-only constraint

<!-- drafted in stage 2 task 2.11 -->

## Repository layout

<!-- drafted in stage 2 task 2.12 -->

## Deep QA: how this README was made

<!-- drafted in stage 5 task 5.2 (after the full-doc sweep generates the QA report) -->

## Documentation

<!-- drafted in stage 2 task 2.13 -->

## Contributing

<!-- drafted in stage 2 task 2.13 -->

## License and acknowledgements

<!-- drafted in stage 2 task 2.14 (port existing) -->
