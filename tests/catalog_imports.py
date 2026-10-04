#!/usr/bin/env python3
"""Compile each public gh-aw import at an immutable catalog commit."""

import argparse
import os
import pathlib
import re
import subprocess
import tempfile

PATTERNS = {
    "issue-triage": "Use the single safe-output comment",
    "ci-failure-diagnosis": "completed workflow run",
    "test-quality": "test-only change",
    "documentation-upkeep": "documentation-only correction",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-ref", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.catalog_ref):
        raise SystemExit("--catalog-ref must be a full lowercase 40-character commit SHA")

    for path in (
        ".github/workflows/run-checked-script.yml",
        ".github/actions/run-checked-script/action.yml",
    ):
        subprocess.run(
            [
                "gh",
                "api",
                f"repos/DevOpsDerek/workflows/contents/{path}?ref={args.catalog_ref}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )

    with tempfile.TemporaryDirectory(prefix="workflow-catalog-test-") as temp:
        workflow_dir = pathlib.Path(temp) / ".github" / "workflows"
        workflow_dir.mkdir(parents=True)
        for name, expected in PATTERNS.items():
            (workflow_dir / f"{name}.md").write_text(
                f"""---
on:
  workflow_dispatch:
permissions:
  contents: read
  issues: read
  pull-requests: read
inlined-imports: true
imports:
  - DevOpsDerek/workflows/.github/workflows/shared/agentic/{name}.md@{args.catalog_ref}
tools:
  github:
---

Follow the imported {name} instructions.
""",
                encoding="utf-8",
            )

        subprocess.run(["git", "init", "--quiet"], check=True, cwd=temp)
        env = os.environ.copy()
        subprocess.run(
            [
                "gh",
                "aw",
                "compile",
                "--validate",
                "--actionlint",
                "--no-check-update",
                "--dir",
                ".github/workflows",
            ],
            check=True,
            env=env,
            cwd=temp,
        )
        for name, expected in PATTERNS.items():
            lock_file = workflow_dir / f"{name}.lock.yml"
            if not lock_file.is_file():
                raise SystemExit(f"gh-aw did not generate {lock_file.name}")
            if expected not in lock_file.read_text(encoding="utf-8"):
                raise SystemExit(
                    f"{lock_file.name} does not contain the inlined component text"
                )
            print(f"verified immutable import and inlined lock: {name}")

        caller_dir = pathlib.Path(temp) / "callers"
        caller_dir.mkdir()
        (caller_dir / "reusable-workflow.yml").write_text(
            f"""name: Contract test
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  checks:
    name: Go tests
    uses: DevOpsDerek/workflows/.github/workflows/run-checked-script.yml@{args.catalog_ref}
    with:
      runtime: go
      version: 1.22.12
      script-path: ./internal/example
""",
            encoding="utf-8",
        )
        (caller_dir / "composite-action.yml").write_text(
            f"""name: Contract test
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  checks:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
      - uses: DevOpsDerek/workflows/.github/actions/run-checked-script@{args.catalog_ref}
        with:
          runtime: python
          version: 3.12.8
          script-path: tests/run_smoke.py
""",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "go",
                "run",
                "github.com/rhysd/actionlint/cmd/actionlint@v1.7.7",
                "-no-color",
                str(caller_dir / "reusable-workflow.yml"),
                str(caller_dir / "composite-action.yml"),
            ],
            check=True,
        )
        print("verified SHA-pinned reusable workflow and composite-action caller YAML")


if __name__ == "__main__":
    main()
