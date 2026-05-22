# russellian-book-suite — suite-wide linter and gate review

Date: 2026-05-21
Reviewer: 4 parallel general-purpose explorer agents, synthesized.
Repository: `C:\russellian-book-suite` at branch `feat/russellian-style-audit`.

## Headline

The suite contains roughly **80+ distinct quality checks** spread across five
skills plus one sibling. The richest linter surfaces are:

- `russellian-style` — 17 prose rules in a single `_LINTER_REGISTRY` (10 default
  gating + 7 advisory)
- `book-qa` — 8 deterministic D-class rules (`lint_artifact.py`) + 4
  thesis-derived D9–D12 + 1 optional D13 + 15 chapter-swarm C-class dimensions = 28
  release-gate checks
- `book-thesis` — 5 distinct check classes (lint_supports, datalog: direct +
  transitive contradiction, declared conflict, unadvanced sub-arg, missing
  evidence)
- `book-knowledge` — 2 SHACL node shapes with embedded SPARQL + 8 competency
  queries (4 coverage, 1 consistency, 3 defeasible)
- `humanizer` (sibling skill, not in this repo) — 24 named patterns loaded
  at runtime via `sibling_skills.py`

`book-compose` is the only skill without its own linters — it composes everyone
else's into a 9-stage pipeline with explicit gates at stages 2, 6, 7, 8, and 9.

## Inventory by skill

### russellian-style (17 rules, `skills/russellian-style/scripts/`)

| Group | Rule | Script | Needs |
| --- | --- | --- | --- |
| Default | `no-hedging` | `lint_hedges.py` | — |
| Default | `active-voice` | `lint_passive_voice.py` | spaCy |
| Default | `signal-density` | `lint_signal_density.py` | spaCy |
| Default | `parallel-structure` | `lint_parallel_structure.py` | spaCy |
| Default | `listicle-abstract` | `lint_listicle_abstract.py` | — |
| Default | `listicle-anaphora` | `lint_listicle_abstract.py` | — |
| Default | `rhythm-uniform-length` | `lint_sentence_rhythm.py` | — |
| Default | `rhythm-repeated-opening` | `lint_sentence_rhythm.py` | — |
| Default | `burstiness` | `lint_burstiness.py` | — |
| Default | `ai-vocabulary` | `lint_ai_vocabulary.py` | optional humanizer sibling |
| **Advisory** | `staccato-paragraph-run` | `lint_ai_staccato.py` | — |
| **Advisory** | `negation-affirmation-template` | `lint_ai_staccato.py` | — |
| **Advisory** | `this-is-conclusion-overuse` | `lint_ai_staccato.py` | — |
| **Advisory** | `abstract-subject-run` | `lint_ai_staccato.py` | spaCy |
| **Advisory** | `concrete-instance-density` | `lint_concrete_instance_density.py` | spaCy |
| **Advisory** | `epistemic-precision` | `lint_epistemic_precision.py` | — |
| **Advisory** | `paragraph-motion` | `lint_paragraph_motion.py` | — |

Public API: `skill_api.lint_fragment(text, linters=None)` — by default runs the
10 gating rules over a text string. The 7 advisory rules are invisible to this
entry point unless explicitly named in `linters=`. The fuller chapter-level
pass `style_pass_report.generate_report_dict(path)` runs all 12 linters and
returns a structured dict with `negative_metrics`, `vitality_metrics` (Fano
factor, in-band proportion, composite `russell_vitality_score`), and
`positive_checks` (concession-turn count, concrete-instance count, etc.).

### book-qa (28 checks, `skills/book-qa/scripts/`)

**Deterministic D1–D8** (`lint_artifact.py`):

| ID | Catches | Severity |
| --- | --- | --- |
| D1 | orphan citation tokens (`clm-` ids in prose) | critical |
| D2 | raw markdown bleed inside HTML blocks | critical |
| D3 | broken cross-references (figures, footnotes, ToC) | critical/minor |
| D4 | heading hierarchy (missing h1, skipped levels) | critical/minor |
| D5 | count-contract failures (word/footnote/figure counts) | minor |
| D6 | paragraph-length variance outside [0.4, 1.2] CV | minor |
| D7 | CSS-reset clobber (Tailwind preflight without h1 override) | critical |
| D8 | asset 404s (broken image paths) | critical |

**Thesis-derived D9–D12** (read from `qa/supports-defects.json`,
`qa/datalog-defects.json`, `qa/entailment-results.json`):

| ID | Catches | Severity |
| --- | --- | --- |
| D9 | paragraph-orphan (no `supports:` reaching `:Thesis`) | critical |
| D10 | transitive contradiction via Datalog | critical |
| D11 | failed entailment (LLM critic returned `contradicts`/`unrelated`) | critical |
| D12 | unadvanced sub-argument (thesis node with no paragraph) | important |

**Optional D13:** verification-unsat from `neurosym-forge`. Skipped unless
`qa-config.yaml` sets `enable_verification: true`. Critical on hit.

**Chapter swarm C1–C15** (`dispatch_chapter_qa.py` + `checklists/chapter-qa.md`):
one fresh-context agent per chapter, ten dispatch slots, checks 15 dimensions:
heading-hierarchy, cross-references, footnote-quality, citation-noise,
HTML-block-hygiene, terminology-consistency, scene-anchoring, sidebar-quality,
table-quality, paragraph-length-variance, Russell-style-discipline,
citation-completeness, closing-strength, image-alt-text, print-ready-format.

Aggregation: `sentinel.py` merges D-class + C-class into `qa/sentinel.json`;
hard-fail policy = any critical D1–D8, any C2 or C13, any critical C-class.
Healing: `healer.py` runs up to 3 iterations per ticket, exhausted tickets
escalate to operator.

Waiver mechanism: workspace-resident `qa-waivers.yaml`. No skill_api — CLI only.

### book-thesis (`skills/book-thesis/scripts/`)

| Check | Script | Defect class |
| --- | --- | --- |
| Orphan paragraph (no `supports:`) | `lint_supports.py` | D9 |
| Broken supports pointer | `lint_supports.py` | D9 |
| Unreachable supports node | `lint_supports.py` | D9 |
| Unadvanced sub-argument | `lint_supports.py` | D12 |
| Per-paragraph entailment payload prep | `dispatch_entailment.py` | feeds D11 |
| Datalog: direct contradiction | `datalog_consistency.py` | D10 |
| Datalog: transitive contradiction | `datalog_consistency.py` | D10 |
| Datalog: declared conflict | `datalog_consistency.py` | D11 |
| Datalog: orphan paragraph | `datalog_consistency.py` | D9 |
| Datalog: unreachable supports | `datalog_consistency.py` | D11 |
| Datalog: unadvanced sub-arg | `datalog_consistency.py` | D12 |
| Datalog: missing evidence | `datalog_consistency.py` | D12 |

All CLI-only. No `skill_api.lint_*` entry point.

### book-knowledge (`skills/book-knowledge/`)

- **SHACL** (`assets/shapes.ttl`): `tbf:ClaimShape` (one schema:text, status in
  5-state enum, confidence in [0,1], ≥1 source span; verified claims require
  `prov:wasDerivedFrom`) + `tbf:ChapterSectionShape` (sections cite only
  verified claims).
- **Competency queries** (`assets/queries/`): 4 coverage, 1 consistency, 3
  defeasible. The 3 defeasible queries (`rebuttal-presence`, `posterior-floor`,
  `contested-rebuttal-window`) carry `severity` metadata; first two are critical
  and hard-fail under `BLOCKING_DEFEASIBLE = True` (current default).
- **Bayesian belief propagation** (`propagate_belief.py`): up to 20 rounds,
  damps posteriors by ×0.95 / ×0.85 / 1.0 based on counter-claim status.
  Advisory, not blocking.
- **Antonym-pair contradiction detection** (`detect_conflicts.py`): 12 antonym
  pairs over verified claims; flips matches to `disputed`; appends to
  `claims/conflicts.jsonl`.
- **Locator verification** (`verify_claim.py`): cross-checks proposed claim
  text against source span; promotes to `verified`.

### book-compose (`skills/book-compose/scripts/`) — pipeline gates

| Stage | Gate |
| --- | --- |
| 2 preflight | SHACL conformance + `unsupported_claims == 0` + `contradiction_scan == 0` |
| 6 chapter_contract_check | All russellian-style linters + humanizer-pass `ai_fingerprint_total == 0` + persona verdict counts |
| 7 persona_review_pass | Soft-gate when gating personas issue any critical |
| 7b check_address | Every counter-claim in `must_address` is handled in the draft |
| 8 build_release_bundle | Verified-claims slice + draft present |
| 9a book_preflight | Per-chapter manifests valid + SHACL + no failed contracts |
| 9b build_book | Calls 9a; `BookBuildError` fatal |

### humanizer (sibling skill, not in this repo)

24 named patterns loaded via `sibling_skills.py` from `~/.claude/skills/humanizer/SKILL.md`:
undue-significance, notability/coverage, superficial -ing analyses,
promotional language, vague attributions, challenges/future-prospects
templates, AI vocabulary (delve/tapestry/underscore/pivotal/showcase),
copula avoidance, negative parallelisms, rule-of-three overuse, elegant
variation, false ranges, em-dash overuse, boldface overuse, inline-header
lists, Title Case in headings, emojis, curly quotes, collaborative artifacts,
knowledge-cutoff disclaimers, sycophantic tone, filler phrases, excessive
hedging, generic positive conclusions.

`russellian-style.lint_ai_vocabulary` optionally augments its own patterns
with whatever it parses from the humanizer SKILL.md.

## Pre-commit and CI surface

- **`lefthook.yml`** runs `clj-kondo` / `ruff check` / `cargo fmt --check` /
  `regex-compile-check.py` / `nixpkgs-fmt --check` on staged code.
  **Zero prose linting.**
- **`ci/`** is a Python package with one pytest plugin (`lint_no_shadow_writes`)
  that enforces NFR-5 — keeps syntopical-metabook from writing the canonical
  subtrees. **Zero prose linting.**
- **`Makefile`** has a `lint` target that runs ruff + cargo fmt + nixpkgs-fmt
  + two pytest suites against `neurosym-forge`. **Zero prose linting.**

The suite has a rich prose-linting surface, none of which fires on commit or
in CI. Prose linting runs only inside the `book-compose` chapter pipeline.

## What's broken or fragmented

1. **No "Claude generated prose → lint it" trigger.** All russellian-style
   trigger phrases are rewrite-oriented ("apply Russell style", "rewrite in
   Russellian style", "Russell pass on this draft"). After a prompt like
   "write a section on X", Claude has no standing instruction to run
   `lint_fragment`. **This is the user's lived pain from today's session.**
2. **`ai-vocabulary` is detected three times.** Once in
   `russellian-style.lint_ai_vocabulary`, once in
   `book-compose/scripts/humanizer_pass.py`, and once in the humanizer skill
   itself. Three pattern lists drift independently. Pick one.
3. **7 of 17 russellian-style rules are invisible to `lint_fragment`** unless
   the caller explicitly names them. The audit I just ran needed
   `linters=ALL_17_RULES` to surface them. Operators do not know to do this.
4. **`book-qa` has no `skill_api.py`.** It is CLI-only and assumes a
   workspace exists. Claude cannot invoke it on raw prose from chat.
5. **`book-thesis` linters are CLI-only orphans.** They require a thesis-tree
   YAML in a workspace; no in-chat invocation path.
6. **The sys.modules namespace collision** between any tool's `scripts/`
   package and russellian-style's `scripts.lint_*` causes `lint_fragment` to
   silently return `[]` when called from inside another tool's venv. The audit
   caught this bug today and fixed it (commit `af72f17`); the underlying
   architectural fragility remains in any future cross-skill caller.
7. **Trigger-phrase mismatch with the audit-sample contract.** Fixed in commit
   `9a680c0` today, but worth flagging that contract drift between two
   files (the operator-facing sample.md and the operator-gate prompt) had been
   shipped on `main` for the entire prior PR cycle.

## Recommendations (rank-ordered)

### 1. Add an automatic post-generation prose lint hook

The single highest-leverage fix. Add to russellian-style SKILL.md (or to a
new skill rule that fires for any prose-generating session):

> When Claude generates non-quoted prose exceeding ~3 paragraphs in a chat
> turn, automatically run `skill_api.lint_fragment(text, linters=ALL_17_RULES)`
> and report the gating + advisory counts before continuing. If gating > 2,
> flag the verdict and offer to revise.

This eliminates today's failure mode (user had to remind Claude to lint).

### 2. Add `lint_fragment(text, all=True)` and promote the 7 advisory rules

The hidden-rules problem is a real coverage gap. Either change `_DEFAULT_LINTERS`
to include all 17, or add an `all=True` keyword to `lint_fragment` that runs
the full registry. The current asymmetry exists for historical reasons and
costs more than it saves.

### 3. Unify the three ai-vocabulary detectors

Pick the humanizer SKILL.md's 24-pattern catalog as canonical (most
comprehensive), drop the duplicates in `russellian-style.lint_ai_vocabulary`
and `book-compose/scripts/humanizer_pass.py`, have them both call into a
single shared loader.

### 4. Give `book-qa` a `skill_api.py`

A thin wrapper exposing `lint_artifact(workspace) -> list[Defect]` and
`run_sentinel(workspace) -> SentinelReport` would let Claude invoke the post-
build gate from a chat session without going through the CLI.

### 5. Add prose linting to lefthook pre-commit

Run `russellian-style.lint_fragment` on staged `.md` files under `chapters/`,
`book/releases/`, and `docs/`. Block commit on gating violations; surface
advisories. Mirrors the existing `ruff check` pattern.

### 6. Add a master `make audit` target

Single entry-point that runs every linter and gate in the suite against a
target workspace and writes a unified report. The audit tool I just built
(`tools/russellian-style-audit/`) is a starting point for this — extend it to
cover all six linter-bearing skills.

### 7. Refactor the cross-tool `scripts.*` namespace collision

The sys.modules eviction I added to `lint_samples.py` is a workaround, not a
fix. A clean fix: rename each skill's `scripts` package to a unique top-level
name (`russellian_style_scripts`, `book_qa_scripts`, etc.) and update internal
imports. Cost is a one-shot rename across each skill; benefit is that any
future cross-skill caller works without per-call sys.modules surgery.

### 8. Document the trigger-phrase contract per skill in a single index

A `docs/skill-triggers.md` listing every trigger phrase across all skills, so
Claude can confirm at the start of a session which natural-language prompts
fire which linters. Today this is scattered across 7 SKILL.md frontmatters.

## Coverage map: where each defect type lives

| Defect family | Skill | Rule(s) |
| --- | --- | --- |
| Hedging / vague uncertainty | russellian-style | `no-hedging`, `epistemic-precision` |
| Passive voice | russellian-style | `active-voice` |
| Listicle abstract | russellian-style | `listicle-abstract`, `listicle-anaphora` |
| Rhythm uniformity / repetition | russellian-style | `rhythm-uniform-length`, `rhythm-repeated-opening`, `burstiness`, `staccato-paragraph-run` |
| AI vocabulary | russellian-style, book-compose, humanizer | `ai-vocabulary` (×3 implementations) |
| Negation-affirmation template | russellian-style | `negation-affirmation-template` |
| Concrete instance density | russellian-style | `concrete-instance-density` |
| Paragraph motion / rhetorical shape | russellian-style | `paragraph-motion` |
| Orphan citation tokens | book-qa | D1 |
| HTML block hygiene | book-qa | D2, C5 |
| Cross-reference integrity | book-qa | D3, C2 |
| Heading hierarchy | book-qa | D4, C1 |
| Word / footnote / figure counts | book-qa | D5, C10 |
| Paragraph-length variance | book-qa | D6, C10 |
| Tailwind preflight + CSS reset | book-qa | D7 |
| Asset 404 | book-qa | D8 |
| Paragraph orphan (no supports) | book-thesis, book-qa | D9 |
| Transitive contradiction (Datalog) | book-thesis, book-qa | D10 |
| Failed entailment (LLM critic) | book-thesis, book-qa | D11 |
| Unadvanced sub-argument | book-thesis, book-qa | D12 |
| Logical unsatisfiability (Z3) | neurosym-forge, book-qa | D13 (opt-in) |
| Claim shape / state machine | book-knowledge | `tbf:ClaimShape` SHACL |
| Verified-only citation | book-knowledge | `tbf:ChapterSectionShape` SHACL |
| Coverage gaps | book-knowledge | 4 SPARQL coverage queries |
| Defeasible reasoning failure | book-knowledge | 3 SPARQL defeasible queries |
| Antonym-pair contradiction | book-knowledge | `detect_conflicts.py` |
| Belief decay from open counter-claims | book-knowledge | `propagate_belief.py` |
| Chapter contract (russellian + persona) | book-compose | `chapter_contract_check.py` |
| Counter-claim address | book-compose | `check_address.py` |
| Persona panel | book-review, review-conductor | 7 personas, soft-gate |
| Scene anchoring | book-qa | C7 |
| Terminology consistency | book-qa | C6 |
| Sidebar / table / image-alt-text quality | book-qa | C8, C9, C14 |

## Conclusion

The suite is unusually rich in checks — the surface is real, the discipline
is real, and most of the gates fire conservatively (critical defects block
release). The main gap is **discoverability**: Claude does not know to invoke
the linters automatically after generating prose, no commit-time prose linting
exists, and seven russellian-style rules are hidden from the default API. The
three-way duplication of `ai-vocabulary` detection is the clearest case of
"defense in depth that has become drift."

Today's audit (`af72f17` + `563aa4a` + `9a680c0`) caught two real bugs in
this surface — the sys.modules namespace collision silently breaking
`lint_fragment` from any subtool, and the operator-gate / audit-sample
contract mismatch — and the immediate recommendation is to do a similar pass
across the other six skills to find their analogues.
