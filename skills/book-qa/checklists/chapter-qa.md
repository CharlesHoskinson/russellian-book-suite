# Per-chapter QA checklist (15 items)

You are auditing ONE chapter of a non-fiction book on Bermuda for editorial defects. You see only this chapter plus the project glossary. Your output is a structured JSON ticket list — never prose, never an essay, never opinions.

Run each of these checks. For each, return tickets ONLY for defects you find.

## C1. Heading hierarchy
- The chapter must have exactly one `# Chapter N: Title` (h1).
- Every `### subsection` must be preceded somewhere in the chapter by a `## section` (h2).
- No skipped levels (h1 → h3 without h2).

## C2. Cross-references
- Every `![alt](path)` figure reference must point to a relative path under `assets/shared/` or `chapters/assets/shared/`.
- Every `<sup class="footnote-ref" id="fnref-chNN-X">` has a matching `<li id="fn-chNN-X">` in the chapter's footnote section.
- Every footnote definition has at least one reference.

## C3. Footnote quality
- Footnote text must be SUBSTANTIVE — a technical clarification, a contested-number aside, a source attribution. NOT a bare claim ID.
- Footnote names must be SEMANTIC (e.g., `[^cahow]`, `[^arv-method]`) not numeric (`[^1]`, `[^2]`).
- If you find footnotes whose text is "clm-XXXX-NNNNNN — statement", flag them.

## C4. Citation noise
- The prose must contain no internal claim IDs (`clm-XXXX-NNNNNN` in any form).
- Phrases like "Claim ledger:" or "(status: verified)" must not appear.
- Citations to real sources are fine (e.g., "Bermuda Monetary Authority annual report"); internal-ID leakage is not.

## C5. HTML block hygiene
- Every `</section>` and `</div>` is followed by a blank line before any markdown content.
- No markdown headings (`# `, `## `) inside an HTML block (would render as literal text).
- Hero-table `<div class="hero-table">...</div>` blocks are well-formed.

## C6. Terminology consistency (against project glossary)
- The chapter must use canonical forms: "Bermuda cedar" not "Bermuda juniper"; "Hamilton" (city) distinct from "Hamilton Parish"; "L. F. Wade International Airport" with periods.
- Flag any deviation.

## C7. Scene anchoring
- The chapter must have at least one CONCRETE scene with sensory detail (named place, time of day, named person, sensory verb).
- Flag if the chapter is pure abstract argumentation with no anchor scene.

## C8. Sidebar quality
- Markdown blockquote sidebars (`> **Term.** Definition.`) must:
  - Lead with a bolded term and a period.
  - Define the term in one or two sentences.
  - Not exceed three sentences.

## C9. Table quality
- Markdown tables must have a header row, separator row, and at least one body row.
- Numeric columns must be right-aligned (`---:` in separator).
- Hero tables (HTML `<div class="hero-table">`) must have a `<table>` inside.

## C10. Paragraph length variance
- Within the chapter, paragraph lengths should vary. If every paragraph is within ±10 words of the chapter mean, flag — that's AI-flat prose.
- Also flag any single paragraph longer than 200 words (likely two paragraphs run together).

## C11. Russell-style discipline
- No hedges in declarative sentences ("perhaps", "may", "seems", "around", "roughly" used to dodge a claim).
- Active voice in body prose (passive ok in technical descriptions).
- No em-dashes used as commas (em-dash for parenthetical aside is fine; for "the result — surprisingly — was" is the kind that sounds AI).

## C12. Citation completeness
- Where the prose makes a numeric or surprising claim, a source must be either named in-prose or footnoted.
- Flag claims that read like asserted facts but have no attribution.

## C13. Closing strength
- The chapter must end on substantive prose (not a stub, not a heading, not a sidebar that runs over).
- If the last 30 words are weak ("In conclusion", "Thus we see") flag as weak close.

## C14. Image alt-text quality
- Every `![alt text](path)` must have descriptive alt text — not "image" or "figure" or the file name.

## C15. Print-ready format
- Lines must not exceed 120 chars in the raw markdown (helps git diffs).
- No tab characters; only spaces for indentation.

# OUTPUT FORMAT

Return ONLY a JSON object on a single line (no prose around it). Schema:

```json
{"chapter": "ch-NN", "tickets": [{"check": "C1..C15", "severity": "critical|important|minor", "where": "line N or 'header'", "detail": "one-sentence description"}, ...]}
```

If the chapter is clean for a given check, omit it from the tickets list. If the chapter is clean for ALL checks, return `{"chapter": "ch-NN", "tickets": []}`.

Do not write any text outside the JSON. Do not say "here are the findings" or "I see that". Output only the JSON.
