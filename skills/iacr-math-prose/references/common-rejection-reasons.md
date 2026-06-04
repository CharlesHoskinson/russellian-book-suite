# Common rejection reasons

A catalogue of failure modes that IACR program-committee reviewers consistently call out in Crypto, Eurocrypt, Asiacrypt, TCC, PKC, CHES, FSE, and ePrint submissions. Each entry lists the failure, why reviewers reject it, and the corrective action.

This is a surface read. Use it as a final-pass checklist before submission and as a triage tool when re-reading a rejected paper.

## R1 — Informal ideal functionality

**Failure.** A UC theorem with `F` defined in prose, not as a labelled box.

**Why rejected.** The IDEAL world is the specification. A prose `F` is ambiguous on input handling, output handling, adversary interface, and corruption side effects. Reviewers cannot verify the simulator without a formal `F`.

**Fix.** Use a `figure` environment with a framed box containing `Inputs`, `Outputs`, `Internal state`, and any side conditions (adversarial influence, scheduling). See `proof-style-uc.md` for the canonical layout.

## R2 — Vague probability bound

**Failure.** `Pr[A wins] ≈ ε` or `Pr[A wins] ≲ ε` or "the probability is roughly `ε`".

**Why rejected.** `≈` is not a proof obligation. Reviewers cannot check the inequality.

**Fix.** Use `≤` exclusively. State the inequality concretely: `Pr[A wins] ≤ ε(λ) + negl(λ)` with `ε` defined and `negl` defined.

## R3 — Missing query bound

**Failure.** A concrete-security claim that omits the query budget. `Adv ≤ ε` without `q_S`, `q_H`, `q_D`, `q_E`.

**Why rejected.** A bound without queries is uninstantiable. A deployment cannot pick parameters.

**Fix.** Carry `q_S`, `q_H`, `q_D` etc. through every step of every reduction. State them in the theorem statement.

## R4 — Symbol reuse

**Failure.** The same symbol used for distinct objects. `H` for both a hash function and a hypothesis space; `n` for both security parameter and number of parties; `p` for both prime modulus and probability.

**Why rejected.** A reader has to disambiguate per occurrence. Reviewers reject on first pass to avoid wasting time.

**Fix.** One symbol, one meaning, per paper. Build a notation table if the symbol budget is tight. See `notation-discipline.md` §7.

## R5 — Unspecified security model

**Failure.** "The scheme is secure" without specifying CPA, CCA1, CCA2, EUF-CMA, sUF-CMA, IND-sID-CCA, MU-EUF-CMA, etc.

**Why rejected.** The proof obligation is undefined.

**Fix.** Name the model precisely in every theorem statement. See `theorem-statement-style.md` §"Anti-pattern 2" for the canonical list.

## R6 — Random oracle without domain/range

**Failure.** "Let `H` be a random oracle." No domain. No range.

**Why rejected.** The simulator's programming strategy depends on `H`'s domain and range. Without them the simulator's runtime cannot be analysed.

**Fix.** State `H: D → R` at first use, with `D` and `R` typed concretely (`{0,1}^*`, `G`, `ℤ_p`, `{0,1}^{2λ}`, etc.).

## R7 — Informal-then-formal duplication

**Failure.** Two versions of the same theorem (one prose, one symbolic) with no marker of which is the official claim.

**Why rejected.** Reviewers do not know which version they must check.

**Fix.** State the formal version once, inside `\begin{theorem}`. If a motivational prose version is useful, place it in the surrounding paragraph and explicitly mark it as motivation ("Informally, …") — it must not be a numbered claim.

## R8 — `\textbf` vs `\mathbf` drift

**Failure.** The same object styled differently across the paper. `\textbf{A}` in section 3 vs `\mathbf{A}` in section 5. Lower-case `a` for a vector in one place and `\vec{a}` in another.

**Why rejected.** Suggests the paper was assembled from multiple drafts without copy-editing. Reviewers infer broader sloppiness.

**Fix.** Declare a macro for each typographic role and use it everywhere: `\newcommand{\matr}[1]{\mathbf{#1}}`, `\newcommand{\vect}[1]{\mathbf{#1}}`, `\newcommand{\algo}[1]{\textsf{#1}}`.

## R9 — Constructions in inline prose

**Failure.** A protocol described in a paragraph instead of a numbered `\begin{construction}` block.

**Why rejected.** The construction cannot be cited (`\cref{constr:foo}`), cannot be visually located in the paper, and merges with surrounding analysis.

**Fix.** Wrap every concrete protocol or scheme in `\begin{construction}` with a label. See `iacrtrans-environments.md` §"construction" and `protocol-pseudocode.md`.

## R10 — Cite-by-prose

**Failure.** "See [12]" or "as in [7]" or "the technique of [3]". The citation is referenced as a footnote, not integrated into the sentence.

**Why rejected.** Bad scholarship. The reader must look up the reference to understand the sentence.

**Fix.** Integrate the citation: "Boneh and Franklin [12] showed that …"; "We use the forking lemma of Pointcheval and Stern [25, Theorem 3]"; "By Theorem 4 of [7]".

## R11 — Semantic line breaks in equations

**Failure.** A multi-line equation broken at the wrong point: `a + b` split between `+` and `b` instead of at `=` or `≤`.

**Why rejected.** Eye-tracking is broken. Reviewers re-read displayed equations multiple times; bad breaks cost time.

**Fix.** Break before relation symbols (`=`, `≤`, `≥`, `<`, `>`, `≡`). Use `align` with `&` immediately before the relation. See `iacrtrans-environments.md` §"Equation environments".

## R12 — `\\ \\` as block separator

**Failure.** Two backslash-pairs to separate paragraphs inside a theorem or proof.

**Why rejected.** Forbidden by LaTeX best practice. Produces inconsistent spacing across columns and page widths.

**Fix.** Use `\medskip` for a small gap, `\bigskip` for a large gap, `\paragraph{Name.}` for a labelled sub-block.

## R13 — Forking lemma without citation

**Failure.** A signature security proof that invokes the forking lemma without citing Pointcheval–Stern.

**Why rejected.** The forking lemma is a load-bearing tool with subtle preconditions. The citation is mandatory for the reviewer to verify the preconditions are met.

**Fix.** Cite Pointcheval–Stern "Security Arguments for Digital Signatures and Blind Signatures" (Journal of Cryptology 13(3), 2000). For the general forking lemma, cite Bellare–Neven (CCS 2006).

## R14 — UC without corruption model

**Failure.** "Construction `M` UC-realises `F`" with no statement of static vs adaptive, semi-honest vs malicious.

**Why rejected.** UC results are not transferable across corruption models. The claim is incomplete.

**Fix.** State the model: "against a static, malicious PPT adversary corrupting up to `t-1` parties". See `proof-style-uc.md` §"Checklist".

## R15 — Quantum claim without QROM

**Failure.** "The scheme is post-quantum secure" with the proof in the classical random oracle model.

**Why rejected.** Classical ROM proofs do not transfer to quantum adversaries; the random oracle must be queryable in superposition. See Boneh–Dagdelen–Fischlin–Lehmann–Schaffner–Zhandry "Random Oracles in a Quantum World" (Asiacrypt 2011).

**Fix.** Either restate the result in the QROM and adjust the bound (often loses a factor of `q_H`), or restrict the claim to classical adversaries.

## R16 — Static vs adaptive corruption unstated

**Failure.** An MPC or threshold-signature theorem that does not specify the corruption schedule.

**Why rejected.** Adaptive corruption is strictly stronger than static. A static-secure scheme can be trivially broken by an adaptive adversary in some settings.

**Fix.** State the schedule explicitly. Adaptive corruption proofs typically require erasure assumptions or non-committing encryption — name the technique.

## R17 — Generic group bound dressed as standard model

**Failure.** A bound proven in the generic group model presented as if it were a standard-model bound.

**Why rejected.** Generic group bounds capture only generic algorithms; concrete attacks (e.g., index calculus, MOV reduction) can break the scheme without contradicting the GGM bound.

**Fix.** State the model: "in the generic group model" or "in the algebraic group model" (Fuchsbauer–Kiltz–Loss, Crypto 2018).

## R18 — Setup assumption not declared

**Failure.** A construction uses a CRS, common random string, or trusted setup without declaring it.

**Why rejected.** Setup assumptions are part of the security model. A NIZK in the URS model is different from a NIZK in the CRS model.

**Fix.** State the setup in the construction header and the theorem statement: "in the common reference string model" / "in the uniform random string model" / "in the bare public-key model".

## R19 — Equivocation without supporting structure

**Failure.** A UC simulator that "equivocates" a commitment to a chosen message, when the underlying commitment is binding.

**Why rejected.** Equivocation requires a trapdoor or mixed-mode structure. Plain IND-CPA encryption does not support it.

**Fix.** Use a trapdoor commitment, mixed commitment (Damgård–Nielsen, Crypto 2002), or equivocable commitment (Canetti–Fischlin, Crypto 2001). State the technique.

## R20 — Lossless / loose tightness conflation

**Failure.** A loose reduction (loss factor `q_S` or `q_H`) presented without acknowledging the loss; or a tight reduction claimed without proof.

**Why rejected.** Tightness affects deployable parameters by orders of magnitude. Misrepresenting tightness is a substantive error.

**Fix.** State the loss factor in the theorem. "The reduction is loose with factor `q_S`" or "The reduction is tight: `Adv_A ≤ 2 · Adv_B + 2^{-λ}`".

## R21 — Notation table missing for >40 symbols

**Failure.** A paper with extensive notation but no notation table.

**Why rejected.** Reviewers cannot keep 40+ symbols in working memory.

**Fix.** Include a notation table (or "notation guide") in §2 or as an appendix. List every symbol with its type and meaning.

## R22 — Pseudocode without sampling discipline

**Failure.** `r ∈ ℤ_p` used to mean "sample `r` uniformly". The `∈` is ambiguous (membership? sampling?).

**Why rejected.** Reviewers cannot distinguish sampling from assertion.

**Fix.** Use `←$` for uniform sampling, `←` for assignment, `:=` for definition, `=` for equality, `∈` only for membership tests.

## R23 — Proof ends without `\qed`

**Failure.** A proof block that terminates abruptly mid-paragraph with no `\qed`.

**Why rejected.** amsthm auto-inserts `\qed` only if the proof ends with a non-display line. A proof ending in a displayed equation needs `\qed` explicitly inside the display.

**Fix.** `\qed` immediately after the final displayed equation, e.g. `… \leq \negl(\lambda). \qed`.

## R24 — Theorem inside proof

**Failure.** A `\begin{theorem}` block nested inside a `\begin{proof}`.

**Why rejected.** Theorems are top-level claims of the paper. A claim used inside a proof is a lemma or a `\begin{claim}`.

**Fix.** Move the inner theorem out, or replace with `\begin{claim}` (un-numbered, in-proof).

## R25 — Hardness assumption uncited

**Failure.** "Under the q-SDH assumption" with no citation.

**Why rejected.** Hardness assumptions have specific definitions; q-SDH has variants. Without a citation the reviewer cannot verify the version.

**Fix.** Cite the original paper for the assumption. For q-SDH: Boneh–Boyen "Short Signatures Without Random Oracles" (Eurocrypt 2004). For LWE: Regev "On Lattices, Learning with Errors, Random Linear Codes, and Cryptography" (JACM 2009). For DDH: cite a textbook (Boneh–Shoup, "A Graduate Course in Applied Cryptography", §10.4).

## R26 — Side-channel claim without threat model

**Failure.** "The implementation is constant-time" without specifying the leakage model (cache, branch predictor, instruction timing, EM).

**Why rejected.** "Constant time" is ambiguous across hardware. Reviewers in CHES specifically demand the model.

**Fix.** State the leakage model: "constant-time in the value model (Almeida et al., USENIX Security 2016)" or "constant-time on x86_64 with no data-dependent memory access patterns".

## R27 — Multi-user security ignored

**Failure.** A deployable signature scheme proven only in the single-user model.

**Why rejected.** Real deployments serve many users; the security loss from `u` users can be `Θ(u)` in non-tight reductions.

**Fix.** State the multi-user bound, even if it is the trivial reduction with factor `u`. Cite Bader–Hofheinz–Jager–Kiltz–Li (Eurocrypt 2016) for tight multi-user reductions.

## R28 — Acronym overload

**Failure.** Acronyms introduced and used inconsistently. `EUF-CMA`, `EUF-CMA`, `euf-cma`, `eufcma` in the same paper.

**Why rejected.** Reviewers infer poor copy-editing. Reads as a draft, not a submission.

**Fix.** Pick one casing (`EUF-CMA` is standard). Use `\textsf{EUF-CMA}` or `\mathsf{EUF-CMA}` via a macro.

## R29 — Lemma chain unfaithful

**Failure.** A proof claims "by Lemma 3" but Lemma 3 has hypotheses unmet by the current context.

**Why rejected.** Substantive error; not merely a style issue.

**Fix.** Restate the lemma hypotheses where invoked, or rewrite Lemma 3 to be applicable. This is the highest-priority class of rejection — substantive errors override style.

## R30 — Game number drift

**Failure.** A game-based proof with `G_0, G_1, G_2, G_4, G_5` (missing `G_3`).

**Why rejected.** Suggests a game was deleted late and the numbering not re-flowed.

**Fix.** Re-number contiguously. Use `cleveref` labels (`\cref{game:g3}`) so re-numbering is one-touch.

## Pre-submission checklist

Run through R1–R30. If any item triggers, fix before submission. Items R1, R4, R5, R6, R10, R14, R18, R19, R29 are common single-pass rejection reasons; fix those first.

## See also

- `notation-discipline.md` — fixes R4, R6, R8, R22, R28.
- `theorem-statement-style.md` — fixes R5, R7, R14, R20.
- `proof-style-game-based.md` — fixes R23, R30.
- `proof-style-uc.md` — fixes R1, R14, R16, R19.
- `proof-style-concrete.md` — fixes R3, R15, R20, R27.
- `iacrtrans-environments.md` — fixes R8, R9, R11, R12, R23, R24.
- `ciphersuite-naming.md` — fixes R6 in deployed-scheme contexts.
- `protocol-pseudocode.md` — fixes R9, R22.
