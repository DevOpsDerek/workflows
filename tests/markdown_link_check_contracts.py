#!/usr/bin/env python3
"""Execute the reusable Markdown link checker against isolated callers."""

import http.server
import os
import pathlib
import platform
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from lint_workflow_contracts import ACTION_REF, input_contract


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/markdown-link-check.yml").read_text(encoding="utf-8")


def embedded_script(step):
    lines = WORKFLOW.split(f"      - name: {step}\n", 1)[1].splitlines()
    start = lines.index("        run: |") + 1
    script = []
    for line in lines[start:]:
        if line and not line.startswith("          "):
            break
        script.append(line[10:])
    return "\n".join(script)


CHECK = embedded_script("Check Markdown links")
NETWORK_BLOCKER = """
import socket
def _blocked(*args, **kwargs):
    raise AssertionError("network access attempted in network-free mode")
socket.socket.connect = _blocked
socket.create_connection = _blocked
socket.getaddrinfo = _blocked
"""


class Handler(http.server.BaseHTTPRequestHandler):
    counts = {}
    lock = threading.Lock()

    def do_GET(self):
        with self.lock:
            count = self.counts[self.path] = self.counts.get(self.path, 0) + 1
        statuses = {"/ok": 200, "/missing": 404, "/gone": 410, "/down": 503, "/limited": 429, "/forbidden": 403}
        if self.path == "/flaky":
            status = 503 if count == 1 else 200
        elif self.path == "/slow":
            time.sleep(3)
            status = 200
        elif self.path == "/redirect":
            self.send_response(301)
            self.send_header("Location", "/ok")
            self.end_headers()
            return
        else:
            status = statuses.get(self.path, 500)
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


class MarkdownLinkCheckContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.daemon_threads = True
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        with socket_for_closed_port() as port:
            cls.closed = f"http://127.0.0.1:{port}/closed"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Handler.counts.clear()
        self.temp = tempfile.TemporaryDirectory(prefix="markdown-links-contract-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.workspace = self.root / "caller"
        (self.workspace / "docs" / "images").mkdir(parents=True)
        (self.workspace / "docs" / "images" / "diagram one.png").write_bytes(b"png")
        (self.workspace / "docs" / "guide.md").write_text(
            "# Guide\n\nBack to [readme](../README.md#top) and [root](/README.md).\n", encoding="utf-8"
        )
        self.write("README.md", "# Top\n\n[Guide](docs/guide.md)\n")
        self.env = {
            **os.environ,
            "GITHUB_WORKSPACE": str(self.workspace),
            "PYTHON_VERSION": platform.python_version(),
            "WORKING_DIRECTORY": ".",
            "MARKDOWN_PATHS": "**/*.md",
            "EXCLUDE_PATHS": "",
            "EXCLUDE_LINKS": "",
            "EXTERNAL_LINKS": "skip",
            "TIMEOUT_SECONDS": "1",
            "MAX_RETRIES": "1",
            "FAIL_ON_UNCONFIRMED": "false",
        }

    def write(self, relative, text):
        path = self.workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_check(self, block_network=False, **overrides):
        env = {**self.env, **overrides}
        if block_network:
            blocker = self.root / "blocker"
            blocker.mkdir(exist_ok=True)
            (blocker / "sitecustomize.py").write_text(NETWORK_BLOCKER, encoding="utf-8")
            env["PYTHONPATH"] = str(blocker)
        return subprocess.run(
            [sys.executable, "-c", CHECK], env=env, cwd=self.root,
            capture_output=True, text=True, check=False, timeout=120,
        )

    def test_signature_and_security_contract(self):
        actual = input_contract(WORKFLOW)
        self.assertEqual(actual, {
            "python-version": {"required": "false", "type": "string", "default": "3.12.8"},
            "working-directory": {"required": "false", "type": "string", "default": "."},
            "markdown-paths": {"required": "false", "type": "string", "default": "**/*.md"},
            "exclude-paths": {"required": "false", "type": "string", "default": ""},
            "exclude-links": {"required": "false", "type": "string", "default": ""},
            "external-links": {"required": "false", "type": "string", "default": "skip"},
            "timeout-seconds": {"required": "false", "type": "number", "default": "10"},
            "max-retries": {"required": "false", "type": "number", "default": "2"},
            "fail-on-unconfirmed": {"required": "false", "type": "boolean", "default": "false"},
        })
        self.assertIn("on:\n  workflow_call:\n", WORKFLOW)
        self.assertEqual(re.findall(r"^\s+(\w[\w-]*): (read|write)$", WORKFLOW, re.MULTILINE),
                         [("contents", "read"), ("contents", "read")])
        self.assertIn("persist-credentials: false", WORKFLOW)
        self.assertNotIn("secrets", WORKFLOW)
        self.assertNotIn("github.token", WORKFLOW)
        self.assertNotIn("uses: ./", WORKFLOW)
        self.assertNotIn("${{", CHECK)
        self.assertNotIn("subprocess", CHECK)
        self.assertNotRegex(CHECK, r"\.write_text|open\([^)]*['\"][wa]")
        refs = ACTION_REF.findall(WORKFLOW)
        self.assertEqual(len(refs), 2)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in refs))
        self.assertIn("check-latest: false", WORKFLOW)

    def test_caller_example_uses_immutable_sha_placeholder(self):
        catalog = (ROOT / "docs/catalog.md").read_text(encoding="utf-8")
        section = catalog.split("## Check Markdown links\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn(
            "uses: DevOpsDerek/workflows/.github/workflows/markdown-link-check.yml@<40_CHARACTER_COMMIT_SHA>\n",
            section,
        )
        self.assertNotRegex(section, r"markdown-link-check\.yml@(?!<40_CHARACTER_COMMIT_SHA>)")
        self.assertIn("Limitations", section)

    def test_valid_local_links_pass(self):
        self.write("docs/more.md", "\n".join([
            "![Diagram](images/diagram%20one.png)",
            "![Diagram](<images/diagram one.png>)",
            "[Directory](images/) [Anchor only](#guide) [Query](guide.md?plain=1#guide)",
            "[ref]: ./guide.md \"Guide\"",
            "[^1]: Footnote text, not a link",
            '<a href="../README.md">readme</a> <img src="images/diagram%20one.png">',
            "[mail](mailto:someone@example.com)",
            "",
        ]))
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("::error", result.stdout)

    def test_missing_local_links_fail_with_file_and_line(self):
        self.write("docs/broken.md", "\n".join([
            "# Broken",
            "[missing](missing.md)",
            "![image](images/absent.png)",
            "[case](../readme.md)",
            "[escape](../../outside.md)",
            "[empty]()",
            "[ref]: nowhere/file.md",
            '<a href="gone.md">gone</a>',
            "",
        ]))
        result = self.run_check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        errors = [line for line in result.stdout.splitlines() if line.startswith("::error")]
        self.assertEqual(errors, [
            "::error file=docs/broken.md,line=2::Broken local link 'missing.md': target path does not exist (paths are case-sensitive)",
            "::error file=docs/broken.md,line=3::Broken local link 'images/absent.png': target path does not exist (paths are case-sensitive)",
            "::error file=docs/broken.md,line=4::Broken local link '../readme.md': target path does not exist (paths are case-sensitive)",
            "::error file=docs/broken.md,line=5::Broken local link '../../outside.md': target escapes the repository",
            "::error file=docs/broken.md,line=6::Broken local link '': empty link target",
            "::error file=docs/broken.md,line=7::Broken local link 'nowhere/file.md': target path does not exist (paths are case-sensitive)",
            "::error file=docs/broken.md,line=8::Broken local link 'gone.md': target path does not exist (paths are case-sensitive)",
        ])
        self.assertIn("broken=7", result.stdout)

    def test_code_comments_and_escapes_are_ignored(self):
        self.write("code.md", "\n".join([
            "```markdown", "[missing](missing.md)", "```",
            "~~~~", "[missing](missing.md)", "~~~~",
            "Inline `[missing](missing.md)` code.",
            "<!-- [missing](missing.md)", "-->",
            r"\[not a link\](missing.md)",
            "",
        ]))
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_exclusions(self):
        self.write("vendor/third-party.md", "[missing](missing.md)\n")
        self.write("docs/generated.md", "[api](api/missing.md) [ok](guide.md)\n")
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        result = self.run_check(EXCLUDE_PATHS="vendor/**\n\n", EXCLUDE_LINKS="api/\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("excluded=1", result.stdout)
        result = self.run_check(MARKDOWN_PATHS="docs/*.md\n", EXCLUDE_LINKS="api/")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.run_check(WORKING_DIRECTORY="docs", EXCLUDE_PATHS="generated.md")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_network_free_mode_never_opens_sockets(self):
        self.write("external.md", f"[ext]({self.base}/missing) <https://example.invalid/page>\n")
        result = self.run_check(block_network=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("skip (network-free)", result.stdout)
        self.assertIn("skipped=2", result.stdout)
        self.assertEqual(Handler.counts, {})
        result = self.run_check(block_network=True, EXTERNAL_LINKS="check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("network access attempted", result.stdout + result.stderr)

    def test_external_classification_retries_and_policy(self):
        b = self.base
        self.write("external.md", "\n".join([
            f"[ok]({b}/ok#section) [redirect]({b}/redirect) [flaky]({b}/flaky)",
            f"[down]({b}/down)",
            f"[limited]({b}/limited)",
            f"[forbidden]({b}/forbidden)",
            f"[slow]({b}/slow)",
            f"[closed]({self.closed})",
            "",
        ]))
        result = self.run_check(EXTERNAL_LINKS="check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        warnings = [line for line in result.stdout.splitlines() if line.startswith("::warning")]
        self.assertEqual(len(warnings), 5, result.stdout)
        self.assertIn(f"Transient failure for external link '{b}/down' after 2 attempt(s): HTTP 503; not confirmed broken", result.stdout)
        self.assertIn(f"'{b}/limited' after 2 attempt(s): HTTP 429", result.stdout)
        self.assertIn(f"Unverified for external link '{b}/forbidden' after 1 attempt(s): HTTP 403", result.stdout)
        self.assertIn(f"'{b}/slow' after 2 attempt(s): timed out", result.stdout)
        self.assertIn(f"'{self.closed}' after 2 attempt(s): connection error", result.stdout)
        self.assertNotIn("::error", result.stdout)
        self.assertEqual(Handler.counts["/flaky"], 2)
        self.assertEqual(Handler.counts["/forbidden"], 1)
        self.assertEqual(Handler.counts["/down"], 2)

        result = self.run_check(EXTERNAL_LINKS="check", FAIL_ON_UNCONFIRMED="true", MAX_RETRIES="0")
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn(f"::error file=external.md,line=2::Transient failure for external link '{b}/down' after 1 attempt(s)", result.stdout)

    def test_confirmed_broken_external_links_fail_regardless_of_policy(self):
        self.write("external.md", f"[missing]({self.base}/missing)\n[gone]({self.base}/gone)\n[bad](https://)\n")
        for policy in ("false", "true"):
            with self.subTest(policy=policy):
                result = self.run_check(EXTERNAL_LINKS="check", FAIL_ON_UNCONFIRMED=policy)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(f"::error file=external.md,line=1::Broken external link '{self.base}/missing': confirmed HTTP 404", result.stdout)
                self.assertIn(f"'{self.base}/gone': confirmed HTTP 410", result.stdout)
                self.assertIn("'https://': confirmed invalid URL", result.stdout)
        self.assertEqual(Handler.counts["/missing"], 2)

    def test_input_rejections_and_literal_handling(self):
        marker = self.root / "marker"
        invalid = {
            "PYTHON_VERSION": ["0.0.1"],
            "WORKING_DIRECTORY": ["", "/tmp", "../caller", "docs/../docs", "docs/", "missing", "docs\\images"],
            "MARKDOWN_PATHS": ["", "\n", "/etc/*.md", "../*.md", "docs\\*.md", " README.md", "missing/*.md"],
            "EXCLUDE_PATHS": ["../x", "**/*.md"],
            "EXCLUDE_LINKS": ["bad\x01prefix"],
            "EXTERNAL_LINKS": ["", "on", "true"],
            "TIMEOUT_SECONDS": ["0", "61", "1.5", "-1", "ten"],
            "MAX_RETRIES": ["6", "-1", "1.0"],
            "FAIL_ON_UNCONFIRMED": ["yes", ""],
        }
        for key, values in invalid.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    result = self.run_check(**{key: value})
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertIn("::error::", result.stdout)
        (self.workspace / "linked").symlink_to(self.workspace / "docs", target_is_directory=True)
        self.assertEqual(self.run_check(WORKING_DIRECTORY="linked").returncode, 2)
        outside = self.root / "outside.md"
        outside.write_text("# outside\n", encoding="utf-8")
        (self.workspace / "escape.md").symlink_to(outside)
        self.assertEqual(self.run_check().returncode, 2)
        (self.workspace / "escape.md").unlink()
        self.write("$(touch marker); x.md", "[guide](docs/guide.md)\n")
        result = self.run_check(MARKDOWN_PATHS="$(touch marker); x.md")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("checked=1", result.stdout)
        self.assertFalse(marker.exists())
        self.assertFalse((self.workspace / "marker").exists())

    def test_annotation_values_are_escaped(self):
        self.write("a,b:c.md", "[bad](missing%0A::error::x.md)\n")
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("::error file=a%2Cb%3Ac.md,line=1::Broken local link 'missing%250A::error::x.md'", result.stdout)
        self.assertEqual(len(result.stdout.splitlines()), 3, result.stdout)


class socket_for_closed_port:
    def __enter__(self):
        import socket
        self.socket = socket.socket()
        self.socket.bind(("127.0.0.1", 0))
        return self.socket.getsockname()[1]

    def __exit__(self, *args):
        self.socket.close()


if __name__ == "__main__":
    unittest.main()
