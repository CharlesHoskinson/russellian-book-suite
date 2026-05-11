# v4.3 Prose Furniture — Bermuda Manual

Run date: 2026-05-11

## What changed

Three additions to the book's editorial furniture:

1. **Polished glossary blockquotes.** The ~40 existing `> **Term.** Definition.` sidebars now render with a warm-ochre rule, faint cream fill, small-caps term label, and `break-inside: avoid` so they never split across pages.
2. **Footnotes.** 100 footnote references across all 10 chapters, each anchored to a verified-claim aside or technical clarification. Per-chapter numbering (1..N restart per chapter), backlinks on every note. Endnotes are placed in a `<section class="footnotes">` at the end of each chapter with `border-top: 0.5pt solid` and reduced font size in print.
3. **For Further Reading.** A 14-item annotated bibliography organised by theme (Foundational histories, Primary voices, Governance/economy/finance, Race/politics/modern society, Reference and archives), placed after the Sources section. Each item carries a one- or two-sentence annotation telling the reader why it earns the citation.

## Research outcome

Two parallel research agents surveyed Claude skills, libraries, and editorial conventions. Key findings:

- **No dedicated Claude skill exists** for editorial blockquote/sidenote/footnote treatment in any catalogue (Anthropic-official, awesome-claude-skills, posit-dev, JimLiu/baoyu).
- Tufte CSS is the only mature reference pattern; its `<label>+<input>+<span>` sidenote toggle does not survive markdown → marked.js → Playwright PDF, so we adopt the visual idea (margin notes, epigraphs, pull quotes) but reshape via CSS only.
- **marked.js footnotes**: no native support. Three viable paths: (a) `marked-footnote` plugin CDN, (b) inline 30-line custom extension, (c) Python post-processor that converts GFM `[^name]` syntax to raw HTML before embedding in the script tag. We picked (c) — local-only, no JS-bundle change, full control over per-chapter numbering and class names.

## Implementation

- **Footnote post-processor** (`C:\tmp\process_footnotes.py`): walks chapter by chapter (split on `# Chapter N:` headings), collects `[^name]` references in order of appearance per chapter, assigns 1..N numbering, replaces inline refs with `<sup class="footnote-ref" id="fnref-chNN-name"><a href="#fn-chNN-name">N</a></sup>`, and converts the trailing `## Notes` block to a `<section class="footnotes">…<ol>…</ol></section>` block with backlinks.
- **Prose-furniture CSS block** (`C:\tmp\v4_3_css.html`): 200 lines covering glossary blockquote polish, `.pullquote` class, `.epigraph` class, `.aside` class, footnote ref + endnote styling, all with `@media print` tweaks.
- **Further Reading content** (`C:\tmp\further_reading.md`): authored directly; 14 items in 5 thematic groups.

## Output

`C:\bermuda-manual\book\releases\3.0.0\`

| Artifact | Size |
|---|---:|
| manuscript.pdf | 1.41 MB |
| manuscript.html | 821 KB |
| manuscript.md | 246 KB |

PDF: **80 pages**, 100 footnote refs, 4 hero tables + 9 themed reference tables, 12 figures, 14-item Further Reading bibliography.

## Cumulative progression

| Cut | Pages | What got added |
|---|---:|---|
| v2.0.0 | 53 | Russell-style prose with no visuals or tables |
| v3.0.0 (fast-path) | 72 | 12 figures, 13 markdown tables, scenes, sidebars, front + back matter |
| v4.1 (visuals) | 73 | Mermaid diagrams, real-geometry maps, publication-themed charts |
| v4.2 (tables) | 76 | 4 great_tables hero tables, CSS-themed markdown tables |
| **v4.3 (prose furniture)** | **80** | **Polished blockquotes, 100 footnotes, Further Reading bibliography** |

## Footnote count by chapter

| Chapter | Footnotes |
|---|---:|
| ch-01 Introduction & Geography | 6 |
| ch-02 History | 6 |
| ch-03 Government & Legal System | 6 |
| ch-04 Economy | 5 |
| ch-05 Demographics & Society | 6 |
| ch-06 Daily Life & Cost of Living | 5 |
| ch-07 Housing & Immigration | 6 |
| ch-08 Education | 6 |
| ch-09 Healthcare | 6 |
| ch-10 Transportation, Recreation, Tourism | 6 |
| **Total inserted** | **58** |
| **Total refs inlined (incl. multi-references)** | **100** |

## Files of record

- Footnote post-processor: `C:\tmp\process_footnotes.py`
- Prose-furniture CSS: `C:\tmp\v4_3_css.html`
- Further Reading content: `C:\tmp\further_reading.md`
- Finalizer: `C:\tmp\finalize_v4_3.py`

## Carry-over

- Pull quotes and epigraphs have CSS support (classes `pullquote` and `epigraph`) but the authors did not yet place them in chapters. A v4.4 pass could add 1 epigraph at each chapter open (10 epigraphs) and ~6 pull quotes across the book where the prose has a sentence that earns one.
- The full v4 skill stack (`book-craft` skill packaging linters, persona, manifest) remains scoped in `~/.claude/skills/book-compose/docs/superpowers/plans/2026-05-10-book-craft-v4-and-bermuda-regen.md` for a future cut.
