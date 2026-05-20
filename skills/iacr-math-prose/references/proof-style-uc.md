# Proof style — UC simulation-based

The Universal Composability framework, introduced by Canetti ("Universally Composable Security: A New Paradigm for Cryptographic Protocols", FOCS 2001; revised 2020 ePrint 2000/067), is the standard model for protocol composition results. Use UC when the paper claims composability, or when the natural security definition is simulation-based (e.g., MPC, OT, commitments, threshold signatures, secure messaging).

## The shape

A UC proof has four players:

- **Ideal functionality `F`** — an abstract trusted party specifying what the protocol should achieve.
- **Real protocol `π`** — the concrete protocol the parties run.
- **Adversary `A`** — corrupts a subset of parties in the real world.
- **Environment `Z`** — distinguishes the two worlds; provides inputs and reads outputs.

Two worlds are defined:

- **IDEAL world.** Honest parties forward inputs to `F` and outputs from `F`. The simulator `S` interacts with `F` on behalf of corrupted parties.
- **REAL world.** Honest parties run `π`. The adversary `A` interacts with `π` on behalf of corrupted parties.

The protocol `π` **UC-realises** `F` if there exists a PPT simulator `S` such that for every PPT environment `Z`:

```
EXEC_{IDEAL, S, Z} ≈^c EXEC_{REAL, π, A, Z}.
```

`≈^c` is computational indistinguishability of the output of `Z`.

## Required bookkeeping

Every UC proof MUST include:

1. **A formal box for `F`.** Not prose. A labelled environment with `Inputs`, `Outputs`, and `Internal state` clearly demarcated.
2. **A formal description of `π`.** A `construction` block per party role.
3. **A formal description of `S`.** Pseudocode showing what `S` does on each message from `F` and each message from `Z`.
4. **An indistinguishability argument** between IDEAL and REAL views.
5. **Citation of the UC framework version.** Either Canetti 2001 (FOCS) or Canetti 2020 (ePrint 2000/067 latest revision). For protocols using the global UC (GUC) extension, cite Canetti–Dodis–Pass–Walfish 2007.

## Worked example — Commitment from a CRS

Setting: a common reference string (CRS) functionality `F_CRS` provides a uniformly random string `crs ←$ {0,1}^{poly(λ)}` to all parties. We construct a commitment protocol `π_Com` and show it UC-realises the ideal commitment functionality `F_Com` in the `F_CRS`-hybrid model.

### Ideal functionality

```latex
\begin{figure}[t]
\begin{framed}
\textbf{Functionality $\F_\textsf{Com}$.}
$\F_\textsf{Com}$ proceeds as follows, parameterised by parties $P_1, P_2$ and adversary $\Sim$.
\begin{itemize}
  \item \textbf{Commit phase.} Upon receiving $(\textsf{commit}, \sid, m)$ from $P_1$ (the sender), record $m$, send $(\textsf{receipt}, \sid)$ to $P_2$ and $\Sim$. Ignore any subsequent $(\textsf{commit}, \sid, \cdot)$ message.
  \item \textbf{Open phase.} Upon receiving $(\textsf{open}, \sid)$ from $P_1$, send $(\textsf{open}, \sid, m)$ to $P_2$ and $\Sim$.
\end{itemize}
\end{framed}
\caption{Ideal commitment functionality.}
\label{fig:fcom}
\end{figure}
```

### Real protocol

```latex
\begin{construction}[$\pi_\textsf{Com}$ in the $\F_\textsf{CRS}$-hybrid model]
\label{constr:picom}
Let $(\Gen, \Enc, \Dec)$ be a public-key encryption scheme with IND-CPA security.

\textbf{CRS setup.} $\F_\textsf{CRS}$ samples $(\textsf{pk}, \textsf{sk}) \samples \Gen(1^\secparam)$ and outputs $\crs := \textsf{pk}$.

\textbf{Commit phase ($P_1$).}
\begin{itemize}
  \item Receive $\crs = \textsf{pk}$ from $\F_\textsf{CRS}$.
  \item Sample $r \samples \{0,1\}^\secparam$ and compute $c \gets \Enc_{\textsf{pk}}(m; r)$.
  \item Send $(\textsf{commit}, \sid, c)$ to $P_2$.
\end{itemize}

\textbf{Open phase ($P_1$).} Send $(\textsf{open}, \sid, m, r)$ to $P_2$.

\textbf{Verify ($P_2$).} On $(\textsf{open}, \sid, m, r)$, accept iff $\Enc_{\textsf{pk}}(m; r) = c$.
\end{construction}
```

### Simulator

```latex
\textbf{Simulator $\Sim$.} On behalf of the corrupted sender, $\Sim$ proceeds as follows.
\begin{itemize}
  \item Run $(\textsf{pk}, \textsf{sk}) \samples \Gen(1^\secparam)$ and program $\F_\textsf{CRS}$ to output $\textsf{pk}$.
  \item On receiving commit message $c$ from the corrupted sender, decrypt $m' := \Dec_{\textsf{sk}}(c)$ and forward $(\textsf{commit}, \sid, m')$ to $\F_\textsf{Com}$.
  \item On $(\textsf{open}, \sid, m')$ from $\F_\textsf{Com}$, look up the randomness used by the corrupted sender and forward to the corrupted receiver.
\end{itemize}

For a corrupted receiver, $\Sim$ runs the honest sender's commit algorithm on a dummy message $0$, then on $(\textsf{open}, \sid, m)$ from $\F_\textsf{Com}$ \emph{equivocates} by \ldots
```

(In a real submission, the equivocation step requires a more careful construction; the example uses a non-malleable commitment or extractable commitment. Equivocation in plain IND-CPA encryption is impossible — this would be flagged at peer review. Use mixed commitments à la Damgård–Nielsen 2002 or Canetti–Fischlin 2001 for an actually-sound construction.)

### Indistinguishability argument

```latex
\begin{theorem}[UC security of $\pi_\textsf{Com}$]
\label{thm:picom-uc}
If $(\Gen, \Enc, \Dec)$ is IND-CPA secure, then $\pi_\textsf{Com}$ UC-realises $\F_\textsf{Com}$ in the $\F_\textsf{CRS}$-hybrid model against static corruptions.
\end{theorem}

\begin{proof}[Proof sketch]
Fix a PPT environment $Z$ and a PPT adversary $A$. We show $\textsf{IDEAL}_{\F_\textsf{Com}, \Sim, Z} \approxc \textsf{REAL}_{\pi_\textsf{Com}, A, Z}$ in the $\F_\textsf{CRS}$-hybrid model.

Consider the two cases of corruption.

\paragraph{Honest sender, corrupted receiver.}
$Z$'s view in REAL consists of the CRS $\textsf{pk}$, a commitment $c = \Enc_{\textsf{pk}}(m; r)$, and the opening $(m, r)$. In IDEAL, $\Sim$ produces $c' = \Enc_{\textsf{pk}}(0; r')$ and equivocates to $(m, r'')$.

If $Z$ distinguishes the two views with non-negligible probability $\delta$, we build a PPT IND-CPA adversary $B$ that breaks the encryption scheme with the same advantage. $B$ receives the challenge $\textsf{pk}^*$, runs $Z$ internally with $\crs := \textsf{pk}^*$, submits messages $(0, m)$ to its IND-CPA challenger, and forwards the challenge ciphertext as the commitment. Thus $\Adv^{\textsf{IND-CPA}}_{B}(\secparam) \geq \delta$, contradicting IND-CPA security.

\paragraph{Corrupted sender, honest receiver.}
$\Sim$ extracts $m'$ by decrypting $c$ with $\textsf{sk}$ (which $\Sim$ knows by programming the CRS). The views are perfectly indistinguishable: in REAL, $P_2$ verifies the opening; in IDEAL, $\F_\textsf{Com}$ enforces consistency. \qed
\end{proof}
```

## Pitfalls

1. **`F` defined informally.** The functionality must be a labelled box (figure environment is standard) with `Inputs`, `Outputs`, and `Internal state`. Prose-only definitions are rejected.
2. **Static vs adaptive corruption unstated.** Specify which model. Default is static; adaptive is harder and must be explicitly claimed.
3. **`S` runtime unbounded.** `S` must be PPT. If extraction requires inverting a hash, the simulator must be PPT relative to that hash; usually this means random-oracle programming.
4. **Hybrid model unstated.** If `π` uses `F_CRS`, `F_RO`, `F_KEY`, or any other ideal sub-functionality, state "in the $\F_\textsf{XXX}$-hybrid model".
5. **Composition theorem invoked without justification.** UC composition gives composability for free; cite Canetti 2020 §10 explicitly when invoking it.
6. **Equivocation hand-waved.** If `S` needs to equivocate (open a commitment to a chosen message), the protocol must support equivocation. Plain IND-CPA encryption does not.
7. **GUC vs UC confusion.** If the paper uses global setup (e.g., a global random oracle), cite Canetti–Dodis–Pass–Walfish 2007.

## Variants

### UC with abort

For protocols that allow the adversary to selectively abort honest parties, use the standard `with-abort` variant of `F`. State this in the functionality box.

### Simulation-based without UC

Earlier definitions (Goldreich's "Foundations of Cryptography Vol. 2", 2004) used simulation-based security without the composition theorem. State explicitly which framework you use. Modern submissions default to UC.

### Stand-alone simulation

Simulation against a single environment, no composition. Acceptable for proof-of-concept results. State "stand-alone simulation" and cite Goldreich Vol. 2.

## Checklist before submission

- [ ] `F` is in a labelled `figure` environment with `Inputs`, `Outputs`, `Internal state`.
- [ ] `π` is in a `construction` block, per party.
- [ ] `S` is in pseudocode or a `construction` block.
- [ ] Corruption model stated (static / adaptive; semi-honest / malicious).
- [ ] Hybrid model stated.
- [ ] UC framework citation: Canetti 2001 (FOCS) or Canetti 2020 (ePrint 2000/067).
- [ ] Indistinguishability argument is a reduction to a stated assumption.
- [ ] `S` is PPT.
- [ ] If equivocation is needed, the protocol supports it (e.g., mixed commitments, trapdoor commitments).

## See also

- `proof-style-game-based.md` for non-simulation security.
- `protocol-pseudocode.md` for formatting `F`, `π`, `S`.
- `theorem-statement-style.md` for phrasing UC theorems.
