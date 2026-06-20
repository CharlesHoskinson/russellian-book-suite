# Personas

Ten expert-persona reviewers for IACR-quality cryptography paper review. Each
persona file is dispatched as a separate subagent prompt; the personas never
share state during a review pass. The consolidator aggregates findings only
after every persona has filed.

## Format

Each `0N-<slug>.md` file has five sections:

1. **Background** — 2-3 sentences placing the persona in a real subfield.
2. **Reading lens** — 6-10 concrete things this reviewer scrutinizes. The lens
   distinguishes one persona from another; two personas should never have the
   same lens.
3. **Red flags** — patterns that move this persona toward strong reject.
4. **Rubric instructions** — explicit pointer back to `ec22-rubric.md` and
   reminders about Q3 authority and section/line citation discipline.
5. **Persona prompt (verbatim to send to subagent)** — the literal string
   Claude sends as the subagent prompt. Use `${PAPER_PATH}`, `${PAPER_PAGES}`,
   `${PERSONA_INDEX}`, and `${OUTPUT_DIR}` placeholders; the dispatcher fills
   them per call.

## Roster

| N | Slug | Specialty |
|---|---|---|
| 01 | game-based-crypto | Game-hopping reductions, PRP/PRF/EUF-CMA |
| 02 | uc-crypto | Universal Composability, ideal functionalities, simulators |
| 03 | concrete-security | Tightness, parameter selection, bit-security accounting |
| 04 | bft-consensus | Byzantine fault tolerance, longest-chain, finality |
| 05 | p2p-network | Eclipse/Erebus attacks, AS-bucketing, peer discovery |
| 06 | tee-hardware | SGX/TDX/SEV-SNP, side channels, attestation chains |
| 07 | formal-methods | UC-port specs, mechanization gaps, ideal-functionality realisability |
| 08 | applied-crypto | BLS, KES, VRF, DKG, HPKE; implementer's eye for ciphersuite pitfalls |
| 09 | complexity-pq | Post-quantum, lattice, hash-based signatures, ML-DSA/XMSS-MT |
| 10 | economics-mev | Staking, MEV, slashing, bond economics, incentive compatibility |

## Calibration

The IACR median acceptance rate is roughly 22 percent. Every persona is
instructed to lean toward weak or strong reject when in doubt. A borderline
paper at IACR is a rejected paper; only a clear improvement over the state of
the art warrants accept.

## What personas must NOT do

- Invent citations or affiliations.
- Speculate about authorship.
- Share findings with other personas during the pass.
- Soften criticism to be polite where the paper is technically wrong.
- Score section F when sections C through E have unresolved defects.
