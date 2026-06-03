"""Cross-check claim source spans against raw/ files; promote proposed -> verified."""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from .ledger import read_claims, transition_status, LedgerError
from .source_manifest import load_manifest
from .source_substance import body_chars, MIN_SOURCE_BODY_CHARS
from .workspace import WorkspaceLayout


@dataclass(frozen=True)
class VerificationResult:
    claim_id: str
    ok: bool
    new_status: str
    reason: str = ""
    warnings: tuple[str, ...] = ()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


# Per-document extraction cache, keyed by doc_id. A single verify run reads each
# source file once, regardless of how many claims or spans reference it. Holds the
# raw first-variant text (for the thin-source body check) and the normalized
# extraction variants used for locator matching.
_SOURCE_CACHE: dict[str, "_SourceText"] = {}


@dataclass(frozen=True)
class _SourceText:
    raw_first: str
    norm_variants: tuple[str, ...]


def _pdf_variants(path) -> list[str]:
    """Full-text extractions for a PDF, cheapest and most-conventional first.

    The default ``extract_text`` output comes first so that locators chosen
    against it (every previously verified claim) keep matching unchanged. A
    word-box reconstruction follows: multi-column and tight-kerned academic PDFs
    often drop inter-word spaces in ``extract_text`` ("Thesameproblem"), because
    the default 3-unit word tolerance treats their narrow inter-word gaps as
    intra-word. Re-clustering ``extract_words`` at ``x_tolerance=1`` splits on
    those narrow gaps and recovers the spacing ("the same problem").
    """
    with pdfplumber.open(str(path)) as pdf:
        pages = list(pdf.pages)
        variants = ["\n".join((p.extract_text() or "") for p in pages)]
        try:
            variants.append(
                "\n".join(
                    " ".join(w["text"] for w in p.extract_words(x_tolerance=1))
                    for p in pages
                )
            )
        except Exception:
            # Word-box extraction is a best-effort repair; never let it break
            # verification that the default extraction could satisfy.
            pass
    return variants


def _source_text(layout: WorkspaceLayout, doc_id: str) -> _SourceText:
    cached = _SOURCE_CACHE.get(doc_id)
    if cached is not None:
        return cached
    manifest_path = layout.manifests / f"{doc_id}.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"no manifest for doc_id={doc_id}")
    manifest = load_manifest(manifest_path)
    if manifest["source_kind"] == "markdown":
        path = layout.raw_markdown / manifest["doc_name"]
        variants = [path.read_text(encoding="utf-8")]
    elif manifest["source_kind"] == "pdf":
        variants = _pdf_variants(layout.raw_pdf / manifest["doc_name"])
    else:
        raise ValueError(f"unknown source_kind={manifest['source_kind']}")
    result = _SourceText(
        raw_first=variants[0],
        norm_variants=tuple(_normalize(v) for v in variants),
    )
    _SOURCE_CACHE[doc_id] = result
    return result


def _load_source_text(layout: WorkspaceLayout, doc_id: str) -> str:
    """Default extraction of a source's full text (first variant)."""
    return _source_text(layout, doc_id).raw_first


def _find_claim(layout: WorkspaceLayout, claim_id: str) -> dict | None:
    found: dict | None = None
    for record in read_claims(layout):
        if record["claim_id"] == claim_id:
            found = record
    return found


def verify_claim(layout: WorkspaceLayout, claim_id: str) -> VerificationResult:
    claim = _find_claim(layout, claim_id)
    if claim is None:
        raise LedgerError(f"unknown claim_id={claim_id}")

    warnings: list[str] = []
    for span in claim["source_spans"]:
        source = _source_text(layout, span["doc_id"])
        needle = _normalize(span["locator_text"])
        if not any(needle in variant for variant in source.norm_variants):
            return VerificationResult(
                claim_id=claim_id, ok=False, new_status=claim["status"],
                reason=f"locator_text not found in {span['doc_id']}",
            )
        # A locator can match in a stub's frontmatter while the source has no body.
        # Surface that: the claim still verifies, but the source is too thin to trust.
        n = body_chars(source.raw_first)
        if n < MIN_SOURCE_BODY_CHARS:
            warnings.append(f"thin source {span['doc_id']} ({n} body chars)")

    if claim["status"] == "proposed":
        transition_status(layout, claim_id, "verified", note="locator-text confirmed")
    return VerificationResult(claim_id=claim_id, ok=True, new_status="verified",
                              warnings=tuple(warnings))


def verify_all_proposed(layout: WorkspaceLayout) -> list[VerificationResult]:
    """Run verify_claim against every claim currently in the `proposed` state."""
    results: list[VerificationResult] = []
    seen: set[str] = set()
    for record in read_claims(layout):
        cid = record["claim_id"]
        if cid in seen or record["status"] != "proposed":
            continue
        seen.add(cid)
        results.append(verify_claim(layout, cid))
    return results


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.verify_claim",
        description="Verify claim source spans against raw/ files and promote proposed -> verified.",
    )
    parser.add_argument("workspace", type=Path, help="Workspace root.")
    parser.add_argument("--claim-id", help="Verify a single claim by id (default: every proposed claim).")
    args = parser.parse_args(argv)
    layout = WorkspaceLayout(root=args.workspace.resolve())
    if args.claim_id:
        results = [verify_claim(layout, args.claim_id)]
    else:
        results = verify_all_proposed(layout)
    promoted = sum(1 for r in results if r.ok)
    failed = sum(1 for r in results if not r.ok)
    print(f"verified {len(results)} claim(s): {promoted} promoted, {failed} failed")
    for r in results:
        if not r.ok:
            print(f"  FAIL {r.claim_id}: {r.reason}", file=sys.stderr)
    thin = [r for r in results if r.warnings]
    if thin:
        print(f"  {len(thin)} promoted against a thin source (verify by hand):", file=sys.stderr)
        for r in thin:
            for w in r.warnings:
                print(f"    WARN {r.claim_id}: {w}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
