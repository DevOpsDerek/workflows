#!/usr/bin/env python3
"""Validate a repository-relative file or directory without symlink escapes."""

import os
import pathlib
import sys


def fail(message):
    print(f"::error::{message}", file=sys.stderr)
    raise SystemExit(1)


workspace = pathlib.Path(os.environ["WORKSPACE_ROOT"]).resolve(strict=True)
path_value = os.environ["REPOSITORY_PATH"]
path_name = os.environ["PATH_NAME"]
path_kind = os.environ["PATH_KIND"]
if path_kind not in {"file", "directory"}:
    fail("Path kind must be 'file' or 'directory'.")
if not path_value or "\n" in path_value or pathlib.Path(path_value).is_absolute():
    fail(f"{path_name} must be a non-empty repository-relative path.")
if ".." in pathlib.Path(path_value).parts:
    fail(f"{path_name} must not contain parent-directory components.")

try:
    resolved = (workspace / path_value).resolve(strict=True)
except FileNotFoundError:
    fail(f"{path_name} does not exist.")
except OSError as error:
    fail(f"{path_name} could not be resolved: {error}")

if os.path.commonpath((str(workspace), str(resolved))) != str(workspace):
    fail(f"{path_name} must resolve inside the checked-out repository.")
if "\n" in str(resolved):
    fail(f"{path_name} must not resolve to a path containing a newline.")
if path_kind == "file" and not resolved.is_file():
    fail(f"{path_name} must be a file.")
if path_kind == "directory" and not resolved.is_dir():
    fail(f"{path_name} must be a directory.")

with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
    output.write(f"absolute-path={resolved}\n")
