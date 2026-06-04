import pytest

pytestmark = pytest.mark.windows_canary

from scripts.consolidate import main, parse_review, render_ledger


# A reject persona: ticks H=1 (strong reject), G=3 (good confidence), and
# carries two technical findings (C/Q3 + D/Q4) plus an editorial nit (E/Q5).
# Both technical findings cite "section 4.2" so they converge with persona 02.
PERSONA_01 = """\
# Persona 1: Game-based crypto — Review of EpochPoET v0.3

## A. Paper summary

The paper proposes a game-based proof of leader election for EpochPoET.

## B. Suitability

- [x] Yes

In scope for a crypto venue.

## C. Novelty, methodology, technical correctness

### Q3. Technical flaws

The reduction in section 4.2 loses a factor of q and the bound is therefore
vacuous for realistic adversaries.

## D. Technical details

### Q4. Missing details

The hybrid argument in section 4.2 omits the intermediate game definition, so
the hop cannot be verified.

## E. Editorial quality

### Q5. Editorial sufficiency

Symbol kappa is used in theorem 2 without definition; see line 88.

## G. Confidence

- [x] 3 Good

## H. Recommendation

- [x] 1 Strong reject

### Justification

The section 4.2 reduction is unsound.
"""

# A borderline persona: ticks H=3, G=2, with one technical finding that also
# cites "section 4.2" (drives cross-persona convergence) and one E-section nit.
PERSONA_02 = """\
# Persona 2: UC crypto — Review of EpochPoET v0.3

## A. Paper summary

A UC treatment of the same protocol.

## B. Suitability

- [x] Yes

## C. Novelty, methodology, technical correctness

### Q3. Technical flaws

The ideal functionality in section 4.2 leaks the leader before commitment.

## E. Editorial quality

### Q5. Editorial sufficiency

Figure 3 is referenced in section 5 but never appears.

## G. Confidence

- [x] 2 Medium

## H. Recommendation

- [x] 3 Borderline

### Justification

Fixable but the leakage in section 4.2 must be resolved.
"""

# An accept persona: ticks H=4, G=1. Its C-section body is a template
# placeholder (starts with "<"), so the parser must skip it and produce no
# findings for this persona.
PERSONA_03 = """\
# Persona 3: Concrete security — Review of EpochPoET v0.3

## A. Paper summary

Concrete parameter analysis.

## B. Suitability

- [x] Yes

## C. Novelty, methodology, technical correctness

### Q3. Technical flaws

<no technical flaws found>

## G. Confidence

- [x] 1 Weak

## H. Recommendation

- [x] 4 Accept

### Justification

Parameters check out.
"""


# The parser derives persona_index/slug from `stem.split("-", 2)`, so it reads
# a *plain* `persona-NN-slug.md` name (NN in parts[1]). The version-prefixed
# glob fallback is exercised separately via main() below.
_NAMES = {
    "persona-01-game-based-crypto.md": PERSONA_01,
    "persona-02-uc-crypto.md": PERSONA_02,
    "persona-03-concrete-security.md": PERSONA_03,
}


def _seed(reviews_dir, names=None):
    reviews_dir.mkdir(parents=True, exist_ok=True)
    for fname, body in (names or _NAMES).items():
        (reviews_dir / fname).write_text(body, encoding="utf-8")


def test_parse_review_extracts_recommendation_and_findings(tmp_path):
    p = tmp_path / "persona-01-game-based-crypto.md"
    p.write_text(PERSONA_01, encoding="utf-8")
    review = parse_review(p)

    assert review.persona_index == 1
    assert review.persona_slug == "game-based-crypto"
    assert review.recommendation == 1  # strong reject
    assert review.confidence == 3

    # C/Q3, D/Q4, E/Q5 each yield one finding; the placeholder-free bodies parse.
    categories = sorted(f.category for f in review.findings)
    assert categories == ["C/Q3", "D/Q4", "E/Q5"]

    # rec==1 forces strong-reject severity on the C and D findings; the E
    # finding is also strong-reject because rec==1 short-circuits before the
    # E->nit rule.
    by_cat = {f.category: f for f in review.findings}
    assert by_cat["C/Q3"].severity == "strong-reject"
    assert by_cat["C/Q3"].location == "section 4.2"
    # LOCATION_RE takes the first match in the body; "theorem 2" precedes
    # "line 88" in the E/Q5 text.
    assert by_cat["E/Q5"].location == "theorem 2"
    assert by_cat["C/Q3"].finding_id == "F-01-01"


def test_placeholder_bodies_are_skipped(tmp_path):
    p = tmp_path / "persona-03-concrete-security.md"
    p.write_text(PERSONA_03, encoding="utf-8")
    review = parse_review(p)
    assert review.recommendation == 4
    assert review.findings == []  # the only C-body is a "<...>" placeholder


def test_render_ledger_aggregates_distribution_and_convergence(tmp_path):
    _seed(tmp_path)
    reviews = [parse_review(tmp_path / name) for name in _NAMES]
    ledger = render_ledger(reviews, "EpochPoET", "v0.3", "2026-06-04")

    assert "# IACR Review Ledger - EpochPoET v0.3" in ledger
    assert "Personas reviewed: 3" in ledger
    # Distribution: one strong-reject, one borderline, one accept.
    assert "strong-reject 1" in ledger
    assert "borderline 1" in ledger
    assert "accept 1" in ledger
    # Median of {1, 3, 4} is 3 -> borderline.
    assert "Median recommendation: borderline" in ledger

    # section 4.2 is flagged by personas 01 and 02 -> convergence row present,
    # and the "no convergence" placeholder must be absent.
    assert "section 4.2" in ledger.split("## Cross-persona patterns", 1)[1]
    assert "_(no convergence detected)_" not in ledger

    # The strong-reject finding sorts to the top of the findings table.
    findings_block = ledger.split("## Findings", 1)[1].split("## Cross-persona", 1)[0]
    first_data_row = [
        ln for ln in findings_block.splitlines() if ln.startswith("| F-")
    ][0]
    assert "strong-reject" in first_data_row


def test_main_writes_ledger_to_output(tmp_path, capsys):
    reviews_dir = tmp_path / "reviews"
    _seed(reviews_dir)
    out = reviews_dir / "v0.3-review-ledger.md"

    rc = main(
        [
            "--reviews-dir",
            str(reviews_dir),
            "--paper",
            "EpochPoET",
            "--version",
            "v0.3",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    assert out.exists()

    ledger = out.read_text(encoding="utf-8")
    assert "IACR Review Ledger - EpochPoET v0.3" in ledger
    assert "Personas reviewed: 3" in ledger
    assert "| ID | Persona | Severity |" in ledger

    captured = capsys.readouterr()
    assert "personas: 3" in captured.out


def test_main_accepts_version_prefixed_filenames(tmp_path):
    # No plain `persona-*.md` exist; only version-prefixed names. main() must
    # fall through to the `*persona-*.md` glob and still produce a ledger.
    reviews_dir = tmp_path / "reviews"
    _seed(
        reviews_dir,
        names={f"v0.3-{name}": body for name, body in _NAMES.items()},
    )
    out = reviews_dir / "ledger.md"
    rc = main(["--reviews-dir", str(reviews_dir), "--output", str(out)])
    assert rc == 0
    assert "Personas reviewed: 3" in out.read_text(encoding="utf-8")


def test_main_returns_error_when_no_reviews(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    rc = main(
        ["--reviews-dir", str(empty), "--output", str(tmp_path / "out.md")]
    )
    assert rc == 1
