"""Phase T publication-bridge renderer (REQ-PUB-041..045).

Reads `manuscript-annotations.json` and the source markdown, then
produces an annotated HTML overlay in which each defect's source
span is wrapped in `<mark class="severity-{severity}" ...>`. When
`--out-dir` is given, also emits a `defect-index.html` summarising
every defect across the corpus with clickable jumps and, when
Phase Q's `:semantic-neighbours` is enabled, a "see also" cluster
per defect (REQ-PUB-042, REQ-PUB-045).

The renderer is deliberately tolerant of stale spans (REQ-PUB-043):
when the on-disk markdown's sha256 doesn't match the verdict's
recorded hash, or a `source_span` falls off the end of the file
or lands on whitespace, the affected annotation is skipped with a
`warnings.warn` to stderr and the rest of the annotations are
rendered as best they can be.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
import warnings
from pathlib import Path

# Phase Q's `:semantic-neighbours` is optional — the renderer
# composes with Phase T without forcing the dependency.
_RENDERER_VERSION = "neurosym-forge render_annotations 0.1.0"

_SEVERITY_CLASS_PREFIX = "severity-"

# Severities the renderer recognises and groups together in the
# defect-index. Unknown severities still produce a `<mark>` with
# their literal CSS class — they're just not separately grouped.
_KNOWN_SEVERITIES = ("hard", "soft", "advisory", "critical", "warning", "info")


def _is_stale_span(source: str, start: int, end: int) -> bool:
    """REQ-PUB-043: a span is stale if it falls out of bounds OR
    the captured substring contains no alphabetic characters
    (a heuristic for "the byte range fell into whitespace because
    the manuscript was edited after verification")."""
    if start < 0 or end > len(source) or start >= end:
        return True
    substr = source[start:end]
    return not any(ch.isalpha() for ch in substr)


def _wrap_annotation_html(text: str, ann: dict) -> str:
    """Wrap a single span of source text in a `<mark>` element.

    The text is `html.escape`d so user-supplied source content
    cannot inject markup. The `title` attribute carries the defect
    message for hover tooltips; `data-*` attributes carry the
    claim and defect ids for optional JS overlays without
    re-parsing the document.
    """
    severity = str(ann.get("severity", "advisory"))
    css_class = f"{_SEVERITY_CLASS_PREFIX}{severity}"
    title = ann.get("message", "") or ""
    claim_id = ann.get("claim_id", "") or ""
    defect_id = ann.get("defect_id", "") or ""
    constraint_id = ann.get("constraint_id", "") or ""
    attrs = [
        f'class="{html.escape(css_class, quote=True)}"',
        f'title="{html.escape(str(title), quote=True)}"',
        f'data-claim-id="{html.escape(str(claim_id), quote=True)}"',
    ]
    if defect_id:
        attrs.append(f'data-defect-id="{html.escape(str(defect_id), quote=True)}"')
    if constraint_id:
        attrs.append(
            f'data-constraint-id="{html.escape(str(constraint_id), quote=True)}"'
        )
    confidence = ann.get("defect_confidence")
    if confidence is not None:
        attrs.append(
            f'data-defect-confidence="{html.escape(str(confidence), quote=True)}"'
        )
    # Anchor id lets defect-index.html jump straight to the span.
    if claim_id:
        attrs.append(f'id="{html.escape(_anchor_id(claim_id), quote=True)}"')
    return f"<mark {' '.join(attrs)}>{html.escape(text)}</mark>"


def _anchor_id(claim_id: str) -> str:
    """Anchor id used for defect-index.html clickable jumps."""
    return f"defect-{claim_id}"


def render_html(source_md: str, annotations: dict) -> str:
    """REQ-PUB-041: wrap each annotation's source_span in
    `<mark class="severity-X" title="..." data-claim-id="...">`.

    Spans are byte ranges into the source markdown; multi-span
    overlap is handled by nested marks — the innermost mark wins
    for tooltip semantics because the browser's hit-test resolves
    to the deepest element. The output is the source with all
    non-span characters `html.escape`d and all span characters
    wrapped (and escaped) — i.e. a safe HTML fragment suitable
    for direct embedding in a `<body>`.

    REQ-PUB-043: stale spans (out of bounds or falling on
    whitespace-only ranges) are skipped with a warning rather
    than crashing the render.
    """
    anns = list(annotations.get("annotations", []) or [])
    # Filter out malformed / stale spans up front with a warning.
    valid: list[dict] = []
    for ann in anns:
        span = ann.get("source_span")
        if not (isinstance(span, (list, tuple)) and len(span) == 2):
            warnings.warn(
                f"render_annotations: skipping annotation "
                f"{ann.get('claim_id', '?')!r}: malformed source_span"
            )
            continue
        start, end = int(span[0]), int(span[1])
        if _is_stale_span(source_md, start, end):
            warnings.warn(
                f"render_annotations: skipping annotation "
                f"{ann.get('claim_id', '?')!r}: stale source_span "
                f"[{start}, {end}) (out of bounds or empty)"
            )
            continue
        valid.append({**ann, "_start": start, "_end": end})

    if not valid:
        # REQ-PUB-041 (identity render): no annotations → source is
        # html-escaped and returned verbatim.
        return html.escape(source_md)

    # Build an event stream of open/close boundaries so we can render
    # overlapping spans as nested `<mark>` elements (innermost wins
    # for tooltip per spec). Sort opens before closes at the same
    # offset so adjacent spans nest correctly.
    events: list[tuple[int, int, int, dict]] = []
    # (offset, kind, ann_index, ann); kind: 0 = open, 1 = close
    for i, ann in enumerate(valid):
        events.append((ann["_start"], 0, i, ann))
        events.append((ann["_end"], 1, i, ann))
    # Sort by offset; at the same offset close before open so a span
    # ending exactly where another starts doesn't nest spuriously.
    events.sort(key=lambda e: (e[0], -e[1]))  # close=1 sorts before open=0

    out: list[str] = []
    cursor = 0
    open_stack: list[dict] = []
    for offset, kind, _idx, ann in events:
        if offset > cursor:
            chunk = source_md[cursor:offset]
            out.append(html.escape(chunk))
            cursor = offset
        if kind == 0:
            # Open: emit `<mark ...>` tag.
            attrs_str = _open_mark_attrs(ann)
            out.append(f"<mark {attrs_str}>")
            open_stack.append(ann)
        else:
            # Close: emit `</mark>`. The nested ordering is correct
            # because EDGES_KEY sorted closes before opens at the
            # same offset and otherwise by ascending offset.
            out.append("</mark>")
            if open_stack:
                open_stack.pop()
    # Flush trailing source after the last event.
    if cursor < len(source_md):
        out.append(html.escape(source_md[cursor:]))
    return "".join(out)


def _open_mark_attrs(ann: dict) -> str:
    """Compute the `<mark>` open-tag attribute string for an
    annotation. Mirrors `_wrap_annotation_html` but separated so
    we can reuse it from the nested-span event emitter."""
    severity = str(ann.get("severity", "advisory"))
    css_class = f"{_SEVERITY_CLASS_PREFIX}{severity}"
    title = ann.get("message", "") or ""
    claim_id = ann.get("claim_id", "") or ""
    defect_id = ann.get("defect_id", "") or ""
    constraint_id = ann.get("constraint_id", "") or ""
    attrs = [
        f'class="{html.escape(css_class, quote=True)}"',
        f'title="{html.escape(str(title), quote=True)}"',
        f'data-claim-id="{html.escape(str(claim_id), quote=True)}"',
    ]
    if defect_id:
        attrs.append(f'data-defect-id="{html.escape(str(defect_id), quote=True)}"')
    if constraint_id:
        attrs.append(
            f'data-constraint-id="{html.escape(str(constraint_id), quote=True)}"'
        )
    confidence = ann.get("defect_confidence")
    if confidence is not None:
        attrs.append(
            f'data-defect-confidence="{html.escape(str(confidence), quote=True)}"'
        )
    if claim_id:
        attrs.append(f'id="{html.escape(_anchor_id(str(claim_id)), quote=True)}"')
    return " ".join(attrs)


_DEFAULT_CSS = """\
mark.severity-hard, mark.severity-critical {
  background-color: #fecaca;
  color: #7f1d1d;
}
mark.severity-soft, mark.severity-warning {
  background-color: #fef3c7;
  color: #78350f;
}
mark.severity-advisory, mark.severity-info {
  background-color: #e5e7eb;
  color: #1f2937;
}
"""


def _wrap_full_document(
    body_html: str, title: str, stylesheet: str | None = None,
) -> str:
    """Wrap the rendered fragment in a minimal full HTML5 document
    so the output stands alone in a browser. Uses the default CSS
    palette unless `stylesheet` is supplied."""
    if stylesheet is not None:
        style_block = (
            f'<link rel="stylesheet" href="{html.escape(stylesheet, quote=True)}">'
        )
    else:
        style_block = f"<style>{_DEFAULT_CSS}</style>"
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f"  <title>{html.escape(title)}</title>\n"
        f"  {style_block}\n"
        "</head>\n"
        "<body>\n"
        f'<pre class="manuscript">{body_html}</pre>\n'
        "</body>\n"
        "</html>\n"
    )


def render_defect_index(
    annotations: dict,
    annotated_html_path: str,
    verdict_confidence: float | None = None,
) -> str:
    """REQ-PUB-042: emit a `defect-index.html` body summarising every
    defect across the corpus, grouped by severity. Each entry is a
    clickable link to its in-context anchor in the annotated
    manuscript HTML at `annotated_html_path`.

    REQ-PUB-045: when Phase Q's `:semantic-neighbours` populated
    `see_also`, the index emits a "see also" cluster per defect
    pointing at the cited similar claims' in-document positions.
    """
    by_sev: dict[str, list[dict]] = {}
    advisories: list[dict] = []
    for ann in annotations.get("annotations", []) or []:
        sev = str(ann.get("severity", "advisory"))
        if sev == "advisory":
            advisories.append(ann)
        else:
            by_sev.setdefault(sev, []).append(ann)

    parts: list[str] = ['<section class="defect-index">']
    parts.append("<h1>Defect index</h1>")
    if verdict_confidence is not None:
        parts.append(
            f'<p class="verdict-confidence">Verdict confidence: '
            f"{html.escape(str(verdict_confidence))}</p>"
        )
    # Defect groups in a stable order: known severities first, then
    # any unknown severities alphabetically, then advisories last.
    ordered_known = [s for s in ("critical", "hard", "warning", "soft", "info")
                     if s in by_sev]
    ordered_extra = sorted(set(by_sev) - set(ordered_known))
    for sev in ordered_known + ordered_extra:
        parts.append(_render_index_section(sev, by_sev[sev], annotated_html_path))
    if advisories:
        parts.append(_render_index_section("advisory", advisories, annotated_html_path))
    parts.append("</section>")
    return "\n".join(parts)


def _render_index_section(
    severity: str, defects: list[dict], annotated_html_path: str,
) -> str:
    """One severity-grouped section in the defect index."""
    rows = [f'<section class="severity-group severity-{html.escape(severity)}">']
    rows.append(
        f"<h2>{html.escape(severity.title())} ({len(defects)})</h2>"
    )
    rows.append("<ul>")
    for d in defects:
        claim_id = str(d.get("claim_id", ""))
        message = str(d.get("message", ""))
        anchor = _anchor_id(claim_id)
        href = f"{html.escape(annotated_html_path)}#{html.escape(anchor)}"
        item: list[str] = [
            f'<li><a href="{href}"><code>{html.escape(claim_id)}</code></a> '
            f"— {html.escape(message)}"
        ]
        see_also = d.get("see_also") or []
        if see_also:
            links = ", ".join(
                f'<a href="{html.escape(annotated_html_path)}'
                f'#{html.escape(_anchor_id(str(s)))}">'
                f"<code>{html.escape(str(s))}</code></a>"
                for s in see_also
            )
            item.append(f'<div class="see-also">See also: {links}</div>')
        item.append("</li>")
        rows.append("".join(item))
    rows.append("</ul>")
    rows.append("</section>")
    return "\n".join(rows)


def load_annotations(path: Path) -> dict:
    """Load and lightly-validate a `manuscript-annotations.json`."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level must be an object")
    if data.get("version") != 1:
        warnings.warn(
            f"render_annotations: unexpected annotations version "
            f"{data.get('version')!r} (expected 1); rendering best-effort"
        )
    return data


def _check_source_hash(annotations: dict, source_bytes: bytes) -> None:
    """REQ-PUB-043: emit a single summary warning when the manuscript
    has been modified since verification."""
    expected = annotations.get("source_sha256")
    if not expected:
        return
    actual = hashlib.sha256(source_bytes).hexdigest()
    if actual != expected:
        warnings.warn(
            "render_annotations: manuscript modified since verification "
            f"(sha256 mismatch: expected {expected}, got {actual}); "
            "annotations may be misaligned"
        )


def render_to_out_dir(
    source_path: Path,
    annotations_path: Path,
    out_dir: Path,
    stylesheet: str | None = None,
    verdict_confidence: float | None = None,
) -> tuple[Path, Path | None]:
    """High-level renderer: read source + annotations, write
    `<stem>-annotated.html` (always) and `defect-index.html` (when
    `out_dir` is given). Returns `(annotated_path, index_path)`.
    """
    source_bytes = Path(source_path).read_bytes()
    source_md = source_bytes.decode("utf-8")
    annotations = load_annotations(annotations_path)
    _check_source_hash(annotations, source_bytes)
    body = render_html(source_md, annotations)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(source_path).stem
    annotated_path = out_dir / f"{stem}-annotated.html"
    annotated_path.write_text(
        _wrap_full_document(body, title=f"{stem} (annotated)",
                            stylesheet=stylesheet),
        encoding="utf-8", newline="\n",
    )
    index_path = out_dir / "defect-index.html"
    index_body = render_defect_index(
        annotations,
        annotated_html_path=annotated_path.name,
        verdict_confidence=verdict_confidence,
    )
    index_path.write_text(
        _wrap_full_document(index_body, title="Defect index",
                            stylesheet=stylesheet),
        encoding="utf-8", newline="\n",
    )
    return annotated_path, index_path


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="render_annotations",
        description="Render manuscript-annotations.json as an HTML overlay.",
    )
    ap.add_argument("--source", required=True,
                    help="path to the source markdown manuscript")
    ap.add_argument("--annotations", required=True,
                    help="path to manuscript-annotations.json")
    ap.add_argument("--out-dir", required=False, default=None,
                    help="output directory; emits <stem>-annotated.html "
                         "and defect-index.html")
    ap.add_argument("--out", required=False, default=None,
                    help="single-file output path (mutually exclusive "
                         "with --out-dir)")
    ap.add_argument("--stylesheet", required=False, default=None,
                    help="optional CSS stylesheet href; defaults to "
                         "the built-in palette")
    ap.add_argument("--verdict-confidence", type=float, default=None,
                    help="surface the verdict's top-level confidence on "
                         "the defect-index page")
    args = ap.parse_args(argv)
    if not args.out_dir and not args.out:
        # Default: place outputs next to the source in a `render/` dir.
        args.out_dir = "work/render"
    if args.out and args.out_dir:
        print("--out and --out-dir are mutually exclusive", file=sys.stderr)
        return 2
    if args.out_dir:
        annotated, index = render_to_out_dir(
            Path(args.source),
            Path(args.annotations),
            Path(args.out_dir),
            stylesheet=args.stylesheet,
            verdict_confidence=args.verdict_confidence,
        )
        print(f"wrote {annotated}")
        print(f"wrote {index}")
        return 0
    # Single-file mode.
    source_bytes = Path(args.source).read_bytes()
    source_md = source_bytes.decode("utf-8")
    annotations = load_annotations(Path(args.annotations))
    _check_source_hash(annotations, source_bytes)
    body = render_html(source_md, annotations)
    stem = Path(args.source).stem
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        _wrap_full_document(body, title=f"{stem} (annotated)",
                            stylesheet=args.stylesheet),
        encoding="utf-8", newline="\n",
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
