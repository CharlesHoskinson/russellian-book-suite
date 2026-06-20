# Proof style — game-based reductions

The dominant proof style in modern IACR submissions. Introduced systematically by Shoup ("Sequences of games: a tool for taming complexity in security proofs", IACR ePrint 2004/332) and Bellare–Rogaway ("Code-based game-playing proofs and the security of triple encryption", Eurocrypt 2006).

## The shape

A game-based proof is a finite sequence `G_0, G_1, …, G_k`. Each game is a probability experiment with the same adversary `A`. The proof bounds the change between successive games:

```
|Pr[G_i ⇒ 1] − Pr[G_{i+1} ⇒ 1]| ≤ ε_i.
```

Summing:

```
|Pr[G_0 ⇒ 1] − Pr[G_k ⇒ 1]| ≤ Σ ε_i.
```

`G_0` is the real security experiment. `G_k` is a game where `A`'s advantage is either zero or bounded by an information-theoretic quantity. The chain of `ε_i` bounds is the security reduction.

## Required bookkeeping

Every game-based proof MUST include:

1. **A statement of `G_0`** matching the security definition verbatim. Reviewers cross-check.
2. **For each `i`, a one-sentence description of what changes** between `G_i` and `G_{i+1}`.
3. **A bound `ε_i`** for each transition, justified by either:
   - A reduction to a stated hardness assumption ("if the change is detectable, `A` solves DDH"), or
   - An information-theoretic argument ("the views are identical unless event `Bad_i` occurs, and `Pr[Bad_i] ≤ q^2 / 2^λ`"), or
   - A bridging step ("the games are syntactically equivalent").
4. **A final bound** `Pr[G_k ⇒ 1] ≤ <constant>` (typically `1/2` for indistinguishability games or `0` for unforgeability games against an unbounded adversary).
5. **Summation** giving the final `Adv` bound.

## Worked example — PRF from DDH

Setting: `G` cyclic group of prime order `p`, generator `g`. Define `F_k(x) := g^{k · H(x)}` where `H: {0,1}^* → ℤ_p` is a hash modelled as a random oracle with DST `"DDH-PRF-v1"`. Claim: `F` is a PRF under the DDH assumption.

### Theorem statement (game-based form)

```latex
\begin{theorem}[PRF security of $F$]
\label{thm:prf-from-ddh}
Under the DDH assumption in $G$, the function family $F$ is a secure PRF in the random oracle model. Concretely, for every PPT adversary $A$ making $q_F$ queries to $F$ and $q_H$ queries to $H$,
\[
  \Adv^{\textsf{PRF}}_{F, A}(\secparam) \leq \Adv^{\textsf{DDH}}_{G, B}(\secparam) + \frac{q_H^2}{2 \cdot p},
\]
where $B$ runs in time $t_A + O(q_F \cdot T_\mathsf{exp})$ and $T_\mathsf{exp}$ is the cost of one exponentiation in $G$.
\end{theorem}
```

### Proof (worked through)

```latex
\begin{proof}
We define a sequence of games $G_0, G_1, G_2, G_3$ and bound the change between successive games.

\paragraph{Game $G_0$ (real PRF game).}
The challenger samples $k \samples \Z_p$. On a query $x$ from $A$, it returns $F_k(x) = g^{k \cdot H(x)}$. Hash queries to $H$ are answered by lazy sampling. $A$ outputs a bit $b'$; $G_0$ outputs $b'$.

\paragraph{Game $G_1$ (collision-free hash).}
Identical to $G_0$, except the challenger aborts and outputs $0$ if two distinct hash queries $x \neq x'$ satisfy $H(x) = H(x')$. By the birthday bound,
\[
  |\Pr[G_0 \Rightarrow 1] - \Pr[G_1 \Rightarrow 1]| \leq \frac{q_H^2}{2 \cdot p}.
\]

\paragraph{Game $G_2$ (DDH switch).}
We replace $g^{k \cdot H(x)}$ with $g^{r_x}$ where $r_x \samples \Z_p$ is a fresh random exponent per distinct query (cached across repeated queries). The challenger now answers $F$-queries with $g^{r_x}$.

A distinguisher between $G_1$ and $G_2$ yields a DDH distinguisher $B$ that, given $(g, g^a, g^b, T)$, simulates $G_1$ when $T = g^{ab}$ and $G_2$ when $T \samples G$. Thus
\[
  |\Pr[G_1 \Rightarrow 1] - \Pr[G_2 \Rightarrow 1]| \leq \Adv^{\textsf{DDH}}_{G, B}(\secparam).
\]

\paragraph{Game $G_3$ (random function).}
Since the $r_x$ are independent and uniform per distinct $x$, the function answers are uniformly distributed in $G$. This is statistically identical to the ideal PRF game:
\[
  \Pr[G_2 \Rightarrow 1] = \Pr[G_3 \Rightarrow 1].
\]

\paragraph{Summing.}
By the triangle inequality,
\[
  \Adv^{\textsf{PRF}}_{F, A}(\secparam)
  = |\Pr[G_0 \Rightarrow 1] - \Pr[G_3 \Rightarrow 1]|
  \leq \Adv^{\textsf{DDH}}_{G, B}(\secparam) + \frac{q_H^2}{2 \cdot p}. \qed
\]
\end{proof}
```

Notice:

- `G_0` is the **exact** real PRF game.
- Each game caption is `Game G_i (<one-line label>)`.
- Each bound is its own displayed equation, terminated by a sentence stating what justifies it.
- The summation is explicit. No "by inspection" or "clearly".
- `\qed` is in-line with the final displayed equation, since the proof ends mid-display. Otherwise amsthm inserts it.

## Pitfalls

1. **Skipped justification.** "By a standard hybrid argument" is unacceptable unless the hybrid is genuinely standard and a one-line citation suffices. Reviewers want the bound.
2. **Implicit query counts.** Always carry `q_F`, `q_H`, `q_S`, etc., through every bound. If a query bound dominates only at one step, still state it.
3. **Misuse of `≈`.** Game transitions are bounded by `≤ ε`, not by `≈ ε`. The whole point of the bookkeeping is that the inequality is concrete.
4. **Forgetting the abort case.** If `G_{i+1}` aborts on some event `Bad`, the change is bounded by `Pr[Bad]`. State `Bad` precisely and bound `Pr[Bad]`.
5. **Reordering games.** Each game changes one thing relative to its predecessor. If you change two things, split into two games.

## Variants

### Code-based games (Bellare–Rogaway)

Some papers present games as explicit pseudocode boxes. This is preferred when the game has nontrivial bookkeeping (e.g., maintained sets of queries, oracle state). Use the `game` or `experiment` environment from `iacrtrans-environments.md`.

### Hybrid arguments

A hybrid argument is a game sequence parameterised by an index `j ∈ [n]`, where `G_j` differs from `G_{j-1}` at a single "position" (e.g., the `j`-th query is answered randomly). Standard for proving security of `n`-fold compositions. Bound: `Adv ≤ n · ε_single`.

### Bad-event analysis

Use when two games are identical until a flag `Bad` is set. State the fundamental lemma:

> If `G_i` and `G_{i+1}` are identical-until-`Bad`, then `|Pr[G_i ⇒ 1] − Pr[G_{i+1} ⇒ 1]| ≤ Pr[Bad in G_i]`.

This is the standard tool for handling hash collisions, signing oracle aborts, decryption oracle failures.

## Checklist before submission

- [ ] `G_0` matches the security definition exactly.
- [ ] Every game transition has an `ε_i` bound stated as a displayed equation.
- [ ] Every `ε_i` is justified by an assumption, an information-theoretic argument, or a syntactic identity.
- [ ] The number of games is finite and stated up front (or evident from the game numbering).
- [ ] The summation step is explicit.
- [ ] Query counts (`q_F`, `q_H`, etc.) appear in the final bound.
- [ ] No `≈`. Only `≤` and `=`.

## See also

- `proof-style-uc.md` for simulation-based proofs.
- `proof-style-concrete.md` for the asymptotic-plus-concrete hybrid style.
- `theorem-statement-style.md` for how to phrase the theorem above the proof.
