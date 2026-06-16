# Voice-capture audit — adversarial

Audit ID: voice-capture-2026-06-15
Stance: hostile; thesis under test = "this is slop, the corpus is decorative, the system
cannot generate Hoskinson's voice."

## Verdict: GENUINE (slop thesis disproven), two low-severity fixes applied

The corpus is real, verifiable, and load-bearing — not decorative.

## Corpus authenticity — VERIFIED

All 57 `index.json` entries appear verbatim (whitespace/case-normalized substring) in the
`transcripts/<video_id>.md` they cite. 57/57, zero fabricated. Six hand cross-checks:

- `hoskinson-ILglnEC0iqU-065` — "the sole reason why I still am in the blockchain industry … the basis of our cryptocurrency Cardano is the scientific method" — MATCH
- `hoskinson-9d3bp33AJFk-036` — "imagine if the US government's assets were digital … lock the US government's money" — MATCH
- `hoskinson-fqrAzBAi64c-069` — "the world's strongest envelope … the corresponding private key" — MATCH
- `hoskinson-uZgDxPCXgPo-012` — "economic identity that is portable. Fluid … connecting tissue" — MATCH
- `hoskinson-0QtQGzqAIiU-000` — "you never play chess with a pigeon …" — MATCH
- `hoskinson--IBwDvxMnBc-036` — "the first formally verified ethereum classic client …" — MATCH

Transcripts read as genuine auto-captions: filler, mis-transcriptions ("Charles Hodgkinson",
"growth Indique" for Grothendieck), the "always warm always sunny sometimes colorado"
catchphrase, real Cardano/ETC/governance content.

## Voice fidelity

- **Sample A (pure Hoskinson):** his voice. Reproduces specific corpus moves — signature open
  (P2sNyAZLLqg-000), change-without-consent-erodes-trust (w2bhIQdzeI4-021), walk-before-you-run
  (zhFTO1jYjbk-060), "world financial operating system" (w2bhIQdzeI4-021). Original draft had
  generic filler ("airplanes/nuclear reactors", "billion people"); replaced with corpus-grounded
  phrasing after the audit (ISS-1, fixed).
- **Sample B (triadic fusion):** real, separable blend — Hoskinson open ("I'll show you, not
  just assert it") → Feynman develop (27×453 rederivation + bet/referee intuition pump, matching
  the guide) → Russell close ("reduces to one sentence … Everything else is commentary"). No
  voice dominates or vanishes.
- **Controls:** three measurably distinct voices (Russell syllogism / Feynman sustained intuition
  pump / Hoskinson candor+combat).

## Independent generation test

The auditor wrote its own pure-Hoskinson sample grounded only in cited transcript moves, and
confirmed the corpus materially changed the output vs. generic-Hoskinson memory: it supplied the
exact "sometimes Colorado" tail, the near-verbatim "change a system without consent → hurt trust"
framing (w2bhIQdzeI4-021), and the "works → something you can trust with your money" move
(fqrAzBAi64c). Without the corpus the auditor would have reached for the same generic filler that
leaked into Sample A's first draft. Corpus is load-bearing.

## Discipline floor

russellian-style linters run live against the samples: low passive-voice counts; the only
hedge/signal-density flags are his authentic tics ("sometimes" in the catchphrase, candor modals
like "could've"). Samples clear the floor.

## Findings

- **ISS-1 (low, fixed):** Sample A generic filler not traceable to the corpus → replaced with
  corpus-grounded phrasing.
- **ISS-2 (low, fixed):** samples doc oversold an automated "generator" that does not exist →
  reworded to state the samples are hand-authored against the corpus + guide; automated prose
  generation is future work.
- **ISS-3 (info, open):** the discipline linters flag his genuine catchphrase/candor tics. A
  voice-aware allowlist would stop the floor penalizing the very tics that make it his voice.
- **ISS-4 (info, open):** corpus skews 2020-era governance/Shelley/whiteboard register; broaden
  eras for wider range.

corrections.json (machine-readable) is recorded in the run log; ISS-1 and ISS-2 are resolved in
`2026-06-15-voice-generation-samples.md`.
