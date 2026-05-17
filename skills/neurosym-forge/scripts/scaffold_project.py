"""Emit a CLJS+Rust neurosymbolic verifier project from the template tree."""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from scripts._edn_reader import Keyword
from scripts._io import file_checksum, write_edn_file

CHECKSUMS_KEY = Keyword("checksums")

FORGE_VERSION = "0.1.0"
SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def scaffold_project(
    project_name: str,
    project_slug: str,
    out_dir: Path,
    skill_root: Path,
    has_book_knowledge_bridge: bool = False,
) -> None:
    """Render the project template tree into out_dir."""
    if not SLUG_PATTERN.match(project_slug):
        raise ValueError(f"project_slug must match {SLUG_PATTERN.pattern!r}, got {project_slug!r}")
    out_str = str(out_dir)
    resolved = Path(out_str).resolve()
    cwd = Path.cwd().resolve()
    if not Path(out_str).is_absolute() and not resolved.is_relative_to(cwd.parent):
        raise ValueError(
            f"--out {out_str!r} resolves to {resolved}, which is outside the "
            f"current working directory {cwd}; pass an absolute path if intentional"
        )
    out_dir = resolved
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
        "project_slug_dashed": project_slug.replace("_", "-"),
        "neurosym_forge_version": FORGE_VERSION,
        "scaffolded_at": dt.datetime.now(dt.UTC).isoformat(),
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

    # Bridge-specific templates (only if --book-knowledge-bridge)
    if has_book_knowledge_bridge:
        bridge_root = skill_root / "assets" / "project-template-bridge"
        if bridge_root.is_dir():
            bridge_env = Environment(
                loader=FileSystemLoader(str(bridge_root)),
                keep_trailing_newline=True,
                undefined=StrictUndefined,
            )
            for tmpl in sorted(bridge_root.rglob("*.tmpl")):
                rel = tmpl.relative_to(bridge_root)
                out_rel = Path(str(rel)[:-len(".tmpl")].replace("__project__", project_slug))
                loader_path = str(rel).replace("\\", "/")
                template = bridge_env.get_template(loader_path)
                rendered = template.render(**ctx)
                out_path = out_dir / out_rel
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(rendered, encoding="utf-8", newline="\n")

    # Initialise rules checksums based on the freshly-rendered files
    checksums: dict[str, str] = {}
    for p in sorted((out_dir / "rules").glob("*.edn")):
        if p.name.startswith("."):
            continue
        checksums[p.name] = file_checksum(p)
    write_edn_file(out_dir / "rules" / ".checksums.edn", {CHECKSUMS_KEY: checksums})

    # Vendor the codegen library into the scaffolded project's scripts/ so
    # that `python scripts/codegen_axioms.py` works without PYTHONPATH tricks.
    # We copy the canonical library as `_codegen_axioms_lib.py` alongside the
    # rendered shim (`codegen_axioms.py`). The shim's fallback path picks this up.
    import shutil as _shutil
    scripts_src  = Path(__file__).resolve().parent
    scripts_dest = out_dir / "scripts"
    scripts_dest.mkdir(parents=True, exist_ok=True)
    # Create __init__.py so scripts/ is a proper package importable from
    # the project root (needed by `python scripts/codegen_axioms.py`).
    _init = scripts_dest / "__init__.py"
    if not _init.exists():
        _init.write_text("", encoding="utf-8")
    for _dep_src, _dep_dst in (
        ("_edn_reader.py",   "_edn_reader.py"),
        ("_edn_writer.py",   "_edn_writer.py"),
        ("_io.py",           "_io.py"),
        ("codegen_axioms.py","_codegen_axioms_lib.py"),
        ("codegen_kg.py",    "_codegen_kg_lib.py"),
    ):
        _src = scripts_src / _dep_src
        if _src.exists():
            _shutil.copy2(str(_src), str(scripts_dest / _dep_dst))

    # Run BookLogic codegen for projects that declare active forms. The
    # codegen scripts are inert when their source EDN is missing or empty.
    try:
        from scripts.codegen_axioms import run as _run_axioms
        _run_axioms(out_dir)
    except Exception as e:
        # Codegen failure during scaffold is non-fatal: the project still
        # has the no-op axioms.rs stub. Surface the error so the user
        # sees the codegen is broken but the scaffold completes.
        print(f"[scaffold] codegen_axioms warning: {e}", file=sys.stderr)
    try:
        from scripts.codegen_kg import run as _run_kg
        _run_kg(out_dir)
    except Exception as e:
        print(f"[scaffold] codegen_kg warning: {e}", file=sys.stderr)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="Human-readable project name")
    ap.add_argument("--slug", required=True, help="Filesystem-safe slug (snake_case)")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--book-knowledge-bridge", action="store_true",
                    help="Emit a book-knowledge claim-ledger ingester template")
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
