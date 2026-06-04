# Notation discipline

The first thing an IACR program-committee member scans is notation. A draft with notation drift gets a "needs revision" before the technical contribution is even evaluated. This reference fixes the conventions.

## 1. Security parameter

Choose exactly ONE letter. Use it everywhere.

- `λ` is the modern default (most IACR papers since ~2010).
- `n` is acceptable in older notation, especially for symmetric primitives where `n` is also the block length — but then never use `n` for anything else.
- `k` is deprecated as a security parameter; reviewers will read it as a "key" or as a "number of queries".

**BAD**

> Let the security parameter be `λ`. The adversary runs in time polynomial in `n`.

**GOOD**

> Let `λ ∈ ℕ` be the security parameter. The adversary `A` is PPT in `λ`.

**GOOD (older style, internally consistent)**

> Let `n ∈ ℕ` be the security parameter. All algorithms are PPT in `n`.

## 2. Hash domain separation tags (DSTs)

Every hash invocation in a protocol must carry an explicit DST. RFC 9380 ("Hashing to Elliptic Curves") established the convention; it is now expected across IACR submissions whether or not curves are involved.

**BAD**

> Let `H` be a hash function. Compute `c := H(m, r)`.

(Reviewers ask: which hash? Same as the commitment hash? Different? Domain collisions?)

**GOOD**

> Let `H_commit, H_chal: {0,1}^* → {0,1}^{2λ}` be independent hash functions modelled as random oracles, with DSTs `"EPC-v1-commit"` and `"EPC-v1-chal"`. In practice both are instantiated from SHA-256 with the standard `RFC 9380` `expand_message_xmd` construction.

DST naming pattern: `"<PROJECT>-<VERSION>-<ROLE>"` where ROLE describes the cryptographic role (`commit`, `chal`, `vrf`, `kdf`, `nonce`). For curve-bound hashes follow RFC 9380's ciphersuite string, e.g. `"BLS12381G2_XMD:SHA-256_SSWU_RO_"`.

## 3. Probability bounds

Probabilities are stated concretely. The form is:

```
Pr[ <event> ] ≤ <concrete bound>(λ) + negl(λ)
```

or equivalently

```
Adv^{<notion>}_A(λ) ≤ <concrete bound>(λ) + negl(λ)
```

`negl(λ)` is a negligible function in `λ`, defined once near the start of the paper as `negl(λ) = o(λ^{-c})` for every constant `c > 0`.

**BAD**

> The probability that the adversary wins is approximately `ε`.

**BAD**

> `Pr[A wins] ≈ ε`.

(The `≈` is unbounded. A reviewer cannot check the inequality.)

**GOOD**

> For every PPT adversary `A`, `Adv^{EUF-CMA}_A(λ) ≤ q_S · Adv^{q-SDH}_B(λ) + q_H / 2^λ`, where `q_S` is the number of signing queries and `q_H` the number of hash queries.

## 4. Quantifier order

The IACR-standard form for a security claim is, exactly:

> For every PPT adversary `A`, there exists a negligible function `ε` such that for every `λ ∈ ℕ`, `Pr[Expt(λ) = 1] ≤ ε(λ)`.

In symbols:

```
∀ PPT A, ∃ negligible ε, ∀ λ ∈ ℕ: Pr[Expt^A(λ) = 1] ≤ ε(λ).
```

Order matters. `∃ ε ∀ A` is a different (and stronger) claim and is almost never what is meant.

**BAD**

> There exists a negligible function `ε` such that all PPT adversaries have advantage at most `ε(λ)`.

(Quantifier inverted: this says one `ε` bounds every adversary.)

**GOOD**

> For every PPT adversary `A`, there exists a negligible function `ε_A` such that `Adv_A(λ) ≤ ε_A(λ)` for all `λ`.

## 5. Party labels

For multi-party protocols, label parties with indexed identifiers.

- Two parties: `P_1, P_2`. Acceptable: `S` (sender), `R` (receiver) for OT/commitment; `V` (verifier), `P` (prover) for ZK. Pick a convention per protocol and keep it.
- `n` parties: `P_1, …, P_n` or `{P_i}_{i ∈ [n]}`.
- Adversary: `A`. Simulator: `S` (collides with sender — disambiguate by paragraph context or rename simulator to `Sim`).
- Environment (UC): `Z`. Functionality: `F` or `F_xxx`.

`Alice` and `Bob` are reserved for the informal warmup paragraph only. Do not use them in a theorem statement, definition, or proof.

## 6. Typed sets, groups, fields

Every set, group, or field is typed at first use.

**BAD**

> Let `g` be a generator. The prover computes `c = g^x`.

**GOOD**

> Let `G` be a cyclic group of prime order `p`, with generator `g ∈ G`. The prover samples `x ←$ ℤ_p` and computes `c := g^x ∈ G`.

Conventions:

- `←$` (or `←_$`) for uniform sampling from a finite set.
- `←` for assignment.
- `:=` for definition.
- `=` for equality.
- `≡` for definitional equivalence (rare; do not confuse with congruence).
- `ℤ_p` (or `\mathbb{Z}_p`) for integers modulo `p`. `𝔽_p` (or `\mathbb{F}_p`) when emphasising the field structure.
- `[n]` for `{1, …, n}`.

## 7. No symbol reuse

A symbol means exactly one thing across the paper.

**BAD**

> Let `H` be a hash function. … In the proof, let `H` be the event that the adversary halts.

**GOOD**

> Let `H` be a hash function. … Let `Halt` be the event that the adversary halts.

This applies across sections. If `n` is the security parameter, do not also use `n` for a number of parties; use `N` or `m`.

## 8. Asymptotic vs concrete

Decide per theorem. The hybrid style (Pillar 3c) gives both, with the concrete bound stated first and the asymptotic statement following as a corollary.

**Asymptotic only:**

> Construction 1 is EUF-CMA secure under the q-SDH assumption.

**Concrete only:**

> For every adversary `A` running in time `t` and making at most `q_S` signing queries and `q_H` hash queries, `Adv^{EUF-CMA}_{A}(λ) ≤ q_S · Adv^{q-SDH}_B(λ) + q_H^2 / 2^λ`.

**Hybrid (recommended for Crypto/Eurocrypt submissions):**

> *Theorem 3.* Under the q-SDH assumption, Construction 1 is EUF-CMA secure. Concretely, for every adversary `A` running in time `t` and making `q_S` signing queries and `q_H` hash queries, there exists `B` running in time `t + O(q_S · T_exp)` with `Adv^{EUF-CMA}_A(λ) ≤ q_S · Adv^{q-SDH}_B(λ) + q_H^2 / 2^λ`.

## 9. Modes of negligibility

Define `negl(λ)` once and refer back. Do not redefine in each section.

- `negl(λ)` — a function `f: ℕ → ℝ_{≥0}` such that for every `c > 0`, `f(λ) < λ^{-c}` for all sufficiently large `λ`.
- `poly(λ)` — a function bounded above by `λ^c` for some constant `c`.
- `noticeable(λ)` — the negation of `negl(λ)`: there exists `c > 0` and infinitely many `λ` with `f(λ) ≥ λ^{-c}`.

## 10. Adversary advantage notation

Standard form: `Adv^{<notion>}_{<scheme>, A}(λ) := |Pr[Expt^{<notion>}_{<scheme>, A}(λ) = 1] − 1/2|` for indistinguishability notions, or `Pr[Expt^{<notion>}_{<scheme>, A}(λ) = 1]` for unforgeability/soundness notions where the experiment outputs 1 iff the adversary wins.

When the scheme is clear from context the scheme subscript is dropped: `Adv^{IND-CPA}_A(λ)`.

## 11. Negligible quick-reference

If the bound is `q_H^2 / 2^λ`: negligible in `λ` only if `q_H = poly(λ)`. State this assumption when invoking it.

If the bound is `1 / p` where `|G| = p`: negligible iff `p = 2^{Θ(λ)}`. State the group order in `λ` at first use.

## 12. What this reference does not cover

- Specific algorithm pseudocode formatting: see `protocol-pseudocode.md`.
- Theorem-statement phrasing: see `theorem-statement-style.md`.
- Naming for cryptographic primitives by RFC: see `ciphersuite-naming.md`.
