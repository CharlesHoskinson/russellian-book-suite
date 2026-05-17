"""Generate concept reconciliation pages via booklogic.reconcile_concepts.
Each canonical concept gets its own markdown file under syntopical/concepts/."""
from __future__ import annotations
import os
from pathlib import Path
from sibling_skills import load_skill_api
from scripts.booklogic_adapter import reconcile_concepts as _booklogic_reconcile_concepts
from scripts.booklogic_adapter import CanonicalConcept, Alternate

_LEGACY_BANNER = "> Legacy mode — booklogic disabled"


def _load_book_knowledge():
    return load_skill_api("book-knowledge", expected_major=0)


def _legacy_cluster_concepts(concepts) -> list[CanonicalConcept]:
    """Cluster concepts by overlapping surface_forms. Clusters of size >= 2 become
    a CanonicalConcept whose slug is the lexicographically first member."""
    # Build a union-find structure based on shared surface forms
    slugs = [c.slug for c in concepts]
    parent = {s: s for s in slugs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            # smaller slug as root for determinism
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    # Group by surface form
    sf_to_slugs: dict[str, list[str]] = {}
    for c in concepts:
        for sf in getattr(c, "surface_forms", []):
            sf_to_slugs.setdefault(sf, []).append(c.slug)

    for sf, members in sf_to_slugs.items():
        for i in range(1, len(members)):
            union(members[0], members[i])

    # Build groups
    groups: dict[str, list] = {}
    for c in concepts:
        root = find(c.slug)
        groups.setdefault(root, []).append(c)

    result: list[CanonicalConcept] = []
    for root in sorted(groups.keys()):
        members = sorted(groups[root], key=lambda c: c.slug)
        if len(members) < 2:
            continue
        canonical_slug = root
        alternates = []
        for m in members:
            if m.slug == canonical_slug:
                continue
            sf = (getattr(m, "surface_forms", None) or [m.slug])[0]
            src = (getattr(m, "sources", None) or ["unknown"])[0]
            alternates.append(Alternate(
                slug=m.slug,
                surface_form=sf,
                source_id=src,
                rewrite_witness="legacy-surface-form-cluster",
            ))
        result.append(CanonicalConcept(slug=canonical_slug, alternates=alternates))
    return result


def _write_concept_file(out_dir: Path, cc: CanonicalConcept, banner: str | None = None) -> Path:
    lines = []
    if banner:
        lines += [banner, ""]
    lines += [f"# Canonical Concept: {cc.slug}", "",
              "| Alternate slug | Surface form | Source | Rewrite-witness |",
              "|---|---|---|---|"]
    for a in cc.alternates:
        lines.append(f"| {a.slug} | {a.surface_form} | {a.source_id} | {a.rewrite_witness} |")
    out = out_dir / f"{cc.slug}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def build_concept_reconciliation(workspace_root: Path) -> list[Path]:
    bk = _load_book_knowledge()
    concepts = bk.list_concepts(workspace_root)
    out_dir = workspace_root / "syntopical" / "concepts"
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*.md"):
        f.unlink()
    if os.environ.get("SYNTOPICAL_NO_BOOKLOGIC") == "1":
        canon = _legacy_cluster_concepts(concepts)
        return [_write_concept_file(out_dir, cc, banner=_LEGACY_BANNER) for cc in canon]
    canon = _booklogic_reconcile_concepts(concepts)
    return [_write_concept_file(out_dir, cc) for cc in canon]
