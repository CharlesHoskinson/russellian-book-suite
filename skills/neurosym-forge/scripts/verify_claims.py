"""Print the build+verify commands for a scaffolded project."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--input", required=True, help="EDN claim file")
    ap.add_argument("--output", default="work/verdict.edn")
    args = ap.parse_args(argv)
    project = Path(args.project)
    if not (project / "package.json").exists():
        print(f"no package.json found at {project}; was it scaffolded?",
              file=sys.stderr)
        return 1
    print(f"# Run these commands from {project}:")
    print("npm install")
    print("npm run build")
    print(f"node cljs-orchestrator/dist/main.js verify {args.input} {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
