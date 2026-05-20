# Proof style — concrete-security / asymptotic hybrid

The hybrid style states a security result in both **concrete** and **asymptotic** forms. It is the IACR default for primitives that will be deployed (signatures, KEMs, encryption schemes, MACs, AEADs), because deployments require concrete parameter selection but security definitions are stated asymptotically.

Origin: Bellare–Rogaway "The Exact Security of Digital Signatures" (Eurocrypt 1996) — first systematic concrete-security treatment. Now mandatory in NIST PQC submissions, all CFRG drafts, and most Eurocrypt/Crypto deployment papers.

## The shape

A hybrid claim has three layers:

1. **Concrete bound.** A function of explicit query counts and time bounds. Example: `Adv^{EUF-CMA}_A(λ) ≤ q_S · Adv^{q-SDH}_B(λ) + q_H^2 / 2^λ`.
2. **Asymptotic statement.** "Under the q-SDH assumption, the scheme is EUF-CMA secure."
3. **Parameter table.** A concrete instantiation showing the bound at deployment parameters (NIST level I, III, V or analogous).

## Required bookkeeping

- Explicit time bound for the reduction: `B` runs in time `t_A + O(<concrete overhead>)`.
- Explicit query counts threaded through every step.
- Both the reduction loss factor (e.g., `q_S`) and additive terms (e.g., `q_H^2 / 2^λ`) stated.
- Parameter table mapping NIST levels to (group size, hash output length, signature size, security bits).
- If quantum security is claimed, state the model (QROM / standard model) and cite Boneh et al. "Random oracles in a quantum world" (Asiacrypt 2011).

## Worked example — Concrete EUF-CMA bound for a Schnorr-style signature

Setting: Schnorr signatures over `G` of prime order `p ≈ 2^{2λ}` (so the elliptic-curve group has size `~ 2^{2λ}`, giving `λ` bits of classical security against generic group attacks). Hash `H: {0,1}^* → ℤ_p` with DST `"SCHNORR-v1"`, modelled as a random oracle.

### Theorem statement

```latex
\begin{theorem}[Concrete EUF-CMA security of Schnorr]
\label{thm:schnorr-concrete}
Let $G$ be a cyclic group of prime order $p$ in which the discrete logarithm problem is $(t, \varepsilon_\textsf{DL})$-hard. Let $H: \{0,1\}^* \to \Z_p$ be modelled as a random oracle with DST $\texttt{"SCHNORR-v1"}$. For every adversary $A$ against EUF-CMA of the Schnorr signature scheme that runs in time $t_A$ and makes at most $q_S$ signing queries and $q_H$ hash queries,
\[
  \Adv^{\textsf{EUF-CMA}}_{\textsf{Schnorr}, A}(\secparam) \leq
    \sqrt{q_H \cdot \varepsilon_\textsf{DL}(t_B, \secparam)} + \frac{q_H + q_S}{p},
\]
where $t_B = 2 \cdot t_A + O(q_S \cdot T_\textsf{exp})$, by the forking lemma (Pointcheval--Stern, J.~Cryptology 2000).

\medskip
\noindent\textbf{Asymptotic corollary.} Under the discrete logarithm assumption in $G$, the Schnorr signature scheme is EUF-CMA secure in the random oracle model.
\end{theorem}
```

### Parameter table

```latex
\begin{table}[t]
\centering
\caption{Concrete parameters for the Schnorr signature scheme at NIST security levels.}
\label{tab:schnorr-params}
\begin{tabular}{lcccc}
\toprule
NIST level & $\log_2 p$ & $|\sigma|$ (bytes) & $|pk|$ (bytes) & Target security \\
\midrule
I   & 256 & 64  & 32 & $\geq 2^{128}$ classical \\
III & 384 & 96  & 48 & $\geq 2^{192}$ classical \\
V   & 512 & 128 & 64 & $\geq 2^{256}$ classical \\
\bottomrule
\end{tabular}
\end{table}
```

### Proof skeleton (cited, not redone)

```latex
\begin{proof}[Proof sketch]
By the forking lemma (Pointcheval--Stern, J.~Cryptology 13(3), 2000, Theorem 3), an EUF-CMA forger $A$ producing a valid forgery with probability $\varepsilon$ can be converted into a DL solver $B$ running in time $2 t_A + O(q_S \cdot T_\textsf{exp})$ with success probability at least
\[
  \varepsilon_\textsf{DL} \geq \frac{\varepsilon^2}{q_H} - \frac{q_H + q_S}{p}.
\]
Rearranging gives the stated bound. \qed
\end{proof}
```

## Interpreting the concrete bound

For the example above, at NIST level I (`log_2 p = 256`, `λ = 128`):

- `q_H` is the hash query budget; deployments typically assume `q_H ≤ 2^{80}`.
- `q_S` is the signing query budget; deployments typically assume `q_S ≤ 2^{30}`.
- `ε_DL(t_B, λ)` is the best known DL solver advantage; for prime-order elliptic curves of size `2^{256}` this is `~ 2^{-128}` in the classical setting.

Substituting: `Adv^{EUF-CMA} ≤ sqrt(2^{80} · 2^{-128}) + (2^{80} + 2^{30}) / 2^{256} ≈ 2^{-24}`.

This is **insufficient** for `λ = 128` security: the forking-lemma loss requires a larger group. Either raise `log_2 p` to ~384 or use a tight reduction (e.g., Schnorr-like signatures with a tight proof à la Kiltz–Masny–Pan 2016).

## Pitfalls

1. **Missing query count.** A bound `Adv ≤ ε` without `q_H`, `q_S` is uninstantiable. Reviewers reject.
2. **Loose reduction sold as tight.** State the loss factor `q_S` (or `q_H` for the forking lemma); never hide it.
3. **Parameter table omitted.** A concrete-security claim without a parameter table is not actionable.
4. **NIST level conflated with `λ`.** NIST levels are I (128-bit classical / 64-bit quantum), III (192/96), V (256/128). State both. Do not assume `λ = NIST level`.
5. **Quantum claim without QROM.** If the paper claims post-quantum security, the proof must be in the quantum-accessible random oracle model (QROM). Cite Boneh–Dagdelen–Fischlin–Lehmann–Schaffner–Zhandry, Asiacrypt 2011.
6. **Time bound for `B` omitted.** Always state `t_B` as a function of `t_A` and concrete overheads.
7. **Forking lemma without citation.** Cite Pointcheval–Stern 2000 (J. Cryptology).
8. **Generic group bound dressed as concrete.** Generic group model bounds (e.g., for DL in pairing groups) are weaker than standard model bounds; if the only bound is generic, say so.

## Quantum variant

For post-quantum schemes, add:

- The model: QROM (Boneh et al. 2011) or standard model (rare for hashed primitives).
- A factor of `q_H^2` instead of `q_H` for the forking-lemma analogue in QROM (Don–Fehr–Majenz–Schaffner, Crypto 2019, "Online-extractability in the quantum random-oracle model").
- A parameter table showing both classical and quantum security bits.

## Tight reductions

A reduction is tight if the loss factor is constant (independent of `q_S`, `q_H`). Tight reductions are valuable because they allow smaller parameters. State tightness explicitly:

> *Theorem 7.* Construction 3 admits a tight reduction to the DDH assumption: `Adv^{IND-CPA}_A(λ) ≤ 2 · Adv^{DDH}_B(λ) + 2^{-λ}`, with `B` running in time `t_A + O(λ)`.

## Checklist before submission

- [ ] Concrete bound stated as an inequality with explicit query counts.
- [ ] Asymptotic statement given as a corollary or "Asymptotic corollary" remark.
- [ ] Reduction time bound `t_B` stated explicitly.
- [ ] Parameter table giving the bound at NIST level I / III / V.
- [ ] If quantum: QROM stated, with citation to Boneh et al. 2011.
- [ ] Tightness stated (tight / loose with factor `q_S`).
- [ ] Forking lemma, if used, cited to Pointcheval–Stern 2000.

## See also

- `proof-style-game-based.md` for the per-game bound that feeds into the concrete sum.
- `theorem-statement-style.md` for phrasing the hybrid claim.
- `ciphersuite-naming.md` for naming the concrete instantiation.
