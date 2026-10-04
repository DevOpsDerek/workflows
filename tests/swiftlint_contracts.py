#!/usr/bin/env python3
"""Execute the reusable workflow's embedded Python against isolated callers."""

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from lint_workflow_contracts import ACTION_REF, input_contract


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/swiftlint.yml").read_text(encoding="utf-8")


def embedded_script(step):
    lines = WORKFLOW.split(f"      - name: {step}\n", 1)[1].splitlines()
    start = lines.index("        run: |") + 1
    script = []
    for line in lines[start:]:
        if line and not line.startswith("          "):
            break
        script.append(line[10:])
    return "\n".join(script)


VALIDATE = embedded_script("Validate versions, configuration, and source roots")
LINT = embedded_script("Lint only the validated Swift sources")


class SwiftLintContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="swiftlint-contract-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.workspace = self.root / "caller"
        self.workspace.mkdir()
        fixtures = ROOT / "tests/fixtures/swiftlint"
        for fixture, directory in (("App", "Supercar"), ("Tests", "SupercarTests")):
            shutil.copytree(fixtures / fixture, self.workspace / directory)
        shutil.copyfile(fixtures / ".swiftlint.yml", self.workspace / ".swiftlint.yml")
        self.manifest = self.root / "swiftlint-inputs.json"
        self.env = {
            **os.environ,
            "GITHUB_WORKSPACE": str(self.workspace),
            "RUNNER_TEMP": str(self.root),
            "SWIFTLINT_VERSION": "0.65.1",
            "XCODE_VERSION": "16.4",
            "SOURCE_ROOTS": '["Supercar", "SupercarTests"]',
            "CONFIG_PATH": ".swiftlint.yml",
            "STRICT": "true",
        }

    def run_script(self, script, **overrides):
        return subprocess.run(
            [sys.executable, "-c", script], env={**self.env, **overrides},
            capture_output=True, text=True, check=False,
        )

    def test_signature_and_security_contract(self):
        actual = input_contract(WORKFLOW)
        self.assertEqual(set(actual), {
            "swiftlint-version", "xcode-version", "source-roots", "config-path", "strict",
        })
        self.assertEqual(actual["swiftlint-version"]["default"], "0.65.1")
        self.assertEqual(actual["xcode-version"]["default"], "16.4")
        self.assertEqual(actual["strict"]["type"], "boolean")
        for key in ("source-roots", "config-path"):
            self.assertEqual(actual[key]["required"], "true")
        self.assertIn("runs-on: macos-15", WORKFLOW)
        self.assertIn("persist-credentials: false", WORKFLOW)
        self.assertEqual(re.findall(r"^\s+contents: (\w+)$", WORKFLOW, re.MULTILINE), ["read", "read"])
        self.assertNotIn("secrets", WORKFLOW)
        self.assertNotIn("${{", VALIDATE + LINT)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in ACTION_REF.findall(WORKFLOW)))
        self.assertIn('releases/download/$SWIFTLINT_VERSION/portable_swiftlint.zip', WORKFLOW)
        self.assertIn('[[ "$("$install_dir/tool/swiftlint" version)" == "$SWIFTLINT_VERSION" ]]', WORKFLOW)
        self.assertIn('[[ "$actual" == "Xcode $XCODE_VERSION" ]]', WORKFLOW)

    def test_caller_example_uses_immutable_top_level_workflow_and_both_roots(self):
        catalog = (ROOT / "docs/catalog.md").read_text(encoding="utf-8")
        section = catalog.split("## Lint Swift on macOS\n", 1)[1].split("\n## ", 1)[0]
        self.assertRegex(
            section,
            r"uses: DevOpsDerek/workflows/\.github/workflows/swiftlint\.yml@[0-9a-f]{40}\n",
        )
        self.assertIn('source-roots: \'["Supercar", "SupercarTests"]\'', section)
        self.assertIn("config-path: .swiftlint.yml", section)

    def test_exact_versions(self):
        for version in ("0.65.1", "1.2.3"):
            self.assertEqual(self.run_script(VALIDATE, SWIFTLINT_VERSION=version).returncode, 0)
        for key, invalid in (
            ("SWIFTLINT_VERSION", ("", "latest", "v0.65.1", "0.65", "0.65.1-beta", "0.65.1\n", "01.2.3", "$(touch marker)")),
            ("XCODE_VERSION", ("latest", "16", "../16.4", "16.4\n", "16.4; echo unsafe")),
        ):
            for value in invalid:
                with self.subTest(key=key, value=value):
                    self.manifest.unlink(missing_ok=True)
                    result = self.run_script(VALIDATE, **{key: value})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("::error::", result.stderr)
                    self.assertFalse(self.manifest.exists())

    def test_root_and_config_rejections(self):
        invalid_roots = [
            "", "not json", "[]", "{}", '"Supercar"', '["Supercar", "Supercar"]',
            '[null]', '[1]', '[""]', '["."]', '["/tmp"]', '["../caller"]',
            '["Supercar/../SupercarTests"]', '["Supercar/"]', '["Supercar//child"]',
            '["Supercar\\\\child"]', '["Super*"]', '["--fix"]', '["missing"]',
            '[".swiftlint.yml"]', '["Supercar\\n"]',
        ]
        for value in invalid_roots:
            with self.subTest(roots=value):
                self.assertNotEqual(self.run_script(VALIDATE, SOURCE_ROOTS=value).returncode, 0)
        for config in ("", "/tmp/config.yml", "../config.yml", "Supercar", "missing.yml"):
            with self.subTest(config=config):
                self.assertNotEqual(self.run_script(VALIDATE, CONFIG_PATH=config).returncode, 0)
        (self.workspace / "config.txt").write_text("disabled_rules: []")
        self.assertNotEqual(self.run_script(VALIDATE, CONFIG_PATH="config.txt").returncode, 0)

    def test_empty_roots_and_symlinks_rejected(self):
        (self.workspace / "empty").mkdir()
        self.assertNotEqual(self.run_script(VALIDATE, SOURCE_ROOTS='["Supercar", "empty"]').returncode, 0)
        (self.workspace / "linked").symlink_to(self.workspace / "Supercar", target_is_directory=True)
        self.assertNotEqual(self.run_script(VALIDATE, SOURCE_ROOTS='["linked"]').returncode, 0)
        (self.workspace / "linked.yml").symlink_to(self.workspace / ".swiftlint.yml")
        self.assertNotEqual(self.run_script(VALIDATE, CONFIG_PATH="linked.yml").returncode, 0)
        (self.workspace / "Supercar" / "escape.swift").symlink_to(self.root / "outside.swift")
        self.assertNotEqual(self.run_script(VALIDATE).returncode, 0)

    def test_nested_sources_and_literal_directory_names(self):
        directory = self.workspace / "App $(touch marker)"
        (directory / "Nested").mkdir(parents=True)
        source = directory / "Nested" / "Example.swift"
        source.write_text("let example = 1\n")
        result = self.run_script(VALIDATE, SOURCE_ROOTS=json.dumps([directory.name, f"{directory.name}/Nested"]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.manifest.read_text())["sources"], [str(source)])
        self.assertFalse((self.workspace / "marker").exists())

    def test_literal_arguments_multi_root_lint_only_and_failure_propagation(self):
        special = self.workspace / "Supercar" / "$(touch marker); space.swift"
        special.write_text("let example = 1\n")
        result = self.run_script(VALIDATE)
        self.assertEqual(result.returncode, 0, result.stderr)
        binary = self.root / "fake-swiftlint"
        binary.write_text(
            f"#!{sys.executable}\n"
            "import json, os, pathlib, sys\n"
            "count = int(os.environ['SCRIPT_INPUT_FILE_COUNT'])\n"
            "sources = [os.environ[f'SCRIPT_INPUT_FILE_{i}'] for i in range(count)]\n"
            "pathlib.Path(os.environ['RUNNER_TEMP'], 'invocation.json').write_text("
            "json.dumps({'args': sys.argv[1:], 'sources': sources, 'cwd': os.getcwd()}))\n"
            "sys.exit(int(os.environ.get('FAKE_EXIT', '0')))\n"
        )
        binary.chmod(0o755)
        for strict, exit_code in (("true", 0), ("false", 2)):
            result = self.run_script(LINT, SWIFTLINT_BINARY=str(binary), STRICT=strict, FAKE_EXIT=str(exit_code))
            self.assertEqual(result.returncode, exit_code, result.stderr)
            invocation = json.loads((self.root / "invocation.json").read_text())
            expected = [
                "lint", "--config", str(self.workspace / ".swiftlint.yml"),
                "--use-script-input-files", "--force-exclude", "--no-cache",
                "--reporter", "github-actions-logging",
            ] + (["--strict"] if strict == "true" else [])
            self.assertEqual(invocation["args"], expected)
            self.assertEqual(invocation["cwd"], str(self.workspace))
            self.assertEqual(invocation["sources"], sorted([
                str(self.workspace / "Supercar" / "Example.swift"),
                str(self.workspace / "SupercarTests" / "ExampleTests.swift"),
                str(special),
            ]))
            self.assertFalse((self.workspace / "marker").exists())
        self.assertEqual(special.read_text(), "let example = 1\n")


if __name__ == "__main__":
    unittest.main()
