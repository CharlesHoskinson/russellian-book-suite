"""ASCII diagram of phase boundaries in a scaffolded neurosym-forge project."""
from __future__ import annotations

import argparse
import sys

TEMPLATE = r"""
Phase 1 [Claude]         Extract atoms              -> work/claims.edn
        |
        v
Phase 2 [ClojureScript]  Rewrite via meander (= ...) -> work/fol.edn
        |
        v
Phase 3 [Rust]           Verify (Z3 / egg / cozo)    -> work/verdict.edn
        |
        v
Phase 4 [Claude]         Synthesise report           -> work/report.md
        |
        v
Phase 5 [Rust]           Typeset (tectonic)          -> work/report.pdf

Project: {slug}
"""


def render_call_graph(project_slug: str) -> str:
    return TEMPLATE.format(slug=project_slug)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    args = ap.parse_args(argv)
    print(render_call_graph(args.slug))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
