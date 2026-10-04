#!/usr/bin/env python3
"""Exercise the shared repository-path action's success and rejection behavior."""

import os
import pathlib
import subprocess
import tempfile
import unittest


SCRIPT = (
    pathlib.Path(__file__).resolve().parents[1]
    / ".github"
    / "actions"
    / "validate-repository-directory"
    / "validate.py"
)


class RepositoryPathValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="repository-path-test-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = pathlib.Path(self.temp.name) / "checkout"
        self.workspace.mkdir()
        (self.workspace / "src").mkdir()
        (self.workspace / "src" / "main.py").write_text("pass\n", encoding="utf-8")
        self.output = pathlib.Path(self.temp.name) / "github-output"

    def validate(self, path, kind="directory"):
        env = os.environ.copy()
        env.update(
            {
                "WORKSPACE_ROOT": str(self.workspace),
                "REPOSITORY_PATH": path,
                "PATH_NAME": "test-path",
                "PATH_KIND": kind,
                "GITHUB_OUTPUT": str(self.output),
            }
        )
        self.output.unlink(missing_ok=True)
        return subprocess.run(
            ["python3", str(SCRIPT)],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_accepts_repository_root_and_child_directory(self):
        for path in (".", "src"):
            with self.subTest(path=path):
                result = self.validate(path)
                self.assertEqual(result.returncode, 0, result.stderr)
                expected = (self.workspace / path).resolve()
                self.assertEqual(
                    self.output.read_text(encoding="utf-8"),
                    f"absolute-path={expected}\n",
                )

    def test_accepts_repository_file_when_requested(self):
        result = self.validate("src/main.py", kind="file")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.output.read_text(encoding="utf-8"),
            f"absolute-path={(self.workspace / 'src/main.py').resolve()}\n",
        )

    def test_rejects_traversal_absolute_missing_and_newline_paths(self):
        for path in ("../outside", "src/../main.py", str(self.workspace), "bad\npath"):
            with self.subTest(path=path):
                result = self.validate(path)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.exists())

    def test_rejects_symlink_escape(self):
        outside = pathlib.Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.workspace / "escape").symlink_to(outside, target_is_directory=True)
        result = self.validate("escape")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inside the checked-out repository", result.stderr)

    def test_rejects_wrong_target_kind_and_unknown_kind(self):
        for path, kind in (("src", "file"), ("src/main.py", "directory"), ("src", "other")):
            with self.subTest(path=path, kind=kind):
                result = self.validate(path, kind)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.exists())

    def test_rejects_nonexistent_path(self):
        result = self.validate("missing")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
