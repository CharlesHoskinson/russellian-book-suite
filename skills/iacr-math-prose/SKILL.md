---
name: iacr-math-prose
description: Write or revise mathematical and protocol prose for IACR submissions (Crypto, Eurocrypt, Asiacrypt, TCC, PKC, CHES, FSE). Enforces notation discipline, iacrtrans/amsthm environment usage, and the three accepted IACR proof styles (game-based, UC-simulation, concrete-security/asymptotic). Use when user says "draft this theorem", "write the security proof", "format this protocol as a Construction", "rewrite for IACR", "fix the proof prose for Crypto submission", or asks to format definitions/lemmas/reductions. Do NOT use for marketing copy, blog posts, slide decks, or non-cryptography mathematical work.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
---

# iacr-math-prose

Mathematical and protocol prose conventions for IACR-tier cryptography papers. Sibling to `russellian-style`: where `russellian-style` governs connective English prose, `iacr-math-prose` governs notation, environments, and proof bookkeeping.

For authors targeting Crypto, Eurocrypt, Asiacrypt, TCC, PKC, CHES, FSE, or the IACR ePrint archive. Output is expected to pass a program-committee read without rejection on prose grounds.

## When to use

- Drafting a `\begin{definition}`, `\begin{theorem}`, `\begin{lemma}`, or `\begin{construction}` block.
- Writing a security proof in any of the three IACR-accepted styles.
- Formalising a protocol description (party state, messages, side conditions).
- Fixing notation drift across a paper (DSTs, security parameter, query bounds).
- Reviewing a draft for the common IACR rejection reasons.
- Especially: EpochPoET-style protocol papers combining VRF, KES, and ledger reasoning.

Do NOT use for marketing, blog posts, non-cryptography mathematics (e.g., pure number theory unrelated to a primitive), Lean/Coq formalisation (a separate skill), or casual exposition.

## Operating doctrine — three pillars

### Pillar 1 — Notation discipline

- Pick ONE security-parameter letter (`λ` or `n`) and use it across the whole paper.
- Hash domain separation tags (DSTs) are explicit and ciphersuite-prefixed, RFC 9380 style.
- Probability bounds are concrete: `Pr[A wins] ≤ Adv^{ASSUMPTION}_B(λ) + ε(λ)` with `ε` defined as negligible.
- Quantifiers are tight and ordered: `∀ PPT A, ∃ negligible ε, ∀ λ ∈ ℕ: Pr[...] ≤ ε(λ)`.
- Multi-party schemes label parties `P_1, …, P_n` (or `P_i`). `Alice/Bob` only in informal warmup paragraphs.
- All sets, groups, fields are typed at first use: `G is a cyclic group of prime order p, with generator g ∈ G`.
- No symbol reuse across distinct contexts in one paper (no overloading `H` to mean both a hash and a hypothesis).

See `references/notation-discipline.md`.

### Pillar 2 — Environment usage (iacrtrans / amsthm)

- `\begin{definition}` for definitions. Statement italicised by the class, body plain.
- `\begin{theorem}` / `lemma` / `corollary` / `proposition` for claims.
- `\begin{proof}` ends with `\qed` (auto-inserted by amsthm).
- `\begin{construction}` is the custom env for protocol pseudocode (declared with `\newtheorem*{construction}{Construction}`).
- `\begin{remark}` for asides.
- Never `\\` `\\` (forbidden as block separator). Use `\medskip`.
- Never bare equation arrays for derivations — use `align`, `aligned`, or `gather`.

See `references/iacrtrans-environments.md`.

### Pillar 3 — Proof prose structure

Three accepted styles. Pick one per theorem; do not mix.

(a) **Game-based reductions.** Sequence `G_0, G_1, …, G_k`. Each step bounds `|Pr[G_i = 1] − Pr[G_{i+1} = 1]| ≤ ε_i`. Final bound `|Pr[G_0 = 1] − Pr[G_k = 1]| ≤ Σ ε_i`. Template: `templates/theorem-game-based.tex`. See `references/proof-style-game-based.md`.

(b) **UC simulation-based.** Define ideal functionality `F`, real protocol `π`, environment `Z`, simulator `S`. Show `IDEAL_{F,S,Z} ≈^c REAL_{π,A,Z}`. Cite Canetti's UC framework (2001/2020 revision). Template: `templates/theorem-uc.tex`. See `references/proof-style-uc.md`.

(c) **Concrete-security / asymptotic hybrid.** State `Adv^{notion}_A(λ) ≤ q · Adv^{assumption}_B(λ) + ε(λ)` with both a concrete query bound `q` and an asymptotic claim. See `references/proof-style-concrete.md`.

## Workflow

1. **Identify the prose target.** Definition? Theorem statement? Proof? Construction? Remark? Pick one.
2. **Select the template** from `templates/` that matches.
3. **Fill it.** Replace `\TODO{...}` blocks with content. Do not delete the comment frontmatter — it reminds the writer of the invariants.
4. **Verify against the matching reference.** For a game-based theorem, read `references/proof-style-game-based.md` and check every game transition is bounded.
5. **Run the rejection-reasons checklist** in `references/common-rejection-reasons.md` before declaring the block done.
6. **Layer with `russellian-style`** for the connective English between math blocks (transitions, motivation, intuition paragraphs).

## Russellian compatibility

`russellian-style` and `iacr-math-prose` are siblings. They do not conflict on most material.

- **`russellian-style` governs** prose-level discipline: one claim per sentence, no hedging, active voice, no footnotes-for-substance, no rule-of-three filler, no AI staccato.
- **`iacr-math-prose` governs** notation, theorem/proof environment usage, ciphersuite naming, and the three proof-style templates.
- **When they conflict**, `iacr-math-prose` wins inside math blocks (definitions, theorems, proofs, constructions). `russellian-style` wins in connective prose between blocks.
- Concretely: a `\begin{proof}` body MAY contain a long bookkeeping sentence ("By the union bound over `q` queries, `Pr[E_1 ∪ E_2] ≤ q · ε + ε'`"). `russellian-style` would normally split it; `iacr-math-prose` allows it because bookkeeping integrity outranks atomicity.
- Inverse: the paragraph introducing a theorem in plain English is `russellian-style` territory. One claim per sentence. No "we shall see that".

## Common rejection reasons (surface read)

The full list lives in `references/common-rejection-reasons.md`. The top failure modes:

1. **Informal ideal functionality.** A UC theorem with `F` written in prose, not as a labelled box with `Send`, `Receive`, `Output` interfaces.
2. **Vague probability.** `Pr[A wins] ≈ ε` instead of `≤ ε(λ) + negl(λ)` with `ε` and `negl` defined.
3. **Missing query bound.** A concrete-security claim with no explicit `q` (queries to the hash, signing oracle, decryption oracle, etc.).
4. **Symbol reuse.** `H` used for both a hash function and a hypothesis space. Reviewers reject on first pass.
5. **Unspecified security model.** "The scheme is secure" without saying CPA, CCA1, CCA2, EUF-CMA, sUF-CMA, IND-sID-CCA, etc.
6. **Random oracle without domain/range.** `H` modelled as RO but no statement of `H: {0,1}^* → G`.
7. **Informal-then-formal duplication.** Two versions of the same theorem with no marker of which is the official claim.
8. **`\textbf` vs `\mathbf` drift.** Same role styled differently across the paper.
9. **Constructions in inline prose.** A protocol described in a paragraph instead of a numbered `\begin{construction}` block.
10. **Cite-by-prose.** "See [12]" instead of "Boneh and Franklin [12] proved …".
11. **Semantic line breaks in equations.** Breaking `a + b = c + d` between `+` and `b` instead of at `=`.
12. **`\\ \\` as block separator.** Forbidden. Use `\medskip` or `\paragraph{Name.}`.

## Templates

Each template under `templates/` is real LaTeX. Open it, paste it, fill the `\TODO{...}` blocks, and the result will type-check against the iacrtrans class with `\usepackage{amsmath, amsthm, amssymb, cleveref}`.

- `templates/definition.tex` — definition skeleton.
- `templates/theorem-game-based.tex` — theorem + game-based proof skeleton.
- `templates/theorem-uc.tex` — theorem + UC ideal functionality + simulator skeleton.
- `templates/proof-block.tex` — standalone proof skeleton (use when claim is stated elsewhere).
- `templates/protocol-construction.tex` — `\begin{construction}` block with party state and messages.

## References

- `references/notation-discipline.md` — Pillar 1 in detail with GOOD/BAD pairs.
- `references/iacrtrans-environments.md` — Pillar 2: full env list, when to use each.
- `references/proof-style-game-based.md` — Pillar 3a with a worked PRF-from-DDH example.
- `references/proof-style-uc.md` — Pillar 3b with a worked commitment-from-CRS example.
- `references/proof-style-concrete.md` — Pillar 3c with a worked signature concrete-bound example.
- `references/protocol-pseudocode.md` — pseudocode formatting (algorithm2e vs lstlisting vs custom).
- `references/ciphersuite-naming.md` — RFC 9380 / 9381 / 9180 naming.
- `references/theorem-statement-style.md` — how to phrase a theorem so PC reviewers do not reject it.
- `references/common-rejection-reasons.md` — full failure-mode list.

## Composes with

- `russellian-style` — prose discipline between math blocks. See "Russellian compatibility" above.
- `book-knowledge` — supplies the verified claim ledger that this skill's proofs reference.
- `book-compose` — calls this skill when the chapter target is a cryptography paper.
- `book-review` — runs persona reviews; a "Domain Expert" persona checks the artefacts produced by this skill.
- `iacr-review` — sibling reviewer skill that audits drafts written under this skill against IACR PC criteria.

## Usage

- "Draft a theorem statement for EUF-CMA security of `Sig`." — pull `templates/theorem-game-based.tex`, fill, verify against `references/theorem-statement-style.md`.
- "Format this protocol as a Construction." — pull `templates/protocol-construction.tex`.
- "Rewrite this proof in UC style." — read `references/proof-style-uc.md`, pull `templates/theorem-uc.tex`.
- "Run the IACR rejection-reasons check on section 4." — walk `references/common-rejection-reasons.md` against the section.
