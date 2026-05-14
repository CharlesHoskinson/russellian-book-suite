# Russellian Style Guide

This file enumerates the principles of technical writing transmuted through Bertrand Russell's analytic discipline. Read this file when actively rewriting prose. Each principle lists: the rule, why it matters, and a worked example.

## Domain 1 — Writing Mindset (Epistemological Certainty)

### 1. Eliminate persuasive authority
Never persuade the reader of a tool's value through adjectives or superlatives. State empirical facts. Strip all promotional inflection.
- Bad: "Our highly robust API easily handles enterprise-grade workloads."
- Good: "The API processes 4,000 requests per second on a single instance."

### 2. Eliminate probabilistic hedging
Replace ambiguous qualifiers with deterministic thresholds.
- Bad: "The script might fail under heavy load."
- Good: "The script fails when CPU utilization exceeds 90 percent."

### 3. Prefer the simplest adequate vocabulary
The shortest precise word displaces the complex Latinate one.
- Bad: "The system facilitates the optimization of resource allocation."
- Good: "The system reduces memory use."

### 4. Treat every sentence as an atomic fact
A sentence must withstand empirical scrutiny on its own. If it cannot, atomize it.

### 5. Refuse rhetorical embellishment
No "obviously," "clearly," "of course." If the conclusion is self-evident, the proof speaks for itself.

## Domain 2 — Structure and Flow (Axiomatic Thesis Spine)

### 6. State the axiom in the first paragraph
The opening establishes the foundational premise. Every subsequent section is a derivation from it. Like Principia Mathematica: nothing appears without prior justification.

### 7. Excise sideways drift
Tangential information violates the derivation chain. Remove it. If it is essential, it belongs in a separate document.

### 8. Transitions are logical operators
"Therefore," "if," "and," "but" are not stylistic — they bind atomic facts into molecular propositions. Use them with precision.

### 9. Section order follows logical dependency
Section N may depend only on sections 1..N-1. Forward references are bugs.

### 10. End each section with the conclusion it earned
The reader must always know which proposition has just been established.

## Domain 3 — Teaching and Explanation (Logical Atomism)

### 11. Decouple complex conditionals
Tangled multi-variable sentences split into stacked atomic propositions. See `logical-atomism-for-writers.md` for the IF/AND IF/THEN pattern.

### 12. Define before deploying
Never use a term in an explanation before defining it. Acquaintance precedes description.

### 13. One paragraph, one logical movement
A paragraph is a derivation step. If it contains two, split it.

### 14. Build mental models, not memorization
Explain why the system behaves this way, not only what it does. Causality first.

### 15. Concrete examples are non-optional
Every abstract claim earns the right to exist by producing a concrete instance.

## Domain 4 — Sentence Craft (Signal Density)

### 16. Active voice without exception
The actor and the action must be explicit.
- Bad: "The server is provisioned by the script."
- Good: "The script provisions the server."

### 17. The adjective is the enemy of the noun; the adverb the enemy of the verb
Strip modifiers ruthlessly. Earn each one.

### 18. Linear sentence trajectory
The beginning of a sentence must not lead the reader to an expectation contradicted by the end. Re-engineer such sentences into atomic statements.

### 19. Parallel grammatical structure in lists
All bullets share opening type — imperative verb, noun phrase, gerund — never mixed.

### 20. Sentence length budget
Default ceiling: 30 words. Past that, atomize.

**Compound sentences allowed when atomic.** A compound sentence is acceptable when each clause runs under 12 words AND the clauses share a subject AND the connective is a true logical operator (and / but / therefore). Avoid stringing 4–5 short sentences when 1–2 balanced sentences carry the same atomic content. Russell himself wrote balanced sentences; the atomic-proposition rule applies to logical content, not to sentence count.

### 21. Code blocks repeat themselves; the surrounding prose does not
The prose explains why the code is the optimal resolution. It never narrates what the code does.

## Domain 5 — Reasoning and Argument (Declarative Proofs)

### 22. The solution is an earned conclusion
The problem is stated, the constraints defined, the atomic facts laid out, and only then the resolution arrives.

### 23. Code as empirical evidence
A code example is not an illustration — it is the empirical proof supporting the surrounding theorem.

### 24. State, do not announce
"Here we will explain X" is forbidden. Write X.

### 25. No conversational closers
"Hope this helps" and "Let me know if you have questions" are removed. The document either succeeds or fails on its own.

### 26. The document is the proof
A technical document is a formal argument with a thesis, a derivation, and a conclusion. Treat it as such.

## Domain 6 — Elegance (Cadence and Pattern Refusal)

### 27. Refuse the listicle abstract.
A chapter does not "rest on" a numbered list of premises. The premises are the prose. If the prose cannot carry them, the prose is wrong, not the prose's lack of a roadmap.

- Bad: "The manual rests on six premises: 1. X. 2. Y. 3. Z..."
- Good: prose that argues X, Y, and Z in order, with each claim earning its place.

### 28. Vary the rhythm.
Four sentences of identical word count and shape are a fingerprint, not a discipline. Russell himself wrote alternating short and long sentences. The atomic-proposition rule applies to logical content, not to sentence cadence.

- Bad: four consecutive 18-word sentences each beginning with "Bermuda".
- Good: alternation of short declarative and longer balanced sentences.
