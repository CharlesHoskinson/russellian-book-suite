"""Append a grounded atom record + Rust stub + CLJS bridge stub."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, write_edn_file, file_checksum
from scripts.sort_registry import Sort

GROUNDED_KEY = Keyword("grounded")
KIND_KEY = Keyword("kind")
NAME_KEY = Keyword("name")
SORT_KEY = Keyword("sort")
DOC_KEY = Keyword("doc")
CHECKSUMS_KEY = Keyword("checksums")

NAPI_LIBS = {"z3", "egg", "cozo", "tectonic", "custom"}
_FN_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")


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
    if not _FN_PATTERN.match(fn):
        raise ValueError(f"fn must be a snake_case Rust identifier, got {fn!r}")
    Sort.from_value(sort)  # validate shape

    grounded_path = project_root / "rules" / "grounded.edn"
    payload = read_edn_file(grounded_path)
    if any(g[NAME_KEY] == name for g in payload.get(GROUNDED_KEY, [])):
        raise ValueError(f"duplicate grounded atom: {name}")
    record: dict[Any, Any] = {
        KIND_KEY: Keyword("grounded"),
        NAME_KEY: name,
        SORT_KEY: sort,
        GROUNDED_KEY: {Keyword("lib"): lib, Keyword("fn"): fn, Keyword("napi"): True},
    }
    if doc:
        record[DOC_KEY] = doc
    payload.setdefault(GROUNDED_KEY, []).append(record)
    write_edn_file(grounded_path, payload)

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
            f"    // Sort: {sort!r}\n"
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

    grounded_test_dir = project_root / "tests" / "grounded"
    grounded_test_dir.mkdir(parents=True, exist_ok=True)
    fixture = grounded_test_dir / f"test_{fn}.cljs"
    fn_kebab = fn.replace("_", "-")
    fixture_text = (
        f"(ns grounded.test-{fn_kebab}\n"
        f"  (:require [cljs.test :refer-macros [deftest is]]\n"
        f"            [{project_slug}.bridge :as bridge]))\n\n"
        f"(deftest {fn_kebab}-stub-returns\n"
        f"  ;; grounded atom {name} backed by {lib}\n"
        f"  (is (some? :TODO-supply-input-for-{fn_kebab})))\n"
    )
    fixture.write_text(fixture_text, encoding="utf-8", newline="\n")

    checksums_path = project_root / "rules" / ".checksums.edn"
    checksums = read_edn_file(checksums_path)[CHECKSUMS_KEY] if checksums_path.exists() else {}
    checksums["grounded.edn"] = file_checksum(grounded_path)
    write_edn_file(checksums_path, {CHECKSUMS_KEY: checksums})


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
