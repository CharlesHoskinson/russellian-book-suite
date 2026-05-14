# russellian-style Vitality Layer — Design

Design doc. 2026-05-14. Target: `russellian-style` v0.2.x, with consumer-side changes in `book-compose`.

## Problem

The current `russellian-style` skill is defensive-only. Its six linters (hedges, passive voice, signal density, parallel structure, sentence rhythm, listicle abstraction) catch the prose patterns that fail; none reward the patterns that succeed. A passage can clear every linter and still read like text — uniform sentence lengths, no concrete actors, no concession, no turn at the paragraph break, no rhetorical move that earns the reader's continued attention.

Two independent inputs name the same diagnosis. The recently-added `docs/research/2026-05-14-russell-style-enhancement.md` puts it directly: *"It can punish bloat, passivity, hedge terms, flat rhythm, and fake structure. It cannot reward a concrete instance, a useful concession, a witty antithesis, or a paragraph that earns its last sentence."* The "AI Prose: From Terseness to Cadence" report (Downloads, 2026-05-14) arrives at the same diagnosis from the algorithmic side: RLHF-induced mode collapse concentrates probability mass on the safest tokens, producing uniform low-burstiness prose. The report gives quantitative targets — AI prose averages 14.38 words/sentence in a tight 12.33-17.64 band; human prose averages 19.28 in a 15.67-25.60 band; <40% of AI prose contains a single compound-complex sentence vs >90% of human prose — and names the rhetorical devices AI prose avoids (tricolon with asymmetric tail, antithesis, hyperbaton).

The 50-paragraph Russell corpus map at `references/russell-corpus-map.md` (also 2026-05-14) closes the loop. Each entry is keyed by rhetorical mode (popular philosophy, public argument, analytic exposition, definition-by-pressure) and rhetorical move (concession, distinction, antithesis, turn, concrete instance). The corpus is already a retrieval substrate; the linters do not yet consume it.

This spec adds a vitality layer to `russellian-style`: quantitative burstiness measurement, positive-trigger linters keyed to Russell-specific rhetorical moves, an AI-vocabulary banlist sourced from the existing `humanizer` skill, three system-prompt assets keyed to artifact mode, and a corpus-retrieval primitive that pulls a same-mode Russell paragraph as a calibration anchor when a positive-trigger linter fires. `book-compose`'s drafter loads the matching system prompt when it makes an LLM call. No existing linter changes behaviour; the new linters all start advisory.

## Scope

In:

- New scripts in `skills/russellian-style/scripts/`: `lint_burstiness.py`, `lint_ai_vocabulary.py`, `lint_concrete_instance_density.py`, `lint_epistemic_precision.py`, `lint_paragraph_motion.py`, `retrieve_corpus_anchor.py`, `sibling_skills.py`, `system_prompt_loader.py`.
- New assets: three system-prompt files at `skills/russellian-style/assets/system-prompts/`, plus `skills/russellian-style/assets/ai-vocabulary-supplement.json` (Russell-specific overlay).
- New reference: `skills/russellian-style/references/russellian-vitality-guide.md` (positive-style doctrine, six rules).
- Revisions to `skills/russellian-style/scripts/style_pass_report.py` to surface the new metrics and any retrieved corpus anchors.
- One additive change to `skills/book-compose/scripts/sibling_skills.py` to add `load_russellian_style_module` extensions (already present in the helper; no new endpoint) and to the drafting site to call `load_system_prompt(mode)` from `russellian-style`.
- Optional new chapter-contract field `prose_mode` (defaults to `technical-exposition`).

Out:

- Fission/fusion post-processor that programmatically restructures sentence lengths (the PDF's "AI Humanizer" burstiness injector). Deferred — automated sentence restructuring can corrupt meaning and warrants its own brainstorm.
- LoRA-based stylistic transfer per StyleAdaptedLM. Requires base-model access; out of scope for the local-only constraint.
- Sampler-stack documentation (Min-P / XTC / DRY tuning). Lives in `book-compose` if/when its drafter exposes sampler knobs.
- Promotion of new linters from advisory to gating. Per the research doc's calibration plan, that promotion lands in a follow-up spec after the linters correlate with persona findings.
- Changes to existing linters, the existing Russellian style guide, or the existing 26-principle catalog.
- Any change to `book-knowledge`, `book-qa`, `book-thesis`, `book-review`, `review-conductor`.

## Architecture

```
                       chapter draft (markdown)
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
  ┌──────────┐         ┌─────────────────┐       ┌─────────────────┐
  │ existing │         │ NEW vitality    │       │ NEW corpus      │
  │ 6        │         │ linters (5):    │       │ retrieval:      │
  │ negative │         │  burstiness,    │       │  retrieve_      │
  │ linters  │         │  ai_vocab,      │       │  corpus_anchor  │
  │          │         │  concrete_inst, │       │                 │
  │  (gating │         │  epistemic,     │       │  reads          │
  │  unchang.│         │  paragraph_     │       │  assets/        │
  │  )       │         │  motion         │       │  russell-corpus/│
  └────┬─────┘         │  (advisory)     │       │  index.json     │
       │               └────────┬────────┘       └────────┬────────┘
       │                        │                         │
       │   ┌────────────────────┘                         │
       │   │                                              │
       │   │   ┌──────────────────────────────────────────┘
       │   │   │
       ▼   ▼   ▼
  ┌────────────────────────┐
  │  style_pass_report.py  │  emits style-pass-report.md
  │   (modified)           │  with:
  │                        │  - negative metrics (unchanged)
  │                        │  - vitality metrics (new)
  │                        │  - retrieved Russell anchor per
  │                        │    triggered vitality finding
  └──────────┬─────────────┘
             │
             ▼
   chapters/drafts/<chapter>/style-pass-report.md


   ────────── parallel: drafting path ──────────

   chapter contract (with optional prose_mode field)
                │
                ▼
   ┌────────────────────────┐
   │ book-compose           │
   │ persona_review_pass.py │
   │ or drafting site       │
   │                        │
   │ load_system_prompt(    │  ◀── reads
   │   mode=contract.       │       russellian-style/
   │   prose_mode)          │       assets/system-prompts/
   └──────────┬─────────────┘       <mode>.md
              │
              │ system prompt injected into LLM call
              ▼
        drafted section
```

## Components

### New linter: `lint_burstiness.py`

Computes the Fano factor of sentence-length distribution (variance/mean), plus the proportion of sentences falling inside the AI-signature band `[12, 17]` words.

Output schema:

```json
{
  "rule": "burstiness",
  "section": "<heading>",
  "fano_factor": 0.41,
  "mean_words_per_sentence": 14.6,
  "in_band_proportion": 0.83,
  "severity": "advisory"
}
```

Triggers:
- Critical (when promoted): Fano < 0.3 OR in-band proportion > 0.85 across a 20-sentence window.
- Important: Fano in [0.3, 0.5).
- Advisory: Fano in [0.5, 0.7).
- Pass: Fano ≥ 0.7.

PDF-grounded thresholds; humans cluster around Fano 0.6-0.9.

### New linter: `lint_ai_vocabulary.py`

Delegates to `humanizer`'s 24-pattern catalog via the new `sibling_skills.load_humanizer_module` helper. Loads the Russell-specific overlay at `assets/ai-vocabulary-supplement.json`, which adds:

- Sweeping abstractions used as primary subjects without a concrete actor: `the system`, `the framework`, `the landscape`, `the tapestry`. Detection: subject NP whose head noun is in a closed list, with no concrete actor (PERSON/ORG/GPE) in the same sentence.
- False certainty: `clearly`, `obviously`, `of course`, `it is self-evident that`.
- Magic adverbs (PDF list): `quietly`, `deeply`, `profoundly`, `seamlessly`, `intricately`, `fundamentally`.

Output schema: same shape as existing linters, with `pattern` field naming the catalog entry.

### New linter: `lint_concrete_instance_density.py`

Per-paragraph spaCy NER count of PERSON, ORG, GPE, DATE, MONEY, ORDINAL, EVENT. Plus a custom matcher for occupational nouns (`the official`, `the censor`, `the philosopher`, `the worker`) that frequently appear in Russell's prose but are not NER-tagged.

Triggers:
- Important: 3+ consecutive paragraphs in a section with zero concrete instances.
- Advisory: section has fewer than 0.5 concrete instances per paragraph on average.

### New linter: `lint_epistemic_precision.py`

Replaces the existing binary hedge model with a tiered classifier. The existing `lint_hedges.py` is unchanged; `lint_epistemic_precision.py` runs alongside it and may agree or disagree.

Three categories:

1. **Banned vague:** `perhaps`, `arguably`, `to some extent`, `in some sense`, `to a certain extent`, `it could be argued`. Flag as banned regardless of context.

2. **Allowed bounded:** numeric or conditional constraints. Examples: `within 5%`, `under condition Y`, `in cases where the source has been verified`, `for chapters whose contract...`. Allowed by default.

3. **Required uncertainty:** numeric or temporal specificity (`133 tests`, `78 pages`, `2026-05-14`) without a source attribution in the same sentence or the previous one. Flag as missing-attribution.

Severity: advisory in v1.

### New linter: `lint_paragraph_motion.py`

Per-paragraph rubric tagger. Maps each paragraph to one shape using a small rule set over the sentence count, first-sentence shape, and presence of connectives:

- `assertion_only` — single assertion, no justification.
- `assertion_justification` — assertion followed by justification or evidence.
- `concession_turn` — concedes the opposing view, then turns.
- `contrast` — opens with X, ends with not-X.
- `example_inference` — concrete example, then inference.
- `question_answer` — opens with a question, ends with a (partial) answer.
- `definition_by_pressure` — opens with a common term, exposes its instability, narrows.

Triggers:
- Important: >70% of paragraphs in a section are `assertion_only` or `assertion_justification`. This is the "flat axiom stack" — the failure mode named in the research doc.
- Advisory: 0 paragraphs in a section show concession, contrast, or definition-by-pressure.

Output schema includes per-paragraph tag plus section-level shape distribution.

### New script: `retrieve_corpus_anchor.py`

Public function:

```python
def retrieve_anchor(
    rhetorical_mode: str,
    rhetorical_move: Optional[str] = None,
    seed: int = 42,
) -> ExemplarRef:
    """Return one corpus entry matching the requested mode + (optional) move."""
```

Reads `assets/russell-corpus/index.json`. Filters by `mode` (one of: `popular`, `mysticism`, `external-world`, `analysis-mind`, `free-thought`, `political-ideals`) and optionally by `move` (concession, distinction, antithesis, turn, concrete-instance, dry-irony). Deterministic selection via seeded `random.choice`.

`ExemplarRef` dataclass:

```python
@dataclass(frozen=True)
class ExemplarRef:
    corpus_id: str           # e.g. "problems-007"
    source_title: str        # e.g. "The Problems of Philosophy"
    source_url: str          # Project Gutenberg URL
    line_hint: int           # paragraph locator in source
    rhetorical_move: str     # paraphrased move
    calibration_lesson: str  # one-sentence lesson
```

The function does NOT load the full Russell paragraph text; it returns the reference + lesson. Callers retrieve the paragraph from Project Gutenberg out-of-band if they need it (the corpus map's "do not paste full paragraphs into prompts by default" rule).

### New script: `sibling_skills.py`

Mirror of the `sibling_skills` pattern shipped in `book-review`, `book-compose`, and `review-conductor`. Loads `humanizer` (and any future siblings) under an alias namespace to avoid `scripts.*` collisions.

```python
def load_humanizer_module(name: str) -> types.ModuleType: ...
```

The `humanizer` skill is a Claude Code skill (not a Python package in the same shape as the book-* skills); the loader may need to handle that asymmetry. If humanizer ships its catalog as JSON or markdown (not Python), the loader returns the parsed catalog instead of a module. Test: `test_loads_humanizer_catalog`.

### New assets: system prompts

`skills/russellian-style/assets/system-prompts/technical-exposition.md` — for chapters that explain, define, or argue from evidence. Adapted from the PDF's Table 1 "Academic & Technical Reports" row, narrowed to a single artifact (a chapter section) rather than a whole essay. Banned-word registry, sentence-length variance mandate, tricolon-with-asymmetric-tail directive, ban on rhetorical questions used as section openers.

`skills/russellian-style/assets/system-prompts/narrative-editorial.md` — for narrative chapters, book intros, and chapters that build a scene. Adapted from the PDF's "Narrative & Editorial Prose" row. Allows hyperbaton; allows conjunction-starts; bans "magic adverbs" and emotional-summary closers; mandates sentence-length swings.

`skills/russellian-style/assets/system-prompts/polemic.md` — for op-ed-style work, retrospectives, opinionated explanations. Antithesis emphasis; sharper turns; dry irony allowed. New (no direct PDF analogue).

Each prompt file follows a fixed structure: `## Role`, `## Structural mandates`, `## Negative constraints` (banned words inline), `## Rhetorical devices`, `## Closing rules`. Total length per file ≤ 400 words to fit comfortably inside system-prompt token budgets.

### New asset: `ai-vocabulary-supplement.json`

JSON file declaring the Russell-specific overlay patterns beyond humanizer's 24-pattern catalog. Schema:

```json
{
  "patterns": [
    {
      "id": "sweeping_abstraction_subject",
      "description": "Abstract noun used as primary subject without a concrete actor in the sentence.",
      "head_nouns": ["system", "framework", "landscape", "tapestry", "ecosystem"],
      "exemption": "concrete_actor_present"
    },
    {
      "id": "false_certainty",
      "description": "Words that assert obviousness instead of proving it.",
      "phrases": ["clearly", "obviously", "of course", "it is self-evident that"]
    },
    {
      "id": "magic_adverb",
      "description": "Soft adverb performing the descriptive heavy lifting that a precise verb should.",
      "words": ["quietly", "deeply", "profoundly", "seamlessly", "intricately", "fundamentally"]
    }
  ]
}
```

JSON-Schema-validated. Validator function in `lint_ai_vocabulary.py`.

### New reference: `russellian-vitality-guide.md`

Positive doctrine companion to the existing negative-rules `russellian-style-guide.md`. Six rules:

1. Open with a difficulty, not a system noun.
2. Use concrete examples to earn abstractions.
3. Permit exact uncertainty; ban vague hedging.
4. Use antithesis to expose distinction.
5. Vary paragraph motion: common-view → concession → distinction → consequence → turn.
6. Let the last sentence change pressure; the closing line is the paragraph's verdict, not its summary.

Each rule has a one-paragraph rationale + a worked example pulled from the corpus map (cite the `corpus_id`).

### Modified: `style_pass_report.py`

Adds new metric fields to the JSON output:

```json
{
  "negative_metrics": {
    "hedge_count": 0,
    "passive_voice_ratio": 0.0,
    "modifier_budget_violations": 0,
    "parallel_structure_violations": 0,
    "listicle_abstract_count": 0,
    "rhythm_violations": 0
  },
  "vitality_metrics": {
    "burstiness_fano_factor": 0.62,
    "in_band_proportion": 0.41,
    "ai_vocabulary_violations": 0,
    "concrete_instance_density_violations": 0,
    "epistemic_precision_violations": 0,
    "paragraph_motion_score": 0.78,
    "russell_vitality_score": 0.71
  },
  "corpus_anchors": [
    {
      "for_finding": "paragraph_motion:flat_axiom_stack",
      "anchor": {
        "corpus_id": "problems-007",
        "source_title": "The Problems of Philosophy",
        "rhetorical_move": "Practical prejudice personified",
        "calibration_lesson": "Put a mistaken view into a recognizable human figure."
      }
    }
  ]
}
```

`russell_vitality_score` is a composite advisory metric on [0, 1], higher is better. The v1 formula:

```
russell_vitality_score
  = paragraph_motion_score * 0.4
  + min(burstiness_fano_factor / 0.7, 1.0) * 0.3
  + max(0, 1.0 - ai_vocabulary_violations / 10) * 0.3
```

`paragraph_motion_score` is the proportion of paragraphs in the document whose shape is not `assertion_only` or `assertion_justification` — i.e. the proportion using concession, contrast, definition-by-pressure, or question-answer. The Fano-factor weight saturates at 0.7 (the lower edge of the human-prose target band). The AI-vocabulary weight clamps to zero at 10 violations. All three weights and thresholds are placeholders calibrated empirically in the follow-up promotion spec; the score is advisory only.

The Markdown rendering of the report shows the vitality metrics in a separate section below the existing negative metrics. Each triggered vitality finding gets its retrieved corpus anchor printed alongside.

### `book-compose` integration

One addition to `book-compose/scripts/persona_review_pass.py` (or wherever section drafting happens, depending on the current code state — verify before editing):

```python
def load_system_prompt(prose_mode: str = "technical-exposition") -> str:
    rs = load_russellian_style_module("system_prompt_loader")  # NEW small helper
    return rs.load(prose_mode)
```

A new tiny script `russellian-style/scripts/system_prompt_loader.py` exposes `load(mode: str) -> str` that reads the matching prompt file from `assets/system-prompts/<mode>.md`. The chapter contract gains an optional `prose_mode` field validated against the enum `[technical-exposition, narrative-editorial, polemic]` with default `technical-exposition`. The drafting site injects the loaded prompt as the system message in the LLM call.

`book-compose/SKILL.md` Stage 5 description updates to mention the per-chapter system-prompt selection.

## Severity gates

All five new vitality linters start at **advisory** in v1: they surface in `style-pass-report.md` and contribute to `russell_vitality_score`, but do not gate chapter release. The existing six negative linters retain their current gates unchanged.

Promotion plan (deferred to a follow-up spec per the research doc's calibration plan):

1. Run the new suite against three corpus references: the research doc's 20-paragraph sample, one Bermuda chapter (e.g., `ch-04` since middle chapters degrade), and this README's "fingerprint problem" section.
2. Send the same three through `review-conductor`'s panel with Gottlieb, AI-Slop, and Domain Expert gating.
3. Compute correlation between each vitality linter's findings and the persona criticals on the same passage.
4. Promote linters with correlation > 0.7 from advisory to gating in a follow-up PR.

## Composes with

- **`humanizer`** (read-only, delegated to) — `lint_ai_vocabulary.py` imports the catalog via `sibling_skills.load_humanizer_module`.
- **`book-compose`** (caller) — loads the matching system prompt at drafting time via `system_prompt_loader.load(prose_mode)`.
- **`book-review`** (orthogonal) — `AI-Slop Detector` persona already delegates to humanizer separately; the russellian-style linter is a deterministic complement, not a replacement.
- **`review-conductor`** (orthogonal) — same panel pipeline still runs.
- **`book-qa`** (downstream consumer) — release-gate may eventually consume `russell_vitality_score` once calibrated; v1 does not.

## Testing

TDD per repo convention. New test files per new script:

- `tests/test_lint_burstiness.py` — Fano-factor cases, in-band proportion cases, edge cases (single sentence, empty section).
- `tests/test_lint_ai_vocabulary.py` — humanizer-loader test, supplement-overlay test, end-to-end on a synthetic passage with one magic adverb + one sweeping abstraction.
- `tests/test_lint_concrete_instance_density.py` — spaCy-dependent; uses fixtures with known entity counts.
- `tests/test_lint_epistemic_precision.py` — three categories tested; banned-vague, allowed-bounded, required-uncertainty cases.
- `tests/test_lint_paragraph_motion.py` — fixtures for each paragraph shape; flat-axiom-stack detection at the section level.
- `tests/test_retrieve_corpus_anchor.py` — mode filter, move filter, seed-stable selection.
- `tests/test_sibling_skills.py` — humanizer loader behaviour; graceful failure when humanizer absent.
- `tests/test_style_pass_report_vitality.py` — new metrics fields present; corpus anchors attached to triggered findings.

No live LLM in tests. `load_humanizer_module` returns the catalog parse; tests mock by providing a fixture catalog.

Total: roughly 30 new tests, all advisory-side (do not change existing test counts).

## Migration

Single PR. Additive change.

1. Add the new scripts, assets, and reference doc to `russellian-style`.
2. Add tests.
3. Modify `style_pass_report.py` to emit the new fields.
4. Add `system_prompt_loader.py`.
5. Add `book-compose/scripts/persona_review_pass.py` patch (or matching location) and the optional `prose_mode` contract field.
6. Update `book-compose/SKILL.md` Stage 5 description.

No backward-compatibility shims required. Chapters without `prose_mode` use the default; existing chapter contracts continue to validate.

## Invariants

Five contracts the implementation must hold:

1. New linters never modify the markdown they lint. Read-only.
2. New linters never load full Russell paragraph text from the corpus. They return references + lessons only. The "do not paste full paragraphs into prompts by default" rule in `russell-corpus-map.md` is preserved.
3. New linters degrade gracefully when `humanizer` is absent: `lint_ai_vocabulary.py` runs the Russell-specific overlay only, and the report notes the missing humanizer catalog.
4. The system-prompt loader never makes a network call. The prompts are static markdown shipped with the skill.
5. Vitality linters are advisory in v1. No path through `style_pass_report.py` or downstream consumers blocks release on a vitality-only failure.

## Open questions

None as of 2026-05-14. The user has selected the recommended approach (B + corpus-retrieval slice of C), the recommended banlist policy (share with humanizer), and the recommended prompt-asset location (`russellian-style/assets/system-prompts/`, consumed by `book-compose`). The design has no remaining ambiguity that blocks the implementation plan.

## Future work (deferred, with rationale)

- **Fission/fusion post-processor** (PDF §6). Earns its own brainstorm after we measure whether B alone moves the panel verdict. The mechanical-rewrite step risks corrupting meaning; needs a separate safety design.
- **LoRA-based stylistic transfer** (StyleAdaptedLM workflow, arXiv 2507.18294). Requires base-model access and a corpus of target prose at scale; out of scope for the local-only constraint.
- **Sampler-stack documentation** (Min-P / XTC / DRY from PDF §5). Separate concern; lives in `book-compose` if/when its drafter exposes sampler knobs to callers.
- **Linter promotion to gating.** A follow-up spec writes the correlation study + decision rule.
- **Cross-mode prompt blending.** Some chapters legitimately span modes (technical exposition with a narrative open). Defer; v1 picks one mode per chapter.
- **Russell corpus expansion** beyond 50 entries. The 50-entry corpus is enough for v1 retrieval calibration; expansion follows once we see which entries actually surface in reports.

## References

- `docs/research/2026-05-14-russell-style-enhancement.md` — the research doc whose 5-phase plan this design implements. Phase 1 (corpus expansion) is already shipped at `skills/russellian-style/references/russell-corpus-map.md`; this spec covers Phases 2-5 with quantitative grounding the research doc lacked.
- `C:\Users\charl\Downloads\AI Prose_ From Terseness to Cadence.pdf` — quantitative targets for burstiness and the AI-vocabulary banlist; the PDF's Table 1 system-prompt structures are adapted into the three shipped prompt assets.
- `skills/russellian-style/references/russell-corpus-map.md` — 50-paragraph index this spec retrieves from.
- `skills/humanizer/SKILL.md` — the 24-pattern catalog the new `lint_ai_vocabulary.py` delegates to.
- Anthropic, ["Building Effective Agents"](https://www.anthropic.com/research/building-effective-agents) — Parallelization + Evaluator/Optimizer patterns the linter suite composes.
- [Min-p sampling, arXiv 2407.01082](https://arxiv.org/html/2407.01082v8) — referenced in the deferred sampler-stack work.
- [StyleAdaptedLM, arXiv 2507.18294](https://arxiv.org/abs/2507.18294) — referenced in the deferred LoRA work.
- [Verbalized Sampling, arXiv 2510.01171](https://arxiv.org/html/2510.01171v1) — academic reference for mode-collapse mitigation; not implemented in v1.
