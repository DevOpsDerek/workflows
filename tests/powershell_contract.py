#!/usr/bin/env python3
"""Execute the reusable workflow's analyzer block against multiple source files."""

import os
import pathlib
import subprocess
import tempfile


root = pathlib.Path(__file__).resolve().parents[1]
workflow = (root / ".github/workflows/lint-powershell.yml").read_text()
block = workflow.split("      - name: Analyze PowerShell sources\n", 1)[1]
script = block.split("        run: |\n", 1)[1]
script = "\n".join(line[10:] for line in script.splitlines())


def analyze(directory, settings=""):
    return subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, "TARGET": str(directory), "SETTINGS": str(settings)},
        capture_output=True,
        text=True,
        check=False,
    )


with tempfile.TemporaryDirectory(prefix="powershell-contract-") as temp:
    directory = pathlib.Path(temp)
    first = directory / "first.ps1"
    second = directory / "second.ps1"
    first.write_text("Write-Output 'first'\n")
    second.write_text("Write-Output 'second'\n")
    result = analyze(directory)
    if result.returncode != 0:
        raise SystemExit(f"Multiple valid scripts rejected:\n{result.stdout}\n{result.stderr}")

    second.write_text("function Get-Result { $unused = 1 }\n")
    result = analyze(directory)
    if result.returncode == 0:
        raise SystemExit("A diagnostic in the second source file did not fail analysis")
    if "PSUseDeclaredVarsMoreThanAssignments" not in result.stdout:
        raise SystemExit(f"Expected analyzer diagnostic not reported:\n{result.stdout}\n{result.stderr}")

    first.unlink()
    second.unlink()
    result = analyze(directory)
    if result.returncode == 0:
        raise SystemExit("An empty source directory was incorrectly accepted")

print("Verified multi-file PowerShell success, diagnostic failure, and empty-directory failure")
