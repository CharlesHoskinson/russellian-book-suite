# Theorem statement style

How to phrase the statement inside `\begin{theorem}` so a program-committee reviewer does not reject the paper for vagueness, ambiguity, or under-specification.

This reference is about the **statement only**, not the proof. The statement is what gets cited, screenshotted, and quoted in adversarial reviews. It must stand on its own.

## The five mandatory clauses

A complete IACR theorem statement has, in this order:

1. **The setting.** What primitive, what scheme, what model. ("Let `Sig = (Setup, Sign, Verify)` be the signature scheme of Construction 2. Let `H` be modelled as a random oracle.")
2. **The assumption.** Cited by name. ("Under the q-SDH assumption in `G`, …")
3. **The security notion.** Named precisely. ("`Sig` is EUF-CMA secure, …")
4. **The bound.** For concrete claims, an inequality with explicit query counts. For asymptotic claims, "negligible in `λ`". For UC, "UC-realises `F` against static (or adaptive) corruption".
5. **The reduction overhead.** Time and query overhead of the constructed adversary `B`. ("…with `B` running in time `t_A + O(q_S · T_exp)`.")

A statement missing any of these clauses is incomplete.

## Anti-patterns

### Anti-pattern 1 — "It can be shown that"

**BAD**

> *Theorem 4.* It can be shown that the scheme is secure.

The reviewer asks: under what assumption, in what model, against what adversary class? Reject.

**GOOD**

> *Theorem 4.* Under the decisional Diffie–Hellman assumption in `G`, Construction 2 is IND-CPA secure in the standard model. Specifically, for every PPT adversary `A`, `Adv^{IND-CPA}_{Constr2, A}(λ) ≤ 2 · Adv^{DDH}_{G, B}(λ)` for an adversary `B` running in time `t_A + O(λ)`.

### Anti-pattern 2 — Unspecified security model

**BAD**

> Construction 3 is a secure signature scheme.

"Secure" against what? CMA? KMA? sUF-CMA? EUF-NMA? Reject.

**GOOD**

> Construction 3 is EUF-CMA secure (existential unforgeability under adaptive chosen-message attack).

Always name the model. The standard models are:

- **Signatures:** UF-NMA, EUF-NMA, UF-CMA, EUF-CMA, sUF-CMA (strong UF-CMA), MU-EUF-CMA (multi-user), BUF (blind unforgeability for blind signatures).
- **Encryption:** IND-CPA, IND-CCA1, IND-CCA2, IND-CCA, NM-CPA, NM-CCA.
- **KEM:** IND-CPA, IND-CCA, IND-CCAm (multi-instance).
- **Hash:** collision resistance, preimage resistance, second-preimage resistance, indifferentiability from a random oracle.
- **PRF:** PRF security (real-or-random).
- **MAC:** UF-CMA, sUF-CMA.
- **VRF (RFC 9381):** pseudorandomness, uniqueness, full uniqueness, trusted uniqueness, full collision resistance.
- **Identification:** soundness (passive / active / concurrent), HVZK, ZK.
- **Commitment:** hiding (perfect / statistical / computational), binding (perfect / statistical / computational), equivocability, extractability.
- **MPC / UC:** UC-realisation of `F`; specify corruption model.

### Anti-pattern 3 — Missing query bound

**BAD**

> For every PPT adversary `A`, `Adv^{EUF-CMA}_A(λ) ≤ q · Adv^{q-SDH}(λ)`.

What is `q`? Reject.

**GOOD**

> For every PPT adversary `A` making at most `q_S` signing queries and `q_H` hash queries, `Adv^{EUF-CMA}_A(λ) ≤ q_S · Adv^{q-SDH}_B(λ) + q_H^2 / 2^λ`.

Every query count gets a subscript indicating which oracle is being queried.

### Anti-pattern 4 — Reduction time omitted

**BAD**

> …`Adv^{IND-CPA}_A(λ) ≤ Adv^{DDH}_B(λ)`.

For what `B`? Reject.

**GOOD**

> …`Adv^{IND-CPA}_A(λ) ≤ Adv^{DDH}_B(λ)`, where `B` runs in time `t_A + O(q_E · T_exp)` and `T_exp` is the cost of one exponentiation in `G`.

### Anti-pattern 5 — Mixing informal and formal

**BAD**

> *Theorem 5 (informal).* The scheme is post-quantum secure.
>
> *Theorem 6 (formal).* Under MLWE, …

Two theorems with the same number-ish role. Which is "the" claim?

**GOOD**

> *Theorem 5.* Under the Module-LWE assumption with parameters `(n, q, η)`, Construction 1 is IND-CCA secure in the QROM. Concretely, …
>
> [Optional remark before the theorem stating the informal version, clearly marked as motivational.]

The numbered statement is the formal one. An informal motivational paragraph may precede it but is not a theorem.

### Anti-pattern 6 — Implicit model

**BAD**

> Construction 4 is secure.

In the standard model? Random oracle? Generic group? Ideal cipher? Common reference string?

**GOOD**

> Construction 4 is IND-CPA secure in the random oracle model under the DDH assumption.

If multiple ideal-model assumptions are used, state all of them: "in the (RO, ICM) model" or "in the random oracle and ideal cipher model".

### Anti-pattern 7 — "Roughly"

**BAD**

> `Adv ≤ q^2 · ε` (roughly).

Either it is `≤ q^2 · ε` or it is something else. Reject.

**GOOD**

> `Adv ≤ q^2 · ε + 1/p`, where `p` is the group order.

### Anti-pattern 8 — Unmotivated parameters

**BAD**

> *Theorem 8.* For `λ = 128`, the scheme achieves 128-bit security.

The theorem ought to hold for all `λ`. Picking a specific value as the theorem statement is wrong.

**GOOD**

> *Theorem 8.* For every `λ ∈ ℕ` and every PPT adversary `A`, `Adv^{IND-CPA}_A(λ) ≤ negl(λ)`.
>
> *Concretely, at `λ = 128` (NIST level I), the bound evaluates to `≤ 2^{-110}`.* (Remark following the theorem.)

### Anti-pattern 9 — Citing the assumption by author only

**BAD**

> *Theorem 9.* Under the assumption of Goldreich, Construction 5 is secure.

Which assumption? Goldreich has dozens.

**GOOD**

> *Theorem 9.* Under the existence of one-way functions [Goldreich 2001, Definition 2.1], Construction 5 is secure.

Name the assumption (one-way functions, OWP, DDH, LWE, MLWE, RLWE, q-SDH, q-DBDH, etc.). Cite the definition by chapter/section if it is not universally standard.

### Anti-pattern 10 — UC without corruption model

**BAD**

> *Theorem 10.* Construction 6 UC-realises `F_Com`.

Against which corruption model? Static? Adaptive? Semi-honest? Malicious?

**GOOD**

> *Theorem 10.* In the `F_CRS`-hybrid model, Construction 6 UC-realises `F_Com` against a static, malicious PPT adversary corrupting any strict subset of parties.

## Skeleton templates

### Game-based (signature)

> *Theorem `N`.* Let `Sig = (KeyGen, Sign, Verify)` be the signature scheme of Construction `M`. Let `H: {0,1}^* → R` be modelled as a random oracle with DST `"<DST>"`. Under the `<assumption>` assumption in `<setting>`, `Sig` is EUF-CMA secure. Concretely, for every PPT adversary `A` running in time `t_A` and making at most `q_S` signing queries and `q_H` hash queries,
>
> `Adv^{EUF-CMA}_{Sig, A}(λ) ≤ <bound>(q_S, q_H, λ)`,
>
> where the reduction `B` runs in time `t_A + O(<overhead>)`.

### UC

> *Theorem `N`.* In the `F_<hybrid>`-hybrid model, the protocol `π_<name>` of Construction `M` UC-realises the ideal functionality `F_<target>` (\Cref{fig:f<target>}) against a static (resp. adaptive) malicious PPT adversary corrupting any subset of fewer than `t` parties, assuming `<assumption>`.

### Indistinguishability with concrete bound

> *Theorem `N`.* Let `Π` be the scheme of Construction `M`. Under the `<assumption>` assumption, `Π` is IND-CCA secure. Concretely, for every PPT adversary `A` running in time `t_A` and making at most `q_D` decryption queries,
>
> `Adv^{IND-CCA}_{Π, A}(λ) ≤ <bound>`,
>
> with reduction `B` running in time `t_A + O(q_D · T_dec)`.

### Compositional (multi-instance)

> *Theorem `N`.* Construction `M` is MU-EUF-CMA secure with concrete tightness factor `1`: for every PPT adversary `A` against `u` users running in time `t_A` and making at most `q_S` total signing queries,
>
> `Adv^{MU-EUF-CMA}_{Sig, A}(λ, u) ≤ Adv^{EUF-CMA}_{Sig, B}(λ) + <correction>`,
>
> with `B` running in time `t_A + O(u + q_S)`.

## Style nits

- Capitalise theorem names: "*Theorem 3*" not "*theorem 3*".
- Italicise the theorem text via amsthm; do not add manual `\emph{}`.
- Conclude with a full stop. The statement is a sentence.
- Use `\cref` for cross-references, never hardcoded numbers.
- Place the theorem in the section where it is proven, not where it is first stated informally.

## What this reference does not cover

- How to write the proof: see `proof-style-{game-based,uc,concrete}.md`.
- How to format the surrounding pseudocode: see `protocol-pseudocode.md`.
- How to name the primitives invoked: see `ciphersuite-naming.md`.

## Final check

Before declaring a theorem statement done, ask:

1. Could a reviewer reproduce the experimental setup from this statement alone?
2. Could a reviewer derive the security bound from the cited assumption?
3. Could a reviewer cite this theorem (by number) and trust the citation contains all the model assumptions?

If all three answers are yes, the statement passes. If any answer is no, revise.
