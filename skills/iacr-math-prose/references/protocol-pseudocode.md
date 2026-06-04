# Protocol pseudocode

How to render a protocol description as pseudocode the IACR PC will accept.

## Three options

1. **`algorithm2e`** — for algorithmic primitives (signature generation, KEM encapsulation, key derivation). Polished output, line numbers, supports inline math.
2. **`lstlisting`** — for protocol pseudocode that resembles a programming language (e.g., MPC protocols where state mutation matters).
3. **Custom `construction` env** — for high-level protocol descriptions where each party has a phase-by-phase narrative. The IACR default.

Pick one per paper. Mixing is permitted only when justified (e.g., `algorithm2e` for sub-routines, `construction` for the top-level protocol).

## Choice 1: `algorithm2e`

```latex
\usepackage[ruled,linesnumbered]{algorithm2e}

\begin{algorithm}[t]
\caption{$\Sign(\sk, m)$: Schnorr signature generation.}
\label{alg:schnorr-sign}
\KwIn{secret key $\sk \in \Z_p$, message $m \in \{0,1\}^*$}
\KwOut{signature $\sigma = (R, s) \in G \times \Z_p$}
$r \samples \Z_p$\;
$R \gets g^r$\;
$e \gets H(R \| \pk \| m)$\;
$s \gets r + e \cdot \sk \pmod{p}$\;
\Return $(R, s)$
\end{algorithm}
```

Use when:

- Each step is an explicit assignment or sampling.
- Line numbers help the analysis (e.g., the proof says "line 3 uses fresh randomness").
- The algorithm fits on one page.

Do NOT use when:

- The description is more than ~30 lines: split into helpers or use `construction`.
- Inter-party messages are the point: `algorithm2e` does not natively render send/receive.

## Choice 2: `lstlisting`

```latex
\usepackage{listings}
\lstdefinelanguage{Protocol}{
  morekeywords={if,then,else,send,receive,abort,output,wait,upon,fork,sample},
  sensitive=true,
}
\lstset{
  language=Protocol,
  basicstyle=\small\ttfamily,
  keywordstyle=\bfseries,
  mathescape=true,
  numbers=left,
  numberstyle=\tiny,
}

\begin{lstlisting}[caption={MPC opening phase}, label=lst:mpc-open]
upon receive (open, sid, s_i) from P_i:
  Store s_i in OpenSet[sid].
  if |OpenSet[sid]| >= t:
    s := Reconstruct(OpenSet[sid])
    output (opened, sid, s)
\end{lstlisting}
```

Use when:

- The protocol has explicit `send` / `receive` / `wait upon` semantics.
- Reactive behaviour (event-driven dispatch) matters.

## Choice 3: Custom `construction` environment

Declared as:

```latex
\newtheorem{construction}{Construction}
```

The IACR default for non-trivial protocols. Each party gets a labelled section; each phase is a labelled sub-block.

```latex
\begin{construction}[Threshold signature, $\TS_n^t$]
\label{constr:ts}
Let $G$ be a cyclic group of prime order $p$, generator $g$. Let $H_\mathsf{chal}: \{0,1\}^* \to \Z_p$ with DST $\texttt{"TS-v1-chal"}$.

\textbf{Setup}$(1^\secparam, n, t)$:
\begin{itemize}
  \item Run a $(t, n)$-VSS to share a uniform secret $\sk \samples \Z_p$. Each $P_i$ obtains share $\sk_i$.
  \item Output public key $\pk = g^\sk$ and shares $\{\sk_i\}_{i \in [n]}$.
\end{itemize}

\textbf{Partial-sign}$(\sk_i, m)$ at party $P_i$:
\begin{itemize}
  \item Sample $r_i \samples \Z_p$. Set $R_i \gets g^{r_i}$.
  \item Broadcast $R_i$. Wait until $\{R_j\}_{j \in S}$ are received for some $S \subseteq [n]$ with $|S| \geq t$.
  \item Compute $R \gets \prod_{j \in S} R_j$.
  \item Compute $e \gets H_\mathsf{chal}(R \| \pk \| m)$.
  \item Compute partial signature $s_i \gets r_i + e \cdot \lambda_i^S \cdot \sk_i \pmod{p}$, where $\lambda_i^S$ is the Lagrange coefficient.
  \item Broadcast $s_i$.
\end{itemize}

\textbf{Combine}$(\{s_i\}_{i \in S}, R, m)$:
\begin{itemize}
  \item $s \gets \sum_{i \in S} s_i \pmod{p}$.
  \item Output $\sigma \gets (R, s)$.
\end{itemize}

\textbf{Verify}$(\pk, m, \sigma = (R, s))$: accept iff $g^s = R \cdot \pk^{H_\mathsf{chal}(R \| \pk \| m)}$.
\end{construction}
```

Use when:

- The protocol has multiple phases (setup, online, finalisation).
- Each party has a non-trivial local state.
- The exposition needs to interleave with security analysis.

## Per-party state

For protocols where parties maintain state across phases:

```latex
\begin{construction}[$\pi$]
\textbf{State of $P_i$.} The local state $\state_i$ is a tuple:
\begin{itemize}
  \item $\state_i.\textsf{round}$ — current round counter, initially $0$.
  \item $\state_i.\textsf{view}$ — view of broadcast messages, initially empty multiset.
  \item $\state_i.\textsf{decided}$ — local output, initially $\bot$.
\end{itemize}

\textbf{On message $(\textsf{vote}, r, v)$ from $P_j$ at $P_i$:}
\begin{itemize}
  \item If $r = \state_i.\textsf{round}$, add $(j, v)$ to $\state_i.\textsf{view}$.
  \item If $|\state_i.\textsf{view}| > 2n/3$, decide $\state_i.\textsf{decided} \gets \mathsf{Majority}(\state_i.\textsf{view})$.
\end{itemize}
\end{construction}
```

## Message format

State message format once, at the top of the construction:

> Messages are tuples `(tag, sid, payload)` where `tag ∈ {commit, open, vote, ack}` and `sid` is a session identifier. Cryptographic payloads are encoded as fixed-length byte strings; integer payloads as little-endian unsigned integers.

For wire-format protocols (post-quantum KEMs, signatures): cite the canonical encoding (e.g., NIST FIPS 204 ML-DSA byte format).

## Side conditions and error handling

Side conditions are stated as **guards** preceding the action they guard.

**BAD**

> The party broadcasts the share, but only if the round counter is correct.

**GOOD**

> If `state.round = r`, then broadcast `(share, sid, s_i)`. Otherwise, ignore the message.

Error handling MUST be explicit:

- **Abort.** State precisely which messages cause abort. "If the proof does not verify, output `⊥` and halt."
- **Wait.** State precisely the threshold. "Wait until `2n/3 + 1` distinct `(vote, r, v)` messages are received."
- **Ignore.** State precisely the conditions. "Ignore any `(commit, sid, ·)` message after the first."

## Common mistakes

1. **Mixing prose and pseudocode in one block.** A `construction` either reads as structured pseudocode (preferred) or as prose; do not interleave indented bullets with paragraphs of motivation. Motivation goes outside the block.
2. **Implicit sampling.** `r ∈ ℤ_p` does not mean `r ←$ ℤ_p`. Use `←$` for sampling, `:=` for definition, `←` for assignment.
3. **Implicit broadcast.** "All parties learn `R`" is ambiguous. Say "broadcast `R` over the broadcast channel `F_BC`" or "send `R` to all parties over authenticated channels".
4. **Missing failure mode.** What happens if `t-1` parties send invalid shares? State it.
5. **Unnumbered constructions.** Use `\label{constr:...}` and `\cref` to refer back.

## Cross-skill notes

- For the surrounding theorem statement, see `theorem-statement-style.md`.
- For UC ideal-functionality boxes (`F`), see `proof-style-uc.md` — those are `figure` environments, not `construction`.
- For RFC-bound naming inside the construction (DSTs, ciphersuite labels), see `ciphersuite-naming.md`.
