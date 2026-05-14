"""Emit a CLJS+Rust neurosymbolic verifier project from the template tree."""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from scripts._io import file_checksum, write_json_as_edn

FORGE_VERSION = "0.1.0"


def scaffold_project(
    project_name: str,
    project_slug: str,
    out_dir: Path,
    skill_root: Path,
    has_book_knowledge_bridge: bool = False,
) -> None:
    """Render the project template tree into out_dir."""
    if out_dir.exists():
        raise FileExistsError(f"refusing to overwrite {out_dir}")

    template_root = skill_root / "assets" / "project-template"
    env = Environment(
        loader=FileSystemLoader(str(template_root)),
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )

    ctx = {
        "project_name": project_name,
        "project_slug": project_slug,
        "neurosym_forge_version": FORGE_VERSION,
        "scaffolded_at": dt.datetime.now(dt.UTC).isoformat(),
        "has_book_knowledge_bridge": has_book_knowledge_bridge,
    }

    for tmpl in sorted(template_root.rglob("*.tmpl")):
        rel = tmpl.relative_to(template_root)
        out_rel = Path(str(rel)[: -len(".tmpl")].replace("__project__", project_slug))
        out_path = out_dir / out_rel
        # jinja loader needs forward slashes regardless of OS
        loader_path = str(rel).replace("\\", "/")
        template = env.get_template(loader_path)
        rendered = template.render(**ctx)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8", newline="\n")

    # Initialise rules checksums based on the freshly-rendered files
    checksums: dict[str, str] = {}
    for p in sorted((out_dir / "rules").glob("*.edn")):
        if p.name.startswith("."):
            continue
        checksums[p.name] = file_checksum(p)
    write_json_as_edn(out_dir / "rules" / ".checksums.edn", {"checksums": checksums})


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="Human-readable project name")
    ap.add_argument("--slug", required=True, help="Filesystem-safe slug (snake_case)")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument(
        "--book-knowledge-bridge",
        action="store_true",
        help="Emit a book-knowledge claim-ledger ingestor",
    )
    args = ap.parse_args(argv)
    skill_root = Path(__file__).resolve().parent.parent
    scaffold_project(
        project_name=args.name,
        project_slug=args.slug,
        out_dir=Path(args.out),
        skill_root=skill_root,
        has_book_knowledge_bridge=args.book_knowledge_bridge,
    )
    print(f"scaffolded {args.slug} at {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
