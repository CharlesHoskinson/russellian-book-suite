# book-compose — Lessons learned across releases

Living record of patterns that bit us, so future Charles or future Claude don't redo them.
Add new entries with a date and the release that surfaced the pattern.

## 2026-05-11 — defects from v3 → v4.3

### Orphan citation tokens (recurring)

`[clm-NNNN-NNNNNN]` tokens routinely bleed from chapter drafts into the rendered manuscript and from there into the PDF where they are visible as nonsense. The strip regex must catch both bracketed and bare forms, AND must run on:

1. each chapter draft after agent revisions land,
2. the assembled `manuscript.md` after `build_book`,
3. the merged `manuscript.html` after the React-app payload swap.

Skipping any one of the three lets the next rebuild re-introduce them.

### "Claim ledger:" citation noise

Agents asked to add footnotes will, given the chance, write footnote bodies like "Claim ledger: clm-2026-NNNNNN (status: verified)". This is pipeline jargon, not editorial content. The fix is to constrain the prompt: "Each footnote 1-3 sentences of substantive content. No internal IDs, no claim-ledger references, no '(status: verified)'."

### Numeric-name vs semantic-name footnotes

If you over-aggressively strip `[^\d+]: ...` lines you will also remove perfectly substantive footnotes whose authors used numeric names. The strip pattern should be `[^\d+]: clm-` (anchored to the bad body), not the broader `[^\d+]:`. We lost six chapters' footnotes in ch-05, ch-08, ch-10 once.

### HTML block break (CommonMark blank-line rule)

A closing `</section>`, `</div>`, or `</aside>` MUST be followed by a blank line before any markdown block can resume. Without the blank line, `# Chapter N:` appearing immediately after is consumed as part of the HTML block and renders as literal text. Always emit `</section>\n\n` from any HTML-emitting pipeline step.

### Tailwind preflight overrides heading sizes

The React app's bundled Tailwind preflight CSS contains `h1,h2,h3 { font-size: inherit; font-weight: inherit }` which flattens chapter headings to body-text size. Any heading override CSS must live AFTER the preflight in the cascade — inject as the last `<style>` block before `</head>`.

### Chapter mapping vs chapter content

Agent prompts that hard-code chapter titles drift the moment the contracts change. Always read chapter titles from `<workspace>/chapters/contracts/ch-NN.yaml` at dispatch time. Agents that detect mismatches between their prompt's stated title and the contract file's title should refuse to write to that slot.

### Middle-batch quality dip

Chapters 4-8 in a 10-chapter batch consistently return lower-quality agent output than chapters 1-3 and 9-10. This is "context rot" — accuracy drops more than 30% in the middle of long contexts. Mitigations: (a) one fresh-context agent per chapter, (b) randomised dispatch order to break correlation with position, (c) keep per-agent prompts ≤500 words.

## Prompt patterns that work

- "Return ONLY a JSON object on a single line, no prose around it." Stops agents from monologuing.
- "Be a stern auditor, not a cheerleader." Defeats rubber-stamping.
- "Include line numbers in every ticket." Forces specificity.
- "If the chapter is clean for ALL checks, return `{tickets: []}`." Permits a true zero.

## Prompt patterns that fail

- "Add 4-6 footnotes." Agents will over-deliver to 12+ if they have content to dump. Cap at "exactly 4-6, no more, no less, and reject any that just cite claim IDs."
- "Use semantic names." Without an explicit ban on numeric names, agents will still default to `[^1]`, `[^2]`.
- "Each chapter should grow to ~2000 words." Agents will overshoot (2300-2400) systematically. Specify "between 1900 and 2100" if you want the band.

## Useful one-liners

```bash
# Strip orphan clm tokens from a tree of drafts
find chapters/drafts -name 'draft.md' -exec sed -i -E 's/\s*\[?clm-[0-9]{4}-[0-9]{6}\]?//g' {} +

# Find missing blank lines after HTML close
grep -E '</section>$' manuscript.md | head

# Quick word count per chapter
awk '/^# Chapter/{name=$0; n=0; next} {n+=NF} END{print name, n}' manuscript.md
```

## When something breaks again

1. Check this file first.
2. If the pattern is here, the fix path is here.
3. If not, run `book-qa` first — Stage-1 will name the defect class.
4. After you fix it, ADD AN ENTRY HERE with the date and the symptom.
