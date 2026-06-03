# Negative Triggers and Refusal Protocol

## Part A — Refusal protocol

### When to refuse activation

The feynman-style skill refuses to run on the following text types. In each case, the Feynman voice would actively harm the document's purpose.

- **Formal proofs and theorem statements** — logical structure depends on exact formalism; conversational warmth obscures the deduction chain.
- **Legal and contractual text** — clause language is precise by design; "warming it up" changes legal meaning.
- **Specification and RFC text** — requirements and normative language (SHALL, MUST) must not be paraphrased into casual register.
- **API reference documentation** — function signatures, parameter types, return values, and error codes require exact language; analogies introduce ambiguity.
- **Bureaucratic boilerplate** — forms, compliance notices, and standard disclaimers exist to satisfy external requirements; their register is not a style choice.
- **Academic abstracts** — abstracts follow a genre with strict length and register constraints that serve a specific reader function; Feynman warmth disrupts that function.

**Refusal template:**

> This passage is [genre], which depends on [the property the skill would alter]. The feynman-style skill is a second-pass surface rewrite for technical prose that has already been Russellized. It is not appropriate here.

### The sequence constraint

feynman-style must run after russellian-style, never before. The two-pass contract is: Russell fixes the argument; Feynman warms the surface. If russellian-style has not run, the argument may still contain hedges, passive constructions, Latinate bloat, and vague claims. Applying Feynman warmth to unfixed prose produces readable-but-wrong output. If asked to run before a Russell pass, refuse and explain the sequence.

### When to activate

- Technical explanations, tutorials, and explainers that have already been through a Russell pass.
- Book chapters that are factually and argumentatively complete but cold in register.
- Engineering blog posts and design docs where the author's goal is comprehension, not engagement metrics.
- Any prose where the user asks to "make this click," "warm this up," or "lower the reading difficulty."

When unsure: ask "Has this text had a Russell pass?" If no: refuse and recommend the correct sequence.

---

## Part B — Surface/Integrity linter partition

Feynman legitimately overrides several rules that russellian-style enforces. Contractions, rhetorical questions, direct address, casual rhythm — these are the point of the skill, not violations. Running the full Russell linter battery on Feynman-final prose would flag the desired output as broken.

The partition below resolves this. On Feynman-final text, only **Integrity** linters run. **Surface** linters are suppressed.

The partition is taken directly from `assets/feynman-rules.json` (`linter_class` field). Verify against that file if the partition is ever updated.

### Partition table

| Rule | Class | Why |
|---|---|---|
| `reading-grade` | surface | Feynman deliberately lowers reading grade; suppressing this avoids false failures on text written at a deliberately easy register (the Feynman budget re-applies the grade ceiling as its own gate) |
| `conversational-cold` | surface | Feynman adds conversational markers; this linter would always pass after a Feynman pass and is not useful |
| `latinate-diction` | surface | Feynman substitutes plain words; the Russell Latinate guard is superseded by the Feynman diction rules |
| `analogy-absent` | surface | Feynman adds analogy; a residual absence is a Feynman vitality failure, not a Russell linter matter |
| `abstraction-heavy` | surface | Same reason as `analogy-absent` — abstraction density is managed by the Feynman concreteness linter |
| `curiosity-absent` | surface | Feynman adds curiosity markers; residual absence is a Feynman vitality issue |
| `rhythm-uniform-length` | surface | Feynman varies rhythm differently than Russell; the Russell rhythm guard would misfire on Feynman cadence |
| `no-hedging` | surface | Feynman re-introduces hedges of the honest-doubt type; the Russell no-hedging gate would flag deliberate moves |
| `signal-density` | surface | Feynman accepts lower signal density in exchange for concreteness; suppressed to avoid penalizing valid moves |
| `staccato-paragraph-run` | surface | Feynman uses short punchy runs legitimately; the Russell staccato guard would misfire |
| `ai-vocabulary` | integrity | AI-slop vocabulary is always wrong; Feynman warmth does not excuse it |
| `active-voice` | integrity | Active voice is not a register choice; passive constructions that survive the Russell pass are still bugs |
| `parallel-structure` | integrity | Structural grammar rules are not overridden by Feynman warmth |
| `footnote-orphan` | integrity | Orphaned footnote references are document errors; register does not fix them |
| `preserve-argument` | integrity | The argument is frozen after the Russell pass; this is a hard gate and always runs |

### Feynman budgets

In addition to the Integrity linters, the Feynman-specific budget checks run on Feynman-final text (thresholds from `feynman-rules.json`):

- `reading-grade` budget: 12 (grade level ceiling)
- `conversational-cold`: 0 (no cold conversational sentences allowed)
- `latinate-diction`: 2 (at most 2 Latinate substitution targets)
- `analogy-absent`: 0 (at least one analogy per section)
- `abstraction-heavy`: 0 (no ungrounded abstraction blocks)
- `curiosity-absent`: 2 (at most 2 sections missing curiosity markers)
- `ai-vocabulary`: 0 (hard zero)

These are Feynman pass quality gates, not Russell surface checks.
