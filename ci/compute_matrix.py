"""Dynamic python-skill matrix from .github/ci/skills-matrix.json.

REQ-CI-046: on pull_request events only skills whose paths intersect the
PR diff are selected; shared-path hits and push/merge_group/dispatch/
schedule events select the full matrix. Fail-closed: any error computing
the selection exits non-zero, which fails the compute-matrix job, which
fails ci-required.

Profiles:
  pr             event-scoped selection, rows = entry x entry.os
  full           full selection, rows = entry x entry.os
  windows-canary full selection, one windows-2022 row per runnable entry
                 (nightly under-tagging safety net)
  python-compat  full selection, ubuntu-24.04 rows x --python-versions
                 (nightly py3.11/3.12 coverage; constraints dropped since
                 lockfiles are generated under 3.13)

Run:       python -m ci.compute_matrix --profile pr
Tested by: ci/test_compute_matrix.py
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / ".github" / "ci" / "skills-matrix.json"
FULL_EVENTS = {"push", "merge_group", "workflow_dispatch", "schedule"}


def load_config(path: Path = MATRIX_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    for key in ("shared_paths", "defaults", "skills"):
        if key not in config:
            raise ValueError(f"skills-matrix.json missing top-level key {key!r}")
    return config


def runnable(config: dict) -> list[dict]:
    return [e for e in config["skills"] if e.get("ci") != "none"]


def shared_hit(paths: list[str], shared_paths: list[str]) -> bool:
    for pattern in shared_paths:
        if pattern.endswith("/**"):
            prefix = pattern[: -len("**")]
            if any(p.startswith(prefix) for p in paths):
                return True
        elif pattern in paths:
            return True
    return False


def changed_paths(base_ref: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def select_skills(config: dict, event: str, paths: list[str]) -> list[dict]:
    entries = runnable(config)
    if event in FULL_EVENTS:
        return entries
    if shared_hit(paths, config["shared_paths"]):
        return entries
    return [
        e for e in entries
        if any(p.startswith(f"skills/{e['skill']}/") for p in paths)
    ]


def _row(
    entry: dict,
    os_name: str,
    defaults: dict,
    python_version: str = "3.13",
    include_constraints: bool = True,
) -> dict:
    return {
        "skill": entry["skill"],
        "os": os_name,
        "python_version": python_version,
        "extra": entry.get("extra", defaults.get("extra", "ci")),
        "constraints": entry.get("constraints", "") if include_constraints else "",
        "siblings": " ".join(entry.get("siblings", [])),
        "pytest_deselect": entry.get("pytest_deselect", ""),
        "pytest_workers": entry.get("pytest_workers", ""),
        "smoke": entry.get("smoke", ""),
        "spacy": "true" if entry.get("spacy") else "false",
        "hf_model": entry.get("hf_model", ""),
        "timeout": entry.get("timeout", defaults.get("timeout", 15)),
    }


def build_rows(
    entries: list[dict],
    config: dict,
    profile: str = "pr",
    python_versions: list[str] | None = None,
) -> list[dict]:
    defaults = config["defaults"]
    rows: list[dict] = []
    if profile in ("pr", "full"):
        for e in entries:
            for os_name in e.get("os", defaults["os"]):
                rows.append(_row(e, os_name, defaults))
    elif profile == "windows-canary":
        for e in entries:
            rows.append(_row(e, "windows-2022", defaults))
    elif profile == "python-compat":
        for e in entries:
            for version in python_versions or []:
                rows.append(
                    _row(e, "ubuntu-24.04", defaults, python_version=version,
                         include_constraints=False)
                )
    else:
        raise ValueError(f"unknown profile {profile!r}")
    return rows


def _write_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        print(f"{name}={value}")
        return
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(f"{name}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=["pr", "full", "windows-canary", "python-compat"],
        default="pr",
    )
    parser.add_argument("--python-versions", default="")
    parser.add_argument("--output-prefix", default="")
    args = parser.parse_args()

    config = load_config()
    if args.profile == "pr":
        event = os.environ.get("EVENT_NAME", "")
        if event == "pull_request":
            base_ref = os.environ.get("BASE_REF", "")
            if not base_ref:
                print("compute_matrix: BASE_REF unset on pull_request; failing closed")
                return 1
            selected = select_skills(config, event, changed_paths(base_ref))
        else:
            selected = select_skills(config, event or "push", [])
            if not selected:
                print("compute_matrix: zero skills on a full-matrix event; failing closed")
                return 1
    else:
        selected = runnable(config)
        if not selected:
            print("compute_matrix: zero runnable skills; failing closed")
            return 1

    versions = [v for v in args.python_versions.split(",") if v]
    rows = build_rows(selected, config, profile=args.profile, python_versions=versions)
    prefix = args.output_prefix
    _write_output(f"{prefix}matrix", json.dumps({"include": rows}))
    _write_output(f"{prefix}any_selected", "true" if rows else "false")
    print(f"compute_matrix [{args.profile}]: {len(rows)} rows "
          f"({len(selected)} skills selected)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
