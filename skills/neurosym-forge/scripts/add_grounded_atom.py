"""Append a grounded atom record + Rust stub + CLJS bridge stub."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from scripts._io import read_edn_as_json, write_json_as_edn, file_checksum
from scripts.sort_registry import Sort

NAPI_LIBS = {"z3", "egg", "cozo", "tectonic", "custom"}


def _camel_case(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _napi_arg_types(sort: dict[str, Any]) -> tuple[str, str]:
    """For v0.1 every grounded fn takes and returns String (EDN over the wire)."""
    return ("formulas_edn: String", "napi::Result<String>")


def add_grounded_atom(
    project_root: Path,
    project_slug: str,
    name: str,
    lib: str,
    fn: str,
    sort: dict[str, Any],
    doc: str | None = None,
) -> None:
    if lib not in NAPI_LIBS:
        raise ValueError(f"lib must be one of {sorted(NAPI_LIBS)}, got {lib!r}")
    if not name.startswith(":"):
        raise ValueError(f"grounded atom name must start with ':', got {name!r}")
    Sort.from_value(sort)  # validate shape

    grounded_path = project_root / "rules" / "grounded.edn"
    payload = read_edn_as_json(grounded_path)
    if any(g["name"] == name for g in payload.get("grounded", [])):
        raise ValueError(f"duplicate grounded atom: {name}")
    record: dict[str, Any] = {
        "kind": "grounded",
        "name": name,
        "sort": sort,
        "grounded": {"lib": lib, "fn": fn, "napi": True},
    }
    if doc:
        record["doc"] = doc
    payload.setdefault("grounded", []).append(record)
    write_json_as_edn(grounded_path, payload)

    rs_path = project_root / "rust-verifier" / "src" / f"{lib}.rs"
    if not rs_path.exists():
        rs_path.write_text(f"// grounded atoms for lib={lib}\n", encoding="utf-8", newline="\n")
    arg_sig, ret_sig = _napi_arg_types(sort)
    rs_path.write_text(
        rs_path.read_text(encoding="utf-8")
        + (
            f"\n\n#[napi_derive::napi]\n"
            f"pub fn {fn}({arg_sig}) -> {ret_sig} {{\n"
            f"    // TODO ({name}): implement against {lib} backend.\n"
            f"    // Sort: {json.dumps(sort)}\n"
            f"    todo!()\n"
            f"}}\n"
        ),
        encoding="utf-8",
        newline="\n",
    )

    lib_rs = project_root / "rust-verifier" / "src" / "lib.rs"
    text = lib_rs.read_text(encoding="utf-8")
    mod_line = f"mod {lib};"
    if mod_line not in text:
        if "mod ir;" in text:
            text = re.sub(r"(mod ir;)", r"\1\n" + mod_line, text, count=1)
        else:
            text = text.rstrip() + "\n" + mod_line + "\n"
        lib_rs.write_text(text, encoding="utf-8", newline="\n")

    bridge_path = (
        project_root / "cljs-orchestrator" / "src" / "main" / project_slug / "bridge.cljs"
    )
    bridge_text = bridge_path.read_text(encoding="utf-8")
    bridge_text += (
        f"\n(defn {fn.replace('_', '-')} [edn-arg]\n"
        f"  (native/{_camel_case(fn)} edn-arg))\n"
    )
    bridge_path.write_text(bridge_text, encoding="utf-8", newline="\n")

    checksums_path = project_root / "rules" / ".checksums.edn"
    checksums = read_edn_as_json(checksums_path)["checksums"] if checksums_path.exists() else {}
    checksums["grounded.edn"] = file_checksum(grounded_path)
    write_json_as_edn(checksums_path, {"checksums": checksums})


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--lib", required=True, choices=sorted(NAPI_LIBS))
    ap.add_argument("--fn", required=True)
    ap.add_argument("--sort", required=True,
                    help="JSON object describing the sort, e.g. "
                         "'{\"kind\":\"fn\",\"args\":[\":atom\"],\"ret\":\":verdict\"}'")
    ap.add_argument("--doc")
    args = ap.parse_args(argv)
    add_grounded_atom(
        project_root=Path(args.project),
        project_slug=args.slug,
        name=args.name,
        lib=args.lib,
        fn=getattr(args, "fn"),
        sort=json.loads(args.sort),
        doc=args.doc,
    )
    print(f"added grounded atom {args.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
