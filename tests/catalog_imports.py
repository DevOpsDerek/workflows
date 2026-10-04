#!/usr/bin/env python3
"""Compile each public gh-aw import at an immutable catalog commit."""

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile

PATTERNS = {
    "issue-triage": "Use the single safe-output comment",
    "ci-failure-diagnosis": "completed workflow run",
    "test-quality": "test-only change",
    "documentation-upkeep": "documentation-only correction",
}
LINT_WORKFLOWS = {
    "python-ruff": {
        "path": ".github/workflows/lint/python-ruff.yml",
        "inputs": {
            "python-version": "3.12.8",
            "ruff-version": "0.11.13",
            "working-directory": "src",
        },
    },
    "go": {
        "path": ".github/workflows/lint/go.yml",
        "inputs": {
            "go-version": "1.22.12",
            "golangci-lint-version": "1.64.8",
            "working-directory": "src",
        },
    },
    "rust": {
        "path": ".github/workflows/lint/rust.yml",
        "inputs": {"rust-version": "1.86.0", "working-directory": "src"},
    },
    "shell": {
        "path": ".github/workflows/lint/shell.yml",
        "inputs": {"shellcheck-version": "0.10.0", "working-directory": "scripts"},
    },
    "powershell": {
        "path": ".github/workflows/lint/powershell.yml",
        "inputs": {
            "psscriptanalyzer-version": "1.24.0",
            "working-directory": "scripts",
            "settings-path": ".PSScriptAnalyzerSettings.psd1",
        },
    },
    "markdown": {
        "path": ".github/workflows/lint/markdown.yml",
        "inputs": {
            "node-version": "22.15.0",
            "markdownlint-cli2-version": "0.17.2",
            "working-directory": ".",
            "markdown-paths": "README.md\n      docs/**/*.md",
        },
    },
    "terraform": {
        "path": ".github/workflows/lint/terraform.yml",
        "inputs": {"terraform-version": "1.11.4", "working-directory": "infra"},
    },
    "helm": {
        "path": ".github/workflows/lint/helm.yml",
        "inputs": {"helm-version": "3.17.3", "chart-path": "charts/example"},
    },
}
CALLER_FRONTMATTER = {
    "issue-triage": """on:
  issues:
    types: [opened, reopened]
permissions:
  issues: read
tools:
  github:
    toolsets: [issues, labels]
    allowed: [issue_read, list_labels]""",
    "ci-failure-diagnosis": """on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    branches: [main]
permissions:
  actions: read
  issues: read
tools:
  github:
    toolsets: [actions, issues, search]
    allowed: [actions_get, actions_list, get_job_logs, search_issues]""",
    "test-quality": """on:
  workflow_dispatch:
permissions:
  contents: read
tools:
  github:
    toolsets: [repos]
    allowed: [get_file_contents]""",
    "documentation-upkeep": """on:
  workflow_dispatch:
permissions:
  contents: read
tools:
  github:
    toolsets: [repos]
    allowed: [get_commit, get_file_contents, list_commits]""",
}

EXPECTED_GITHUB_TOOLS = {
    "issue-triage": {"issue_read", "list_labels"},
    "ci-failure-diagnosis": {
        "actions_get",
        "actions_list",
        "get_job_logs",
        "search_issues",
    },
    "test-quality": {"get_file_contents"},
    "documentation-upkeep": {"get_commit", "get_file_contents", "list_commits"},
}
TEST_ALLOWED_FILES = [
    "tests/**",
    "test/**",
    "**/tests/**",
    "**/test/**",
    "**/*_test.*",
    "**/test_*.*",
    "**/*.test.*",
    "**/*.spec.*",
    "**/*Tests.cs",
    "**/*Test.cs",
    "**/*.tftest.hcl",
]
DOCUMENTATION_ALLOWED_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "docs/*.md",
    "docs/**/*.md",
    "doc/*.md",
    "doc/**/*.md",
]


def generated_job_permissions(lock_text):
    lines = lock_text.splitlines()
    try:
        jobs_start = lines.index("jobs:")
    except ValueError:
        raise SystemExit("generated gh-aw lock has no jobs section")

    permissions = {}
    current_job = None
    index = jobs_start + 1
    while index < len(lines):
        line = lines[index]
        if line and not line.startswith(" "):
            break
        if re.fullmatch(r"  [A-Za-z0-9_-]+:", line):
            current_job = line.strip()[:-1]
        elif current_job and line == "    permissions:":
            scopes = {}
            index += 1
            while index < len(lines) and lines[index].startswith("      "):
                match = re.fullmatch(r"      ([A-Za-z0-9_-]+): ([A-Za-z]+)", lines[index])
                if match:
                    scopes[match.group(1)] = match.group(2)
                index += 1
            permissions[current_job] = scopes
            continue
        index += 1
    return permissions


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--catalog-ref")
    source.add_argument("--catalog-directory", type=pathlib.Path)
    args = parser.parse_args()
    if args.catalog_ref and not re.fullmatch(r"[0-9a-f]{40}", args.catalog_ref):
        raise SystemExit("--catalog-ref must be a full lowercase 40-character commit SHA")

    if args.catalog_ref:
        for path in (
            ".github/workflows/run-checked-script.yml",
            ".github/actions/run-checked-script/action.yml",
            ".github/actions/check-python-syntax/action.yml",
            ".github/actions/validate-repository-directory/action.yml",
            *[item["path"] for item in LINT_WORKFLOWS.values()],
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
    else:
        args.catalog_directory = args.catalog_directory.resolve(strict=True)

    with tempfile.TemporaryDirectory(prefix="workflow-catalog-test-") as temp:
        workflow_dir = pathlib.Path(temp) / ".github" / "workflows"
        workflow_dir.mkdir(parents=True)
        local_import_dir = workflow_dir / "shared" / "agentic"
        local_import_dir.mkdir(parents=True)
        for name, expected in PATTERNS.items():
            if args.catalog_ref:
                imported_path = (
                    "DevOpsDerek/workflows/.github/workflows/shared/agentic/"
                    f"{name}.md@{args.catalog_ref}"
                )
            else:
                shutil.copyfile(
                    args.catalog_directory / ".github" / "workflows" / "shared" / "agentic" / f"{name}.md",
                    local_import_dir / f"{name}.md",
                )
                imported_path = f"shared/agentic/{name}.md"
            (workflow_dir / f"{name}.md").write_text(
                f"""---
{CALLER_FRONTMATTER[name]}
inlined-imports: true
imports:
  - {imported_path}
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
            lock_text = lock_file.read_text(encoding="utf-8")
            manifest_match = re.search(r"^# gh-aw-manifest: (.+)$", lock_text, re.MULTILINE)
            if not manifest_match:
                raise SystemExit(f"{lock_file.name} has no generated gh-aw manifest")
            manifest = json.loads(manifest_match.group(1))
            github_server = next(
                (server for server in manifest["mcp_servers"] if server["name"] == "github"),
                None,
            )
            actual_tools = set(github_server["tools"]) if github_server else set()
            if actual_tools != EXPECTED_GITHUB_TOOLS[name]:
                raise SystemExit(
                    f"{name} generated GitHub tool allowlist does not match: "
                    f"expected {EXPECTED_GITHUB_TOOLS[name]}, found {actual_tools}"
                )
            print(f"verified immutable import and inlined lock: {name}")

        expected_handlers = {
            "issue-triage": {"add_comment"},
            "ci-failure-diagnosis": {"create_issue"},
            "test-quality": {"create_pull_request"},
            "documentation-upkeep": {"create_pull_request"},
        }
        expected_config = {
            "issue-triage": {
                "add_comment": {"max": 1, "target": "triggering"},
            },
            "ci-failure-diagnosis": {
                "create_issue": {"max": 1, "title_prefix": "[CI diagnosis] "},
            },
        }
        system_issue_handlers = {
            "create_missing_tool_issue",
            "create_missing_data_issue",
            "create_report_incomplete_issue",
        }
        for name, expected in expected_handlers.items():
            lock_text = (workflow_dir / f"{name}.lock.yml").read_text(encoding="utf-8")
            match = re.search(
                r'GH_AW_SAFE_OUTPUTS_CONFIG:\s*("(?:\\.|[^"])*")',
                lock_text,
            )
            if not match:
                raise SystemExit(f"{name} lock has no generated safe-output configuration")
            config = json.loads(json.loads(match.group(1)))
            actual = set(config) & {
                "add_comment",
                "create_issue",
                "create_pull_request",
            }
            if actual != expected:
                raise SystemExit(
                    f"{name} safe-output handlers do not match: expected {expected}, "
                    f"found {actual}"
                )
            for handler, options in expected_config.get(name, {}).items():
                if config.get(handler) != options:
                    raise SystemExit(
                        f"{name} {handler} configuration does not match: "
                        f"expected {options}, found {config.get(handler)}"
                    )
            if system_issue_handlers & set(config):
                raise SystemExit(f"{name} lock enabled an issue-producing system handler")
            if "queue: max" not in lock_text:
                raise SystemExit(
                    f"{name} lock does not exercise the concurrency.queue compatibility case"
                )
            jobs = generated_job_permissions(lock_text)
            agent_permissions = jobs.get("agent")
            if not agent_permissions or any(
                level == "write" for level in agent_permissions.values()
            ):
                raise SystemExit(
                    f"{name} agent job must have generated read-only permissions, "
                    f"found {agent_permissions}"
                )
            writable_jobs = {
                job: scopes
                for job, scopes in jobs.items()
                if any(level == "write" for level in scopes.values())
            }
            expected_write_scopes = {
                "issue-triage": {
                    "safe_outputs": {"issues": "write", "pull-requests": "write"},
                    "conclusion": {"issues": "write", "pull-requests": "write"},
                },
                "ci-failure-diagnosis": {
                    "safe_outputs": {"issues": "write"},
                    "conclusion": {"issues": "write"},
                },
                "test-quality": {
                    "safe_outputs": {"contents": "write", "pull-requests": "write"},
                    "conclusion": {"contents": "write", "pull-requests": "write"},
                },
                "documentation-upkeep": {
                    "safe_outputs": {"contents": "write", "pull-requests": "write"},
                    "conclusion": {"contents": "write", "pull-requests": "write"},
                },
            }[name]
            if writable_jobs != expected_write_scopes:
                raise SystemExit(
                    f"{name} generated write permissions do not match the safe-output "
                    f"contract: expected {expected_write_scopes}, found {writable_jobs}"
                )
        for name in ("test-quality", "documentation-upkeep"):
            lock_text = (workflow_dir / f"{name}.lock.yml").read_text(encoding="utf-8")
            match = re.search(
                r'GH_AW_SAFE_OUTPUTS_CONFIG:\s*("(?:\\.|[^"])*")',
                lock_text,
            )
            config = json.loads(json.loads(match.group(1)))
            pull_request_config = config["create_pull_request"]
            if pull_request_config.get("draft") is not True or pull_request_config.get("fallback_as_issue") is not False:
                raise SystemExit(f"{name} lock lost draft-only PR restrictions")
            expected_files = (
                TEST_ALLOWED_FILES
                if name == "test-quality"
                else DOCUMENTATION_ALLOWED_FILES
            )
            if pull_request_config.get("allowed_files") != expected_files:
                raise SystemExit(
                    f"{name} lock lost its exclusive file allowlist: "
                    f"expected {expected_files}, found {pull_request_config.get('allowed_files')}"
                )
            if name == "documentation-upkeep" and pull_request_config.get("protected_files_policy") != "allowed":
                raise SystemExit(
                    "documentation-upkeep lock does not allow its explicitly allowlisted "
                    "documentation files through the protected-files policy"
                )
            if "issues: write" in lock_text or "pull-requests: write" not in lock_text:
                raise SystemExit(f"{name} lock has unexpected write permissions")
            for explicit_disable in (
                'GH_AW_MISSING_TOOL_CREATE_ISSUE: "false"',
                'GH_AW_REPORT_INCOMPLETE_CREATE_ISSUE: "false"',
            ):
                if explicit_disable not in lock_text:
                    raise SystemExit(
                        f"{name} lock lost system issue-output restriction "
                        f"{explicit_disable!r}"
                    )

        if not args.catalog_ref:
            print("verified local safe-output and actionlint lock contracts")
            return

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
        (caller_dir / "python-syntax-action.yml").write_text(
            f"""name: Python syntax contract
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  syntax:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
      - uses: DevOpsDerek/workflows/.github/actions/check-python-syntax@{args.catalog_ref}
        with:
          python-version: 3.12.8
          source-path: tests/example.py
""",
            encoding="utf-8",
        )
        for name, contract in LINT_WORKFLOWS.items():
            input_lines = []
            for key, value in contract["inputs"].items():
                if "\n" in value:
                    input_lines.append(f"      {key}: |")
                    input_lines.extend(
                        f"        {line}" for line in value.splitlines()
                    )
                else:
                    input_lines.append(f"      {key}: {value}")
            inputs = "\n".join(input_lines)
            (caller_dir / f"lint-{name}.yml").write_text(
                f"""name: {name} lint contract
on:
  pull_request:
permissions:
  contents: read
jobs:
  lint:
    uses: DevOpsDerek/workflows/{contract["path"]}@{args.catalog_ref}
    with:
{inputs}
""",
                encoding="utf-8",
            )
        subprocess.run(
            [
                "go",
                "run",
                "github.com/rhysd/actionlint/cmd/actionlint@v1.7.12",
                "-no-color",
                str(caller_dir / "reusable-workflow.yml"),
                str(caller_dir / "composite-action.yml"),
                str(caller_dir / "python-syntax-action.yml"),
                *[
                    str(caller_dir / f"lint-{name}.yml")
                    for name in LINT_WORKFLOWS
                ],
            ],
            check=True,
        )
        print("verified SHA-pinned reusable workflow and composite-action caller YAML")


if __name__ == "__main__":
    main()
