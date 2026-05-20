# iacrtrans / amsthm environments

The `iacrtrans` document class is the IACR's official LaTeX class, used by all IACR transactions (ToSC, TCHES, CiC) and accepted in conference submissions (Crypto, Eurocrypt, Asiacrypt, TCC, PKC). It inherits from `article`, loads `amsmath`, `amsthm`, `amssymb`, and is normally paired with `cleveref` and `mathtools`.

This reference fixes which environments to use for which content.

## Preamble baseline

```latex
\documentclass[fullversion,submission]{iacrtrans}
\usepackage{mathtools}     % loads amsmath, fixes amsmath bugs
\usepackage{amssymb}
\usepackage{cleveref}      % for \cref, \Cref
\usepackage[capitalize]{cleveref}

% Custom environments
\newtheorem{construction}{Construction}
\newtheorem{scheme}{Scheme}
\newtheorem{protocol}{Protocol}
\newtheorem{game}{Game}
\newtheorem{experiment}{Experiment}
\newtheorem{attack}{Attack}
\newtheorem*{remark*}{Remark}
\newtheorem*{observation}{Observation}
\newtheorem*{example*}{Example}

% Optional theorem-like
\newtheorem{fact}[theorem]{Fact}
\newtheorem{conjecture}[theorem]{Conjecture}
\newtheorem{claim}[theorem]{Claim}
```

The numbered `[theorem]` shared counter is the IACR convention. Theorems, lemmas, corollaries, propositions, facts, and conjectures all share one counter, so a reader scanning "Theorem 3" knows it is the third numbered claim of any type.

## Environment catalogue

### `definition`

For introducing new objects.

- Statement italicised by amsthm; body plain.
- Number the definition.
- Refer back as `\cref{def:foo}`.

```latex
\begin{definition}[EUF-CMA security]
\label{def:eufcma}
A signature scheme $\Sig = (\Setup, \Sign, \Verify)$ is \emph{existentially unforgeable under chosen-message attack (EUF-CMA)} if for every PPT adversary $A$, $\Adv^{\textsf{EUF-CMA}}_{\Sig, A}(\secparam) \leq \negl(\secparam)$, where the experiment is defined as follows. \ldots
\end{definition}
```

Use for: assumptions (DDH, q-SDH, LWE), security notions (EUF-CMA, IND-CCA), syntactic definitions of primitive interfaces.

Do NOT use for: numerical conventions ("let $p$ be a 256-bit prime") — those go in plain prose. Do not use for protocol descriptions — use `construction`.

### `theorem`, `lemma`, `corollary`, `proposition`

For claims.

- `theorem` — a main claim, expected to be a load-bearing result of the paper.
- `lemma` — a stepping-stone result used in a later proof.
- `corollary` — an immediate consequence of a theorem.
- `proposition` — an auxiliary result that is neither a load-bearing theorem nor purely instrumental.

IACR convention: most security claims are stated as `theorem`. Information-theoretic helpers (e.g., "the statistical distance between distributions `D_0` and `D_1` is bounded by `ε`") are `lemma`.

### `proof`

- Closes with `\qed` automatically. Do not type `\qed` yourself unless the proof ends mid-display.
- Optional name: `\begin{proof}[Proof of \cref{thm:foo}]`.
- For long proofs, use `\paragraph{Step 1: <name>.}` as a sub-block — never `\\ \\`.

### `remark`

For asides that are not part of the claim chain. Reviewers tolerate up to three or four `remark` blocks per section.

```latex
\begin{remark}
The bound in \cref{thm:main} is tight up to a factor of $\secparam$. We do not pursue this here.
\end{remark}
```

Do NOT use `remark` for: a key technical lemma (use `lemma`), a definition (use `definition`), or motivation paragraphs (use plain text).

### `construction`

Custom env declared via `\newtheorem{construction}{Construction}`. For protocol descriptions and concrete scheme instantiations.

```latex
\begin{construction}[EpochPoET signature, $\PoET_1$]
\label{constr:poet1}
\textbf{Setup}$(1^\secparam)$:
\begin{itemize}
  \item Sample $\sk \gets \KeyGen(1^\secparam)$.
  \item Output $\pk \gets \PubFromSec(\sk)$.
\end{itemize}
\textbf{Sign}$(\sk, m, \epoch)$:
\begin{itemize}
  \item Compute $\sigma \gets \VRF.\Eval(\sk, m \| \epoch)$.
  \item Output $\sigma$.
\end{itemize}
\textbf{Verify}$(\pk, m, \epoch, \sigma)$: \ldots
\end{construction}
```

Use for: every concrete protocol/scheme the paper introduces.

Do NOT use `construction` for: an abstract primitive interface (use `definition`).

### `scheme`, `protocol`

Same role as `construction`. Some sub-communities prefer `scheme` for non-interactive primitives (PKE, signatures) and `protocol` for interactive ones (OT, ZK, MPC). Pick one and stick to it.

### `game`, `experiment`

For pseudocode that defines an adversarial game.

```latex
\begin{game}[$\GameEUFCMA^A(\secparam)$]
\label{game:eufcma}
\begin{enumerate}
  \item $(\pk, \sk) \gets \Setup(1^\secparam)$.
  \item $(m^*, \sigma^*) \gets A^{\Sign(\sk, \cdot)}(\pk)$, with query set $Q$.
  \item Output $1$ iff $\Verify(\pk, m^*, \sigma^*) = 1$ and $m^* \notin Q$.
\end{enumerate}
\end{game}
```

`game` and `experiment` are interchangeable; pick one project-wide.

### `attack`

For describing an attack as a stand-alone object, typically in the related-work or motivation section. Rarely used; reviewers expect attacks in plain prose unless they form a load-bearing example.

### `fact`, `conjecture`, `claim`

- `fact` — folklore result cited without proof. Always paired with a citation.
- `conjecture` — open problem the paper does not resolve.
- `claim` — an in-proof assertion the proof itself then justifies. Lives inside a `proof` block.

```latex
\begin{proof}
\ldots
\begin{claim}
The probability of event $E$ is at most $q^2 / 2^\secparam$.
\end{claim}
\begin{proof}[Proof of claim]
\ldots
\end{proof}
\ldots
\end{proof}
```

Note: nested `proof` blocks render `\qed` for each. amsthm handles this correctly.

### `observation`, `example*`, `remark*`

The starred versions (un-numbered). Use sparingly. A reviewer scanning for results does not want to count un-numbered observations.

## Block separators

- `\medskip` — between major reasoning blocks.
- `\bigskip` — between sections of a long proof.
- `\paragraph{Name.}` — labelled sub-block, used heavily in game-based proofs ("Paragraph: Game G_1.").
- **Forbidden:** `\\ \\`, `\vspace{1em}`, `\\[1ex]\\[1ex]`.

## Equation environments

- `equation` — single numbered equation.
- `equation*` — single un-numbered equation.
- `align` / `align*` — multi-line, with `&` as alignment column.
- `aligned` — inside `equation` for multi-line that share one number.
- `gather` — multi-line with no alignment.

Forbidden: `eqnarray` (deprecated, broken spacing).

```latex
\begin{align}
\Pr[G_0 = 1]
  &\leq \Pr[G_1 = 1] + \varepsilon_1   \label{eq:g0g1} \\
  &\leq \Pr[G_2 = 1] + \varepsilon_1 + \varepsilon_2   \label{eq:g1g2} \\
  &\leq \Pr[G_3 = 1] + \sum_{i=1}^{3} \varepsilon_i.   \label{eq:g2g3}
\end{align}
```

Break at relations (`=`, `≤`, `≥`, `<`, `>`, `≡`) on the LEFT of the relation symbol. Never break mid-term.

## Referencing

Use `cleveref`. Never write "Theorem 3" by hand; the section may be reordered.

```latex
\cref{thm:main}                % "Theorem 3"
\Cref{thm:main}                % "Theorem 3" at sentence start
\cref{thm:main,lem:bound}      % "Theorem 3 and Lemma 4"
\cref{eq:g0g1}                 % "Equation (1)"
```

## Conventions specific to iacrtrans

- `[fullversion]` option for the long version posted to ePrint.
- `[submission]` option to anonymise; this strips author identity from the title block.
- `\keywords{...}` for the keyword list (mandatory in submission mode).
- IACR transactions issues use `[journal=tches]` or `[journal=tosc]` or `[journal=cic]`.

## When to NOT use an environment

If the content is one sentence of plain analytic prose, do not wrap it. Reviewers complain when paragraphs of motivation are wrapped in `remark` blocks. Use environments for content with logical status (definition, claim, scheme); use plain prose for connective tissue.

## Cross-reference to other skill files

- For protocol pseudocode inside `construction`, see `protocol-pseudocode.md`.
- For phrasing the statement inside `theorem`, see `theorem-statement-style.md`.
- For the proof body, see `proof-style-{game-based,uc,concrete}.md`.
