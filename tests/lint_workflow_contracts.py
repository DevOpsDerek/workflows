#!/usr/bin/env python3
"""Check published lint workflow signatures and safety invariants."""

import pathlib
import re
import json
import os
import subprocess
import tempfile
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACTS = {
    "python-ruff": {
        "python-version": "3.12.8",
        "ruff-version": "0.11.13",
        "working-directory": ".",
    },
    "go": {
        "go-version": "1.24.2",
        "golangci-lint-version": "1.64.8",
        "working-directory": ".",
    },
    "rust": {"rust-version": "1.86.0", "working-directory": "."},
    "shell": {"shellcheck-version": "0.10.0", "working-directory": "."},
    "powershell": {
        "psscriptanalyzer-version": "1.24.0",
        "working-directory": ".",
        "settings-path": "",
    },
    "markdown": {
        "node-version": "22.15.0",
        "markdownlint-cli2-version": "0.17.2",
        "working-directory": ".",
        "markdown-paths": "**/*.md",
    },
    "terraform": {"terraform-version": "1.11.4", "working-directory": "."},
    "helm": {"helm-version": "3.17.3", "chart-path": None},
}
ACTION_REF = re.compile(
    r"^\s+uses:\s+[^@\s]+@([^\s]+)\s*$", re.MULTILINE
)


def input_contract(text):
    match = re.search(
        r"^    inputs:\n(.*?)(?=^permissions:)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise AssertionError("workflow_call inputs block not found")
    inputs = {}
    current = None
    for line in match.group(1).splitlines():
        name = re.match(r"^      ([a-z0-9-]+):\s*$", line)
        if name:
            current = name.group(1)
            inputs[current] = {}
        elif current and (field := re.match(r"^        (type|required|default):\s*(.*)$", line)):
            value = field.group(2).strip().strip("\"'")
            inputs[current][field.group(1)] = value
    return inputs


class LintWorkflowContractTests(unittest.TestCase):
    def test_reusable_workflows_are_top_level(self):
        workflows = ROOT / ".github/workflows"
        for path in workflows.rglob("*.yml"):
            if "  workflow_call:" in path.read_text(encoding="utf-8"):
                with self.subTest(workflow=str(path.relative_to(ROOT))):
                    self.assertEqual(path.parent, workflows)

    def test_workflow_signatures_and_defaults(self):
        self.assertEqual(set(CONTRACTS), {
            path.stem.removeprefix("lint-")
            for path in (ROOT / ".github/workflows").glob("lint-*.yml")
        })
        for name, expected in CONTRACTS.items():
            with self.subTest(workflow=name):
                text = (
                    ROOT / ".github/workflows" / f"lint-{name}.yml"
                ).read_text(encoding="utf-8")
                self.assertIn("on:\n  workflow_call:\n", text)
                actual = input_contract(text)
                self.assertEqual(set(actual), set(expected))
                self.assertIn("contents: read", text)
                self.assertNotIn("contents: write", text)
                self.assertNotIn("secrets.", text)
                self.assertNotIn("safe_outputs", text)
                self.assertTrue(ACTION_REF.findall(text))
                self.assertTrue(all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in ACTION_REF.findall(text)))
                for key, default in expected.items():
                    self.assertEqual(actual[key].get("type"), "string")
                    if default is None:
                        self.assertEqual(actual[key].get("required"), "true")
                    else:
                        self.assertEqual(actual[key].get("required"), "false")
                        self.assertEqual(actual[key].get("default"), default)

    def test_caller_inputs_are_not_interpolated_as_shell(self):
        for path in (ROOT / ".github/workflows").glob("lint-*.yml"):
            with self.subTest(workflow=path.name):
                in_run_block = False
                for line in path.read_text(encoding="utf-8").splitlines():
                    if re.match(r"^      run:\s*[|>]", line):
                        in_run_block = True
                        continue
                    if in_run_block and line and len(line) - len(line.lstrip()) <= 6:
                        in_run_block = False
                    if in_run_block:
                        self.assertNotIn("${{ inputs.", line)

    def test_known_consumer_contracts_and_failure_modes(self):
        python = (ROOT / ".github/workflows/lint-python-ruff.yml").read_text()
        go = (ROOT / ".github/workflows/lint-go.yml").read_text()
        shell = (ROOT / ".github/workflows/lint-shell.yml").read_text()
        powershell = (ROOT / ".github/workflows/lint-powershell.yml").read_text()
        terraform = (ROOT / ".github/workflows/lint-terraform.yml").read_text()
        markdown = (ROOT / ".github/workflows/lint-markdown.yml").read_text()
        self.assertIn("ruff check --no-fix .", python)
        self.assertIn("ruff format --check .", python)
        self.assertIn("releases/download/v$LINTER_VERSION", go)
        self.assertIn("1.*|2.*)", go)
        self.assertIn("shellcheck --shell=bash", shell)
        self.assertIn("$diagnostics.Count -gt 0", powershell)
        self.assertIn("exit 1", powershell)
        self.assertIn("-lockfile=readonly", terraform)
        self.assertIn('mapfile -t patterns <<< "$MARKDOWN_PATHS"', markdown)
        self.assertIn('args+=("$pattern")', markdown)
        self.assertIn('markdownlint-cli2 "${args[@]}"', markdown)
        self.assertIn('markdown-paths entries must not contain parent-directory components.', markdown)

    def test_markdown_globs_are_validated_and_passed_as_literal_arguments(self):
        workflow = (ROOT / ".github/workflows/lint-markdown.yml").read_text()
        lines = workflow.split("      - name: Lint Markdown\n", 1)[1].splitlines()
        start = lines.index("        run: |") + 1
        script_lines = []
        for line in lines[start:]:
            if line and len(line) - len(line.lstrip()) <= 8:
                break
            script_lines.append(line[10:] if line.startswith("          ") else "")
        script = textwrap.dedent("\n".join(script_lines))

        with tempfile.TemporaryDirectory(prefix="markdown-paths-test-") as temp:
            root = pathlib.Path(temp)
            binary_dir = root / "bin"
            binary_dir.mkdir()
            arguments_file = root / "arguments.json"
            fake_linter = binary_dir / "markdownlint-cli2"
            fake_linter.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "pathlib = __import__('pathlib')\n"
                "pathlib.Path(os.environ['ARGUMENTS_FILE']).write_text(json.dumps(sys.argv[1:]))\n",
                encoding="utf-8",
            )
            fake_linter.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{binary_dir}:{env['PATH']}",
                    "ARGUMENTS_FILE": str(arguments_file),
                }
            )
            valid = "README.md\ndocs/**/*.md"
            result = subprocess.run(
                ["bash", "-e", "-c", script],
                env={**env, "MARKDOWN_PATHS": valid},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(arguments_file.read_text()), valid.splitlines())

            marker = root / "should-not-exist"
            injected = f"README.md\n$(touch {marker})"
            result = subprocess.run(
                ["bash", "-e", "-c", script],
                env={**env, "MARKDOWN_PATHS": injected},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(marker.exists())
            self.assertEqual(
                json.loads(arguments_file.read_text()),
                ["README.md", f"$(touch {marker})"],
            )

            for invalid in ("", "../private.md", "/etc/passwd", "docs\\secret.md"):
                with self.subTest(invalid=invalid):
                    result = subprocess.run(
                        ["bash", "-e", "-c", script],
                        env={**env, "MARKDOWN_PATHS": invalid},
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
