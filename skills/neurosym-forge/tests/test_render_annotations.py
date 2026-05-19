"""Phase T renderer tests (REQ-PUB-041..046).

Exercises `skills/neurosym-forge/scripts/render_annotations.py`:
single + multiple + zero annotations, stale-span warn+skip,
defect-index grouping, see-also semantic-neighbours composition,
and the round-trip mark-count invariant.
"""
from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

import pytest

from scripts.render_annotations import (
    load_annotations,
    main,
    render_defect_index,
    render_html,
    render_to_out_dir,
)


def _ann(claim_id: str, span: tuple[int, int], severity: str = "hard",
         message: str = "", **extra) -> dict:
    out = {
        "claim_id": claim_id,
        "source_span": list(span),
        "severity": severity,
        "message": message,
        "defect_confidence": 0.5,
    }
    out.update(extra)
    return out


def test_marks_wrap_source_spans() -> None:
    """REQ-PUB-041: each annotation wraps exactly its source span
    in `<mark class="severity-X" title="...">`."""
    md = "The trial enrolled 42 patients with no adverse events."
    annotations = {
        "version": 1,
        "source_path": "src.md",
        "annotations": [
            _ann("c-001", (4, 9), severity="critical",
                 message="trial size below minimum"),
        ],
    }
    html = render_html(md, annotations)
    assert '<mark class="severity-critical"' in html
    assert 'title="trial size below minimum"' in html
    assert html.count("<mark") == 1
    # The wrapped text is the source slice [4, 9) == "trial".
    assert ">trial</mark>" in html


def test_multiple_annotations_produce_n_marks() -> None:
    """REQ-PUB-041: N non-overlapping annotations → N `<mark>` tags."""
    md = "alpha beta gamma delta"
    annotations = {
        "version": 1,
        "source_path": "src.md",
        "annotations": [
            _ann("c-1", (0, 5), severity="hard", message="first"),
            _ann("c-2", (6, 10), severity="soft", message="second"),
            _ann("c-3", (16, 21), severity="advisory", message="third"),
        ],
    }
    html = render_html(md, annotations)
    assert html.count("<mark") == 3
    assert 'class="severity-hard"' in html
    assert 'class="severity-soft"' in html
    assert 'class="severity-advisory"' in html


def test_no_annotations_yields_identity_render() -> None:
    """REQ-PUB-041 (identity case): zero annotations → escaped source,
    no marks. The renderer still HTML-escapes the source content."""
    md = 'a < b & c > "d"'
    annotations = {"version": 1, "source_path": "s.md", "annotations": []}
    html = render_html(md, annotations)
    assert "<mark" not in html
    # html.escape should turn the metacharacters into entities.
    assert "&lt;" in html and "&amp;" in html and "&gt;" in html
    assert "&quot;" in html or '"d"' not in html


def test_html_escaping_inside_marks() -> None:
    """REQ-PUB-041 (safety): user content inside a span is escaped
    so a manuscript can't smuggle markup through the renderer."""
    md = "the <script>bad</script> here"
    annotations = {
        "version": 1, "source_path": "s.md",
        "annotations": [
            _ann("c-1", (4, 24), message="malicious tag"),
        ],
    }
    html = render_html(md, annotations)
    # Wrapped text is escaped — no raw `<script>` slips through.
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_stale_span_warns_and_skips() -> None:
    """REQ-PUB-043: out-of-bounds spans emit a warning and skip
    that annotation while continuing to render the rest."""
    md = "short text"
    annotations = {
        "version": 1, "source_path": "s.md",
        "annotations": [
            _ann("c-valid", (0, 5), message="ok"),
            _ann("c-out-of-bounds", (1000, 2000), message="off the end"),
            _ann("c-degenerate", (5, 5), message="empty"),
        ],
    }
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        html = render_html(md, annotations)
    msgs = [str(w.message) for w in caught]
    # The valid annotation rendered as a mark; the two stale ones
    # got warnings and were skipped.
    assert html.count("<mark") == 1
    assert any("c-out-of-bounds" in m for m in msgs)
    assert any("c-degenerate" in m for m in msgs)


def test_stale_span_whitespace_only_warns() -> None:
    """REQ-PUB-043: a span landing on whitespace-only text is also
    treated as stale (heuristic: 'fell into whitespace after edit')."""
    md = "abc   def"
    annotations = {
        "version": 1, "source_path": "s.md",
        "annotations": [
            _ann("c-ws", (3, 6), message="whitespace"),
        ],
    }
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        html = render_html(md, annotations)
    assert html.count("<mark") == 0
    assert any("c-ws" in str(w.message) for w in caught)


def test_overlapping_spans_nest() -> None:
    """REQ-PUB-041: overlapping spans render as nested marks
    (inner span wins for tooltip per design)."""
    md = "alphabetagamma"
    annotations = {
        "version": 1, "source_path": "s.md",
        "annotations": [
            _ann("outer", (0, 14), severity="soft", message="big"),
            _ann("inner", (5, 9), severity="hard", message="small"),
        ],
    }
    html = render_html(md, annotations)
    assert html.count("<mark") == 2
    assert html.count("</mark>") == 2
    # The hard mark should appear after the soft open tag.
    soft_idx = html.find('class="severity-soft"')
    hard_idx = html.find('class="severity-hard"')
    assert 0 <= soft_idx < hard_idx


def test_defect_index_groups_by_severity(tmp_path: Path) -> None:
    """REQ-PUB-042: defect-index.html groups defects by severity and
    each entry links to the in-context anchor in the annotated HTML.
    Advisories live in their own section beneath the main defects."""
    annotations = {
        "version": 1, "source_path": "s.md",
        "annotations": [
            _ann("c-h1", (0, 5), severity="hard", message="h1 msg"),
            _ann("c-h2", (6, 10), severity="hard", message="h2 msg"),
            _ann("c-s1", (11, 14), severity="soft", message="s1 msg"),
            _ann("c-a1", (15, 19), severity="advisory", message="a1 msg"),
        ],
    }
    index_html = render_defect_index(
        annotations, annotated_html_path="m-annotated.html",
        verdict_confidence=0.78,
    )
    assert "Verdict confidence: 0.78" in index_html
    assert index_html.count('<section class="severity-group') == 3
    assert "c-h1" in index_html and "c-h2" in index_html
    assert "m-annotated.html#defect-c-h1" in index_html
    # Advisories rendered last.
    advisory_idx = index_html.find("severity-advisory")
    hard_idx = index_html.find("severity-hard")
    soft_idx = index_html.find("severity-soft")
    assert hard_idx < advisory_idx
    assert soft_idx < advisory_idx


def test_see_also_links_emitted_when_semantic_neighbours_enabled() -> None:
    """REQ-PUB-045: WHERE `see_also` is present on the annotation
    (Phase Q's `:semantic-neighbours`), the defect-index emits a
    "See also" link cluster pointing at the similar claims."""
    annotations = {
        "version": 1, "source_path": "s.md",
        "annotations": [
            _ann("c-001", (0, 5), severity="hard", message="primary",
                 see_also=["c-100", "c-101", "c-102"]),
        ],
    }
    index_html = render_defect_index(
        annotations, annotated_html_path="m-annotated.html",
    )
    assert "See also:" in index_html
    assert "m-annotated.html#defect-c-100" in index_html
    assert "m-annotated.html#defect-c-101" in index_html
    assert "m-annotated.html#defect-c-102" in index_html


def test_see_also_omitted_when_semantic_neighbours_absent() -> None:
    """REQ-PUB-045 (no Phase Q): without `see_also` the renderer
    omits the cluster entirely."""
    annotations = {
        "version": 1, "source_path": "s.md",
        "annotations": [
            _ann("c-only", (0, 5), severity="hard", message="lone"),
        ],
    }
    index_html = render_defect_index(
        annotations, annotated_html_path="m-annotated.html",
    )
    assert "See also" not in index_html


def test_load_annotations_handles_unknown_version(tmp_path: Path) -> None:
    """REQ-PUB-040: unexpected schema version warns but returns the
    payload so we don't hard-fail on minor schema drift."""
    p = tmp_path / "ann.json"
    p.write_text(json.dumps({"version": 9, "annotations": []}),
                 encoding="utf-8")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        data = load_annotations(p)
    assert data["version"] == 9
    assert any("version" in str(w.message).lower() for w in caught)


def test_render_to_out_dir_emits_both_files(tmp_path: Path) -> None:
    """REQ-PUB-042 + REQ-PUB-044: render_to_out_dir produces both
    `<stem>-annotated.html` and `defect-index.html`."""
    src = tmp_path / "manuscript.md"
    src.write_text("alpha beta gamma", encoding="utf-8")
    ann = tmp_path / "manuscript-annotations.json"
    ann.write_text(json.dumps({
        "version": 1, "source_path": str(src),
        "annotations": [
            {"claim_id": "c-1", "source_span": [0, 5],
             "severity": "hard", "message": "msg",
             "defect_confidence": 0.5},
        ],
    }), encoding="utf-8")
    out_dir = tmp_path / "render"
    annotated, index = render_to_out_dir(src, ann, out_dir)
    assert annotated.exists()
    assert index.exists()
    assert annotated.name == "manuscript-annotated.html"
    assert index.name == "defect-index.html"
    annotated_text = annotated.read_text(encoding="utf-8")
    assert "<mark" in annotated_text
    index_text = index.read_text(encoding="utf-8")
    assert "c-1" in index_text


def test_sha256_mismatch_warns_once(tmp_path: Path) -> None:
    """REQ-PUB-043: when the source's sha256 doesn't match the
    annotations' recorded hash, emit a summary warning."""
    src = tmp_path / "m.md"
    src.write_text("EDITED text here", encoding="utf-8")
    ann = tmp_path / "ann.json"
    ann.write_text(json.dumps({
        "version": 1, "source_path": str(src),
        "source_sha256": hashlib.sha256(b"different bytes").hexdigest(),
        "annotations": [
            {"claim_id": "c-1", "source_span": [0, 6],
             "severity": "hard", "message": "m",
             "defect_confidence": 0.5},
        ],
    }), encoding="utf-8")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        render_to_out_dir(src, ann, tmp_path / "render")
    msgs = [str(w.message) for w in caught]
    assert any("sha256 mismatch" in m for m in msgs)


def test_round_trip_mark_count_equals_defect_count(tmp_path: Path) -> None:
    """REQ-PUB-046: round-trip — fixture markdown + verdict-shaped
    annotations → render produces `<mark>` count == defect count."""
    src = tmp_path / "m.md"
    src.write_text(
        "The first claim is here. The second is later. "
        "And a third tucked on.",
        encoding="utf-8",
    )
    annotations = {
        "version": 1, "source_path": str(src),
        "annotations": [
            _ann("c-1", (4, 9), severity="hard", message="m1"),
            _ann("c-2", (29, 35), severity="soft", message="m2"),
            _ann("c-3", (52, 57), severity="advisory", message="m3"),
        ],
    }
    html = render_html(src.read_text(encoding="utf-8"), annotations)
    assert html.count("<mark") == len(annotations["annotations"])


def test_cli_main_writes_outputs(tmp_path: Path) -> None:
    """REQ-PUB-044: `main(argv)` with --source, --annotations, --out-dir
    writes both annotated.html and defect-index.html."""
    src = tmp_path / "doc.md"
    src.write_text("alpha beta", encoding="utf-8")
    ann = tmp_path / "ann.json"
    ann.write_text(json.dumps({
        "version": 1, "source_path": str(src),
        "annotations": [
            {"claim_id": "c-1", "source_span": [0, 5],
             "severity": "hard", "message": "m",
             "defect_confidence": 0.5},
        ],
    }), encoding="utf-8")
    out_dir = tmp_path / "render"
    rc = main([
        "--source", str(src),
        "--annotations", str(ann),
        "--out-dir", str(out_dir),
    ])
    assert rc == 0
    assert (out_dir / "doc-annotated.html").exists()
    assert (out_dir / "defect-index.html").exists()


def test_cli_main_single_file_mode(tmp_path: Path) -> None:
    """REQ-PUB-044 single-file alternative: `--out path.html` instead
    of `--out-dir` writes a single annotated HTML and no index."""
    src = tmp_path / "doc.md"
    src.write_text("alpha beta", encoding="utf-8")
    ann = tmp_path / "ann.json"
    ann.write_text(json.dumps({
        "version": 1, "source_path": str(src), "annotations": [],
    }), encoding="utf-8")
    out = tmp_path / "single.html"
    rc = main([
        "--source", str(src),
        "--annotations", str(ann),
        "--out", str(out),
    ])
    assert rc == 0
    assert out.exists()
    assert not (tmp_path / "defect-index.html").exists()


def test_cli_main_rejects_conflicting_flags(tmp_path: Path) -> None:
    """REQ-PUB-044: --out and --out-dir cannot be combined."""
    src = tmp_path / "doc.md"
    src.write_text("x", encoding="utf-8")
    ann = tmp_path / "ann.json"
    ann.write_text(json.dumps({"version": 1, "annotations": []}),
                   encoding="utf-8")
    rc = main([
        "--source", str(src),
        "--annotations", str(ann),
        "--out", str(tmp_path / "a.html"),
        "--out-dir", str(tmp_path / "b"),
    ])
    assert rc != 0


def test_round_trip_stale_span_warns(tmp_path: Path) -> None:
    """REQ-PUB-046 stale-span variant: annotations were captured
    against an older manuscript that has since been truncated;
    out-of-range spans warn but unaffected spans still render."""
    src = tmp_path / "m.md"
    src.write_text("short", encoding="utf-8")
    annotations = {
        "version": 1, "source_path": str(src),
        "annotations": [
            _ann("c-keep", (0, 5), message="still ok"),
            _ann("c-lost", (100, 200), message="off the end"),
        ],
    }
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        html = render_html(src.read_text(encoding="utf-8"), annotations)
    assert html.count("<mark") == 1
    msgs = [str(w.message) for w in caught]
    assert any("c-lost" in m for m in msgs)
