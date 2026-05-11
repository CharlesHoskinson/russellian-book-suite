"""Stage-1 deterministic linter for assembled book artefacts.

Catches the mechanical defect classes D1-D8 directly from our retrospective:

D1  orphan citation tokens                  ([clm-...], "Claim ledger:", numeric-id GFM footnotes)
D2  raw markdown bleed inside HTML blocks   (# heading or | table inside <section> or <div>)
D3  broken cross-references                 (figure path missing, footnote ref without def, ToC mismatch)
D4  heading-hierarchy violations            (H3 without H2, missing H1, duplicate H1)
D5  count-contract failures                 (chapter word/footnote/figure count out of band)
D6  paragraph-length variance               (within-chapter cv outside [0.4, 1.1])
D7  CSS reset clobber                       (Tailwind preflight + no h1 override in final HTML)
D8  asset 404s                              (every <img src> resolves to a real file)

Usage:
    python lint_artifact.py <workspace> <release-version>

Emits JSON to <workspace>/qa/defects.json with structured tickets,
exits 0 if no D1-D8 defects, exit 1 otherwise.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Defect:
    class_: str        # "D1" .. "D8"
    severity: str      # "critical" | "minor"
    where: str         # human-readable location
    detail: str        # one-line description
    fix_hint: str = ""


CRITICAL = "critical"
MINOR = "minor"


# ----------------------------------------------------------------- D1 helpers

CLM_TOKEN_RE = re.compile(r"\[?clm-\d{4}-\d{6}\]?")
CLAIM_LEDGER_RE = re.compile(r"Claim ledger:", re.IGNORECASE)
NUMERIC_FN_CLM_RE = re.compile(r"^\[\^\d+\]:\s*clm-\d{4}-\d{6}", re.MULTILINE)


def lint_d1_orphan_tokens(md: str) -> list[Defect]:
    out: list[Defect] = []
    for m in CLM_TOKEN_RE.finditer(md):
        line = md.count("\n", 0, m.start()) + 1
        out.append(Defect("D1", CRITICAL,
                          f"line {line}", f"orphan claim token {m.group(0)!r}",
                          "strip the token from the chapter draft"))
    for m in CLAIM_LEDGER_RE.finditer(md):
        line = md.count("\n", 0, m.start()) + 1
        out.append(Defect("D1", CRITICAL, f"line {line}",
                          "'Claim ledger:' citation noise in prose",
                          "rewrite the sentence or footnote without the internal-ID phrasing"))
    for m in NUMERIC_FN_CLM_RE.finditer(md):
        line = md.count("\n", 0, m.start()) + 1
        out.append(Defect("D1", CRITICAL, f"line {line}",
                          "numeric-ID footnote defn whose body is a claim ID + statement",
                          "delete this footnote or rewrite as a substantive aside"))
    return out


# ----------------------------------------------------------------- D2 helpers

HTML_BLOCK_RE = re.compile(
    r"(<(?P<tag>section|div|figure|aside)[^>]*>)(?P<body>.*?)(</(?P=tag)>)",
    re.DOTALL,
)
MD_LEAK_RE = re.compile(r"(?m)^#{1,6}\s|^\s*\|.+\||\*\*[^*\n]+\*\*")


def lint_d2_raw_md_bleed(md: str) -> list[Defect]:
    out: list[Defect] = []
    # Hot-fix exception: hero tables contain markdown-looking content inside <td>
    # legitimately; skip <div class="hero-table">.
    for m in HTML_BLOCK_RE.finditer(md):
        body = m.group("body")
        if "hero-table" in m.group(1):
            continue
        # Match Markdown leaks that start at the actual start of body, not inside HTML tags
        # Look for `# ` or `## ` etc. on their own line within an HTML block
        for leak in re.finditer(r"(?m)^#{1,6}\s+\S", body):
            line = md.count("\n", 0, m.start()) + body.count("\n", 0, leak.start()) + 1
            out.append(Defect("D2", CRITICAL, f"line {line}",
                              f"markdown heading inside <{m.group('tag')}> block",
                              "insert a blank line after the closing tag so markdown parser re-engages"))
    return out


# ----------------------------------------------------------------- D3 helpers

IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
FN_REF_RE = re.compile(r'class="footnote-ref"\s+id="fnref-([^"]+)"')
FN_DEF_RE = re.compile(r'<li\s+id="fn-([^"]+)"')
CHAPTER_HEADING_RE = re.compile(r"^# Chapter\s+(\d+):\s*(.+)$", re.MULTILINE)
TOC_ITEM_RE = re.compile(r"^\s*(\d+)\.\s+(.+)$", re.MULTILINE)


def lint_d3_broken_xref(md: str, workspace: Path, release_dir: Path) -> list[Defect]:
    out: list[Defect] = []

    # Figure paths
    for m in IMG_RE.finditer(md):
        rel = m.group(1).strip()
        # Manuscript.md is at <release_dir>/manuscript.md; relative paths resolve from there
        target = (release_dir / rel).resolve()
        if not target.exists():
            line = md.count("\n", 0, m.start()) + 1
            out.append(Defect("D3", CRITICAL, f"line {line}",
                              f"image src {rel!r} does not resolve",
                              f"create the asset or correct the path; expected at {target}"))

    # Footnote ref↔def integrity
    refs = set(FN_REF_RE.findall(md))
    defs = set(FN_DEF_RE.findall(md))
    for r in sorted(refs - defs):
        out.append(Defect("D3", CRITICAL, "footnote refs",
                          f"footnote ref {r!r} has no matching <li id='fn-{r}'>",
                          "either delete the inline ref or add a definition"))
    for d in sorted(defs - refs):
        out.append(Defect("D3", MINOR, "footnote defs",
                          f"footnote def {d!r} has no matching ref",
                          "delete the orphan definition"))

    # ToC vs chapter headings
    headings = [(int(m.group(1)), m.group(2).strip()) for m in CHAPTER_HEADING_RE.finditer(md)]
    # Pull ToC entries from the section between "## Table of Contents" and the next `---`
    toc_match = re.search(r"## Table of Contents\s*(.+?)\n---", md, re.DOTALL)
    if toc_match:
        toc_entries = [(int(m.group(1)), m.group(2).strip())
                       for m in TOC_ITEM_RE.finditer(toc_match.group(1))]
        for (n_toc, title_toc), (n_ch, title_ch) in zip(toc_entries, headings):
            if n_toc != n_ch or title_toc != title_ch:
                out.append(Defect("D3", CRITICAL, f"ToC entry {n_toc}",
                                  f"ToC says {n_toc}. {title_toc!r}; chapter heading says {n_ch}. {title_ch!r}",
                                  "rebuild ToC or correct the heading"))
    return out


# ----------------------------------------------------------------- D4 helpers

H_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def lint_d4_hierarchy(md: str) -> list[Defect]:
    out: list[Defect] = []
    headings = [(len(m.group(1)), m.group(2).strip(), md.count("\n", 0, m.start()) + 1)
                for m in H_RE.finditer(md)]
    prev_level = 0
    for level, title, line in headings:
        if level > prev_level + 1 and prev_level > 0:
            out.append(Defect("D4", MINOR, f"line {line}",
                              f"heading jumps from h{prev_level} to h{level}: {title!r}",
                              "demote the heading or insert a parent level"))
        prev_level = level
    # Missing chapter heading?
    chapter_h1s = [t for lv, t, _ in headings if lv == 1 and t.lower().startswith("chapter")]
    if not chapter_h1s and len(headings) > 5:  # non-trivial doc
        out.append(Defect("D4", CRITICAL, "doc-level",
                          "no `# Chapter N:` heading found",
                          "assembled manuscript should have one h1 per chapter"))
    return out


# ----------------------------------------------------------------- D5 + D6

WORD_RE = re.compile(r"\b\w+\b")


def _strip_html_blocks(body: str) -> str:
    """Remove <section>, <div>, <figure>, <aside> blocks so word counts
    measure only the chapter's actual prose, not embedded tables/figures/footnote
    sections."""
    return re.sub(
        r"<(section|div|figure|aside)\b[^>]*>.*?</\1>",
        " ",
        body,
        flags=re.DOTALL,
    )


BACK_MATTER_BOUNDARY = re.compile(
    r"\n---\n+##\s+(How to read|Glossary|Sources|For Further Reading|A note on)",
)


def _chapter_bodies(md: str) -> list[tuple[int, str, str]]:
    """Return (chapter_num, chapter_title, prose_body) for each chapter.
    prose_body has embedded HTML blocks (tables, footnote sections) stripped,
    and the last chapter ends at the back-matter boundary."""
    positions = [(m.start(), int(m.group(1)), m.group(2).strip())
                 for m in CHAPTER_HEADING_RE.finditer(md)]
    out = []
    for i, (start, num, title) in enumerate(positions):
        if i + 1 < len(positions):
            end = positions[i + 1][0]
        else:
            # Last chapter: stop at back-matter boundary
            bm = BACK_MATTER_BOUNDARY.search(md, start)
            end = bm.start() if bm else len(md)
        out.append((num, title, _strip_html_blocks(md[start:end])))
    return out


def lint_d5_count_contracts(md: str,
                             word_band: tuple[int, int] = (1700, 2700),
                             fn_band: tuple[int, int] = (3, 12),
                             fig_band: tuple[int, int] = (0, 4)) -> list[Defect]:
    out: list[Defect] = []
    # For footnote counts we need the un-stripped body (footnotes live in HTML <sup>)
    full_bodies = []
    positions = [(m.start(), int(m.group(1))) for m in CHAPTER_HEADING_RE.finditer(md)]
    for i, (start, num) in enumerate(positions):
        if i + 1 < len(positions):
            end = positions[i + 1][0]
        else:
            bm = BACK_MATTER_BOUNDARY.search(md, start)
            end = bm.start() if bm else len(md)
        full_bodies.append((num, md[start:end]))
    full_by_num = dict(full_bodies)

    for num, title, body in _chapter_bodies(md):
        wc = len(WORD_RE.findall(body))
        fn = len(FN_REF_RE.findall(full_by_num.get(num, "")))
        figs = len(IMG_RE.findall(body))
        loc = f"ch-{num:02d}"
        if not (word_band[0] <= wc <= word_band[1]):
            out.append(Defect("D5", MINOR, loc,
                              f"word count {wc} outside [{word_band[0]}, {word_band[1]}]",
                              "shorten or expand prose, or revise contract band"))
        if not (fn_band[0] <= fn <= fn_band[1]):
            out.append(Defect("D5", MINOR, loc,
                              f"footnote ref count {fn} outside [{fn_band[0]}, {fn_band[1]}]",
                              "add or trim footnotes"))
        if not (fig_band[0] <= figs <= fig_band[1]):
            out.append(Defect("D5", MINOR, loc,
                              f"figure count {figs} outside [{fig_band[0]}, {fig_band[1]}]",
                              "add or remove figures"))
    return out


def lint_d6_paragraph_variance(md: str,
                                cv_band: tuple[float, float] = (0.4, 1.2),
                                mean_band: tuple[int, int] = (35, 130)) -> list[Defect]:
    out: list[Defect] = []
    for num, title, body in _chapter_bodies(md):
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()
                 and not p.startswith(("|", "<", ":", "#", ">"))]
        if len(paras) < 4:
            continue
        lengths = [len(WORD_RE.findall(p)) for p in paras]
        if not lengths:
            continue
        mean = statistics.mean(lengths)
        stdev = statistics.pstdev(lengths)
        cv = stdev / mean if mean else 0
        loc = f"ch-{num:02d}"
        if not (cv_band[0] <= cv <= cv_band[1]):
            out.append(Defect("D6", MINOR, loc,
                              f"paragraph-length coefficient-of-variation {cv:.2f} outside [{cv_band[0]}, {cv_band[1]}]",
                              "vary paragraph length more (low cv) or normalise outliers (high cv)"))
        if not (mean_band[0] <= mean <= mean_band[1]):
            out.append(Defect("D6", MINOR, loc,
                              f"average paragraph length {mean:.0f} words outside [{mean_band[0]}, {mean_band[1]}]",
                              "shorten or lengthen typical paragraphs"))
    return out


# ----------------------------------------------------------------- D7 + D8

PREFLIGHT_RESET_RE = re.compile(
    r"h1\s*,\s*h2\s*,\s*h3.*?\{[^}]*font-size\s*:\s*inherit",
    re.DOTALL,
)
H1_OVERRIDE_RE = re.compile(
    r"h1\s*\{[^}]*font-size\s*:\s*[\d.]+(?:em|px|rem)",
    re.DOTALL,
)


def lint_d7_css_reset(html: str) -> list[Defect]:
    if not html:
        return []
    has_reset = bool(PREFLIGHT_RESET_RE.search(html))
    has_override = bool(H1_OVERRIDE_RE.search(html))
    if has_reset and not has_override:
        return [Defect("D7", CRITICAL, "manuscript.html",
                       "Tailwind preflight resets heading sizes and no override block found",
                       "inject a stronger heading-size style block AFTER the preflight in the cascade")]
    return []


IMG_HTML_RE = re.compile(r'<img\s+[^>]*src=["\']([^"\']+)["\']', re.IGNORECASE)


def lint_d8_asset_404s(md: str, html: str, release_dir: Path) -> list[Defect]:
    out: list[Defect] = []
    paths = set()
    for m in IMG_RE.finditer(md):
        paths.add(m.group(1).strip())
    for m in IMG_HTML_RE.finditer(html):
        src = m.group(1).strip()
        if src.startswith(("data:", "http://", "https://", "${", "blob:")):
            continue
        paths.add(src)
    for rel in sorted(paths):
        target = (release_dir / rel).resolve()
        if not target.exists():
            out.append(Defect("D8", CRITICAL, "assets",
                              f"asset {rel!r} not found at {target}",
                              "create the asset or correct the path"))
    return out


# ----------------------------------------------------------------- main

def lint_artifact(workspace: Path, version: str) -> tuple[list[Defect], dict]:
    release_dir = workspace / "book" / "releases" / version
    md_path = release_dir / "manuscript.md"
    html_path = release_dir / "manuscript.html"
    if not md_path.exists():
        raise FileNotFoundError(md_path)
    md = md_path.read_text(encoding="utf-8")
    html = html_path.read_text(encoding="utf-8") if html_path.exists() else ""

    defects: list[Defect] = []
    defects += lint_d1_orphan_tokens(md)
    defects += lint_d2_raw_md_bleed(md)
    defects += lint_d3_broken_xref(md, workspace, release_dir)
    defects += lint_d4_hierarchy(md)
    defects += lint_d5_count_contracts(md)
    defects += lint_d6_paragraph_variance(md)
    defects += lint_d7_css_reset(html)
    defects += lint_d8_asset_404s(md, html, release_dir)

    summary = {
        "release": version,
        "manuscript_md_bytes": len(md),
        "manuscript_html_bytes": len(html),
        "total_defects": len(defects),
        "by_class": {},
        "by_severity": {CRITICAL: 0, MINOR: 0},
    }
    for d in defects:
        summary["by_class"][d.class_] = summary["by_class"].get(d.class_, 0) + 1
        summary["by_severity"][d.severity] += 1

    return defects, summary


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: lint_artifact.py <workspace> <release-version>", file=sys.stderr)
        return 2
    workspace = Path(argv[1]).resolve()
    version = argv[2]
    defects, summary = lint_artifact(workspace, version)
    out_dir = workspace / "qa"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "defects.json"
    payload = {
        "summary": summary,
        "defects": [asdict(d) for d in defects],
    }
    # rename the dataclass field for JSON
    for entry in payload["defects"]:
        entry["class"] = entry.pop("class_")
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    # Console summary
    print(f"Linted {workspace.name} @ {version}")
    print(f"  md: {summary['manuscript_md_bytes']:,} bytes; html: {summary['manuscript_html_bytes']:,} bytes")
    print(f"  defects: {summary['total_defects']} ({summary['by_severity'][CRITICAL]} critical, {summary['by_severity'][MINOR]} minor)")
    for cls in sorted(summary["by_class"]):
        print(f"    {cls}: {summary['by_class'][cls]}")
    print(f"  full report: {out_path}")
    n_critical = summary["by_severity"][CRITICAL]
    return 1 if n_critical else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
