export const meta = {
  name: 'qa-halmos-review',
  description: 'Review the halmos skill across 4 dimensions, adversarially verify findings, return report data',
  phases: [
    { title: 'Review', detail: '4 read-only dimension reviewers in parallel' },
    { title: 'Verify', detail: 'refute-by-default skeptic per critical/important finding' },
    { title: 'Synth', detail: 'dedup + severity bucket -> report data' },
  ],
}

const FINDINGS_SCHEMA = {
  type: 'object',
  required: ['dimension', 'summary', 'findings'],
  properties: {
    dimension: { type: 'string' },
    summary: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'title', 'severity', 'location', 'claim', 'evidence', 'suggested_fix'],
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          severity: { type: 'string', enum: ['critical', 'important', 'minor'] },
          location: { type: 'string' },
          claim: { type: 'string' },
          evidence: { type: 'string' },
          suggested_fix: { type: 'string' },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['finding_id', 'verdict', 'reasoning', 'corrected_severity'],
  properties: {
    finding_id: { type: 'string' },
    verdict: { type: 'string', enum: ['real', 'partial', 'refuted'] },
    reasoning: { type: 'string' },
    corrected_severity: { type: 'string', enum: ['critical', 'important', 'minor'] },
  },
}

const ROOT = 'C:/russellian-book-suite'

const REVIEWERS = [
  {
    key: 'code',
    files: [
      `${ROOT}/skills/halmos/scripts/concept_ledger.py`,
      `${ROOT}/skills/halmos/scripts/build_linkage.py`,
      `${ROOT}/skills/halmos/scripts/dispatch_halmos_review.py`,
      `${ROOT}/skills/halmos/scripts/aggregate_halmos.py`,
      `${ROOT}/skills/halmos/scripts/conductor.py`,
      `${ROOT}/skills/halmos/skill_api.py`,
    ],
    brief: [
      'Review these Python modules for correctness and robustness. Concrete things to check:',
      '- _chapter_n parsing: off-by-one, ids that are not "ch-NN", non-numeric suffixes.',
      '- _norm / _slug: distinct concepts colliding to the same slug; empty or punctuation-only inputs.',
      '- rollup._key in aggregate_halmos.py: does the (check, concept|prior_chapter|detail) fallback ever wrongly merge or wrongly split findings?',
      '- harvest_title_case in concept_ledger.py: the regex and _ARTICLES stripping; what does it do with ALL-CAPS, hyphenated, or footnote-title text?',
      '- file IO: missing files, malformed JSON, encoding; are exceptions handled or do they crash the conductor?',
      'Report only defects you can point at in the code. Each finding needs a file:line location and the exact code as evidence.',
    ].join('\n'),
  },
  {
    key: 'doctrine',
    files: [
      `${ROOT}/skills/halmos/references/halmos-doctrine.md`,
      `${ROOT}/skills/halmos/references/seed-concepts.txt`,
    ],
    brief: [
      'Review the reviewer doctrine and seed concepts for fidelity and efficacy.',
      '- Is the doctrine faithful to Paul Halmos spiral-exposition method (concepts reintroduced and deepened, not just cross-referenced)?',
      '- Are the seven checks (orphan-reference, broken-handoff, continuity-gap, missed-recall, spiral-stall, terminology-drift, premature-definition) complete and non-overlapping? Is severity calibrated?',
      '- Two known limitations to assess head-on: (a) footnote-title noise in concept harvesting, e.g. "Safety Gridworlds" / "Existential Risk" captured as concepts; (b) introduced_in = earliest mention marks ch-01 for devices ch-1 only previews, not defines.',
      '- Seam-overlap stopword tuning: could the function-word stoplist produce a false "clean" seam (overlap that is all filler) or a false "broken" seam?',
      'Each finding needs a location (file plus heading or line) and a quote as evidence.',
    ].join('\n'),
  },
  {
    key: 'tests',
    files: [
      `${ROOT}/skills/halmos/tests/test_concept_ledger.py`,
      `${ROOT}/skills/halmos/tests/test_build_linkage.py`,
      `${ROOT}/skills/halmos/tests/test_aggregate_halmos.py`,
      `${ROOT}/skills/halmos/tests/test_conductor_integration.py`,
      `${ROOT}/skills/book-compose/tests/test_halmos_gate.py`,
    ],
    brief: [
      'Review the tests for rigor and coverage.',
      '- Do tests exercise real behavior or only happy paths? Which branches in the scripts are untested?',
      '- Brittle assertions (exact-string matches that will break on benign change), over-mocking, or tests that would pass even if the code were wrong.',
      '- Missing regressions for the known edge cases: title-case article stripping, target-less duplicate findings in rollup, the gate mtime sentinel (verdict older than draft -> 999).',
      '- Is test_halmos_gate.py actually asserting the gate blocks when the count is non-zero, not just when it is zero?',
      'Each finding names the test (file::test_name) and what is missing or wrong.',
    ].join('\n'),
  },
  {
    key: 'fidelity',
    files: [
      `${ROOT}/skills/halmos/SKILL.md`,
      `${ROOT}/skills/halmos/README.md`,
      `${ROOT}/docs/superpowers/specs/2026-06-01-halmos-skill-design.md`,
      `${ROOT}/docs/superpowers/plans/2026-06-01-halmos-skill.md`,
      `${ROOT}/skills/book-compose/scripts/chapter_contract_check.py`,
    ],
    brief: [
      'Review the built skill against its spec and plan, plus docs and integration.',
      '- Were the two plan defects fully resolved: (1) Title-Case regex capturing a leading article ("The Authority Airgap"), (2) the deterministic forward-reference check that is logically impossible and was reassigned to the agent layer?',
      '- Does SKILL.md / README accurately describe what the scripts do? Any drift between documented and actual public surface (skill_api.py)?',
      '- AI-slop in the docs (antithesis cadence, rule-of-three, "this skill", empty significance claims).',
      '- Integration: in chapter_contract_check.py, is halmos_critical_count wired so an absent or stale verdict cannot silently satisfy the == 0 gate?',
      'Each finding cites file plus line or heading.',
    ].join('\n'),
  },
]

const REVIEW_PREAMBLE = [
  'You are a QA reviewer for the "halmos" skill (a chapter-linkage reviewer for a book pipeline).',
  'Read ONLY the files listed below, in full, then report defects in your assigned dimension.',
  'Be concrete and skeptical. Do not invent issues to seem thorough; a short, true report beats a long, padded one.',
  'Do not propose unrelated refactors. Severity: critical = wrong output or a broken gate; important = real bug or real gap that bites in normal use; minor = style, clarity, nit.',
  'Return the FINDINGS object. Give each finding a stable id like "<dimension>-1".',
].join('\n')

function reviewerPrompt(r) {
  const fileList = r.files.map((f) => '- ' + f).join('\n')
  return `${REVIEW_PREAMBLE}\n\nDimension: ${r.key}\n\nFiles to read:\n${fileList}\n\n${r.brief}`
}

function skepticPrompt(f, dimension) {
  return [
    'You are an adversarial verifier. A QA reviewer raised the finding below about the halmos skill.',
    'Your job is to REFUTE it. Read the cited location yourself and decide whether the claim actually holds.',
    'Default to "refuted" if you are not sure, or if the claim is subjective taste rather than a defect.',
    'Use "partial" only when a real but narrower or lower-severity issue survives.',
    '',
    `Dimension: ${dimension}`,
    `Finding id: ${f.id}`,
    `Title: ${f.title}`,
    `Severity claimed: ${f.severity}`,
    `Location: ${f.location}`,
    `Claim: ${f.claim}`,
    `Evidence given: ${f.evidence}`,
    `Suggested fix: ${f.suggested_fix}`,
    '',
    'Read the file at that location and return the VERDICT object. corrected_severity is your judgment, not the reviewer claim.',
  ].join('\n')
}

// Verify one dimension's findings: critical/important get a skeptic; minor pass through unverified.
async function verifyDimension(findings, reviewer) {
  const dim = reviewer.key
  const gating = findings.findings.filter((f) => f.severity === 'critical' || f.severity === 'important')
  const minor = findings.findings.filter((f) => f.severity === 'minor')
  const verdicts = await parallel(
    gating.map((f) => () =>
      agent(skepticPrompt(f, dim), { label: `verify:${f.id}`, phase: 'Verify', schema: VERDICT_SCHEMA }).then((v) => ({
        ...f,
        dimension: dim,
        verdict: v.verdict,
        corrected_severity: v.corrected_severity,
        verify_reasoning: v.reasoning,
      }))
    )
  )
  const minorPass = minor.map((f) => ({
    ...f,
    dimension: dim,
    verdict: 'unverified',
    corrected_severity: f.severity,
    verify_reasoning: '',
  }))
  return { dimension: dim, summary: findings.summary, findings: [...verdicts.filter(Boolean), ...minorPass] }
}

function dedupeKey(f) {
  const loc = (f.location || '').split(':')[0].trim().toLowerCase()
  return `${loc}|${(f.title || '').trim().toLowerCase()}`
}

function synthesize(perDimension) {
  const all = perDimension.flatMap((d) => d.findings)
  const kept = all.filter((f) => f.verdict !== 'refuted')
  const refuted = all.filter((f) => f.verdict === 'refuted')
  const seen = new Map()
  for (const f of kept) {
    const k = dedupeKey(f)
    if (!seen.has(k)) seen.set(k, f)
  }
  const survivors = [...seen.values()]
  const order = { critical: 0, important: 1, minor: 2 }
  survivors.sort((a, b) => (order[a.corrected_severity] ?? 3) - (order[b.corrected_severity] ?? 3))
  return { survivors, refuted }
}

function reportMarkdown({ survivors, refuted }) {
  const lines = ['# Halmos QA review', '']
  const buckets = ['critical', 'important', 'minor']
  for (const sev of buckets) {
    const items = survivors.filter((f) => f.corrected_severity === sev)
    if (!items.length) continue
    lines.push(`## ${sev}`, '')
    for (const f of items) {
      lines.push(`### ${f.title}  \`[${f.dimension}]\``)
      lines.push(`- Location: ${f.location}`)
      lines.push(`- Problem: ${f.claim}`)
      lines.push(`- Evidence: ${f.evidence}`)
      lines.push(`- Fix: ${f.suggested_fix}`)
      lines.push('')
    }
  }
  if (refuted.length) {
    lines.push('## Refuted (raised, dismissed on verification)', '')
    for (const f of refuted) {
      lines.push(`- **${f.title}** \`[${f.dimension}]\` — ${f.verify_reasoning || 'refuted'}`)
    }
    lines.push('')
  }
  return lines.join('\n')
}

phase('Review')
const perDimension = await pipeline(
  REVIEWERS,
  (r) => agent(reviewerPrompt(r), { label: `review:${r.key}`, phase: 'Review', schema: FINDINGS_SCHEMA }),
  (findings, r) => verifyDimension(findings, r)
)

phase('Synth')
const valid = perDimension.filter(Boolean)
const { survivors, refuted } = synthesize(valid)
log(
  `survivors: ${survivors.length} (crit ${survivors.filter((f) => f.corrected_severity === 'critical').length}, imp ${survivors.filter((f) => f.corrected_severity === 'important').length}, minor ${survivors.filter((f) => f.corrected_severity === 'minor').length}); refuted: ${refuted.length}`
)

return { survivors, refuted, report_md: reportMarkdown({ survivors, refuted }) }
