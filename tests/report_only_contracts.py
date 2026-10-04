#!/usr/bin/env python3
"""Validate report-only proposals and reproduce the pinned compiler blocker."""

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

from catalog_imports import generated_job_permissions

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / ".github/workflows/shared/agentic"
CONTRACTS = (
    "ci-failure-report", "platform-pr-report",
    "test-lesson-report", "documentation-drift-report",
)
POLICY = """permissions: {}
checkout: false
network:
  allowed: []
tools:
  github: false
  edit: false
  bash: []
safe-outputs:
  report-failed-jobs: false
  report-failure-as-issue: false
  missing-tool: false
  missing-data: false
  report-incomplete: false
  noop: false
  threat-detection: false"""


def validate_component(text):
    if not text.startswith(f"---\n{POLICY}\n---\n"):
        raise ValueError("component must match the trigger-free report-only source policy")


def validate_evidence_path(path, approved, excluded):
    """Check metadata only; never open or print the referenced evidence."""
    if not isinstance(path, str) or not re.fullmatch(r"[A-Za-z0-9_./-]+", path):
        raise ValueError("evidence requires a literal repository-relative path")
    parts = path.lower().split("/")
    sensitive = {
        ".aws", ".azure", ".gcloud", ".kube", ".ssh", "data", "exports",
        "backups", "dumps", "private", "customer", "customers", "secrets",
        "credentials", "location", "locations", "location-history", "live-data",
    }
    if any(part in {"", ".", ".."} or part in sensitive or
           part.startswith(".env") or
           re.search(r"(^|[._-])(secrets?|credentials?|locations?|tfstate|tfplan)([._-]|$)", part)
           for part in parts) or parts[-1].endswith((".pem", ".key", ".p12", ".pfx", ".kubeconfig")):
        raise ValueError("sensitive or traversing evidence path")
    if path not in approved or any(path == item or path.startswith(item.rstrip("/") + "/")
                                   for item in excluded):
        raise ValueError("evidence path must be explicitly approved and not excluded")


def validate_generated_lock(text):
    jobs = generated_job_permissions(text)
    if not jobs or "agent" not in jobs:
        raise ValueError("generated lock must declare agent permissions")
    if any(level not in {"read", "none"} for scopes in jobs.values() for level in scopes.values()):
        raise ValueError("generated lock grants write permissions")
    if re.search(r"^  safe_outputs:|GH_AW_SAFE_OUTPUTS_CONFIG:", text, re.MULTILINE):
        raise ValueError("generated lock enables safe outputs")
    matches = re.findall(r"^# gh-aw-manifest: (.+)$", text, re.MULTILINE)
    if len(matches) != 1 or json.loads(matches[0]).get("mcp_servers"):
        raise ValueError("generated lock exposes tools or lacks its compiler manifest")


class ReportOnlyTests(unittest.TestCase):
    def test_central_sources(self):
        for name in CONTRACTS:
            with self.subTest(contract=name):
                text = (COMPONENTS / f"{name}.md").read_text(encoding="utf-8")
                validate_component(text)
                self.assertIn("compiler-blocked", text)
                self.assertIn("ordinary agent response only", text)
                self.assertIn("untrusted data", text)
                self.assertIn("insufficient evidence is not a clean result", text)

    def test_capability_overrides(self):
        fixtures = json.loads((ROOT / "tests/fixtures/report-only/prohibited.json").read_text())
        for case in fixtures["caller_overrides"]:
            with self.subTest(capability=case["name"]):
                with self.assertRaises(ValueError):
                    validate_component(f"---\n{POLICY}\n{case['frontmatter']}---\n")

    def test_sensitive_paths_even_when_allowlisted(self):
        fixtures = json.loads((ROOT / "tests/fixtures/report-only/prohibited.json").read_text())
        for path in fixtures["prohibited_paths"]:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    validate_evidence_path(path, [path], [])

    def test_reviewed_paths(self):
        for path in ("docs/lesson.md", "tests/lesson_test.py", "infra/main.tf", ".github/workflows/ci.yml"):
            validate_evidence_path(path, [path], ["data", "exports"])
        with self.assertRaises(ValueError):
            validate_evidence_path("docs/lesson.md", [], [])
        with self.assertRaises(ValueError):
            validate_evidence_path("docs/lesson.md", ["docs/lesson.md"], ["docs"])

    def test_generated_capability_fixtures(self):
        # These are parser unit-test excerpts, not runnable or published locks.
        readonly = (
            '# gh-aw-manifest: {"mcp_servers": []}\n'
            "jobs:\n  agent:\n    permissions:\n      contents: read\n"
        )
        validate_generated_lock(readonly)
        for scope in ("issues", "pull-requests", "contents", "actions", "id-token"):
            with self.subTest(scope=scope), self.assertRaisesRegex(ValueError, "write permissions"):
                validate_generated_lock(readonly + f"      {scope}: write\n")
        with self.assertRaisesRegex(ValueError, "safe outputs"):
            validate_generated_lock(readonly + "  safe_outputs:\n    permissions:\n      contents: read\n")
        with self.assertRaisesRegex(ValueError, "safe outputs"):
            validate_generated_lock(readonly + 'GH_AW_SAFE_OUTPUTS_CONFIG: "{}"\n')
        with self.assertRaisesRegex(ValueError, "exposes tools"):
            validate_generated_lock(readonly.replace('"mcp_servers": []', '"mcp_servers": [{"name": "github"}]'))


def compiler_regression(catalog_ref):
    version = subprocess.check_output(
        ["gh", "aw", "--version"], text=True, stderr=subprocess.STDOUT,
    ).strip()
    if version != "gh aw version v0.89.21":
        raise SystemExit(f"regression requires supported compiler v0.89.21, found {version}")
    if catalog_ref and not re.fullmatch(r"[0-9a-f]{40}", catalog_ref):
        raise SystemExit("--catalog-ref must be a full immutable commit SHA")
    with tempfile.TemporaryDirectory(prefix="report-only-regression-") as temp:
        workflows = pathlib.Path(temp) / ".github/workflows"
        shared = workflows / "shared/agentic"
        shared.mkdir(parents=True)
        for name in CONTRACTS:
            shutil.copyfile(COMPONENTS / f"{name}.md", shared / f"{name}.md")
            imported = (
                f"DevOpsDerek/workflows/.github/workflows/shared/agentic/{name}.md@{catalog_ref}"
                if catalog_ref else f"shared/agentic/{name}.md"
            )
            (workflows / f"{name}.md").write_text(
                f"---\non:\n  workflow_dispatch:\ninlined-imports: true\nimports:\n"
                f"  - {imported}\n---\n\nUse only supplied redacted evidence.\n",
                encoding="utf-8",
            )
        subprocess.run(["git", "init", "--quiet"], cwd=temp, check=True)
        subprocess.run(
            ["gh", "aw", "compile", "--validate", "--actionlint", "--no-check-update"],
            cwd=temp, check=True,
        )
        for name in CONTRACTS:
            text = (workflows / f"{name}.lock.yml").read_text(encoding="utf-8")
            if "ordinary agent response only" not in text:
                raise SystemExit(f"{name}: import was not inlined")
            match = re.search(r'GH_AW_SAFE_OUTPUTS_CONFIG:\s*("(?:\\.|[^"])*")', text)
            if not match or "create_issue" not in json.loads(json.loads(match.group(1))):
                raise SystemExit(f"{name}: compiler behavior changed; re-evaluate blocker")
            try:
                validate_generated_lock(text)
            except ValueError as error:
                if str(error) != "generated lock grants write permissions":
                    raise
                print(f"EXPECTED BLOCKER: {name}: {error}; injected create_issue")
            else:
                raise SystemExit(f"{name}: unsafe compiler lock was accepted")
    print("Compiler regression confirmed; no runnable locks retained or published.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compile", action="store_true")
    parser.add_argument("--catalog-ref")
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ReportOnlyTests)
    )
    if not result.wasSuccessful():
        raise SystemExit(1)
    if args.compile or args.catalog_ref:
        compiler_regression(args.catalog_ref)
