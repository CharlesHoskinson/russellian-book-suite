# iacr-math-prose

Mathematical and protocol prose conventions for IACR-tier cryptography papers (Crypto, Eurocrypt, Asiacrypt, TCC, PKC, CHES, FSE, IACR ePrint).

This skill is a sibling of `russellian-style` in the russellian-book-suite. It teaches a Claude Code agent how to write definitions, theorems, lemmas, constructions, and proofs in a form that passes a program-committee read.

## Three pillars

1. **Notation discipline.** Single security parameter, explicit DSTs, concrete probability bounds, tight quantifiers, typed sets/groups/fields, no symbol reuse.
2. **Environment usage.** `iacrtrans` + `amsthm` conventions: `definition`, `theorem`, `lemma`, `corollary`, `proposition`, `proof`, `remark`, `construction`. No `\\ \\` block separators. No bare equation arrays.
3. **Proof prose structure.** Three accepted styles: game-based reductions, UC-simulation, concrete-security/asymptotic hybrid. Each has a template.

## Layout

```
iacr-math-prose/
  SKILL.md
  README.md
  pyproject.toml
  references/
    notation-discipline.md
    iacrtrans-environments.md
    proof-style-game-based.md
    proof-style-uc.md
    proof-style-concrete.md
    protocol-pseudocode.md
    ciphersuite-naming.md
    theorem-statement-style.md
    common-rejection-reasons.md
  templates/
    definition.tex
    theorem-game-based.tex
    theorem-uc.tex
    proof-block.tex
    protocol-construction.tex
```

## Relation to russellian-style

`russellian-style` governs connective English prose. `iacr-math-prose` governs notation, environments, and proofs. Inside a `\begin{theorem}` or `\begin{proof}` block, this skill wins. In the paragraphs between blocks, `russellian-style` wins.

## Invocation

Load this skill when the task target is mathematical or protocol prose for a cryptography venue. The user-facing triggers live in `SKILL.md`.
