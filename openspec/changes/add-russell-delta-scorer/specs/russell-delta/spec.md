# Spec delta — russell-delta

Capability: `DELTA` (russell-delta)
Delta against `openspec/specs/russell-delta/spec.md` (new capability; all ADD).

## ADD REQ-DELTA-001 — Ubiquitous

The russellian-style skill shall provide a committed reference-profile asset at
`assets/russell-delta-profile.json` containing statistics only — the most-frequent-word
list, per-feature mean and standard deviation, the distribution of per-segment Burrows's
Delta to the author profile (`centroid_delta`: p10/p50/p90/max/mean), and provenance —
and no source prose.

## ADD REQ-DELTA-002 — Event-driven

When the profile builder runs over a set of local cleaned Russell text files, it shall
segment them into fixed-size word units (default 2500), compute the top-N (default 300)
most-frequent-word relative frequencies, and emit the profile asset deterministically
for fixed input.

## ADD REQ-DELTA-003 — Ubiquitous

The scorer shall compute a target document's Russell-Delta as classic Burrows's Delta —
the mean absolute z-score of the target's most-frequent-word relative frequencies
against the profile's per-feature mean and standard deviation.

## ADD REQ-DELTA-004 — Event-driven

When the scorer runs on a markdown file, it shall output JSON containing the delta, the
band (p10, p50, p90), a three-band verdict (within / at the edge of / outside Russell's
range, the outside cutoff being one inter-decile range past p90), the word count, and a
reliability flag.

## ADD REQ-DELTA-005 — Unwanted behaviour

If the target document is below the minimum reliable length (default 1000 words), then
the scorer shall still report the delta and shall set the reliability flag to false.

## ADD REQ-DELTA-006 — Ubiquitous

The scorer shall be deterministic and shall require no network access. The profile
builder shall be network-free; fetching of reference sources is a separate documented
step performed through scrapling-fetch.

## ADD REQ-DELTA-007 — Ubiquitous

The Russell-Delta score shall be advisory: it shall not gate, fail, or block the
pipeline.

## ADD REQ-DELTA-008 — Event-driven

When the style pass report dict is generated, it shall include an advisory
`russell_delta` entry stating the Russell-Delta score and verdict.

## ADD REQ-DELTA-009 — Ubiquitous

The reference corpus shall comprise the curated public-domain Russell prose works named
in the design doc and shall exclude symbol-dense works (Principia Mathematica), the
Project Gutenberg index, the Modern Essays anthology, and non-Russell texts.
