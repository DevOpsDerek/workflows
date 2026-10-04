#!/usr/bin/env python3
"""Parse tracked Python source as AST without importing or executing it."""

import ast
import pathlib
import sys
import tokenize


def fail(message):
    raise SystemExit(message)


def main():
    if len(sys.argv) != 3:
        fail("usage: check.py WORKSPACE SOURCE_PATH")

    workspace = pathlib.Path(sys.argv[1]).resolve(strict=True)
    relative_source = pathlib.PurePath(sys.argv[2])
    if relative_source.is_absolute() or ".." in relative_source.parts:
        fail("source-path must be repository-relative and must not traverse parent directories")

    requested = workspace.joinpath(relative_source)
    for length in range(1, len(relative_source.parts) + 1):
        if workspace.joinpath(*relative_source.parts[:length]).is_symlink():
            fail("source-path must not traverse symbolic links")
    source = requested.resolve(strict=True)
    if source != workspace and workspace not in source.parents:
        fail("source-path must resolve inside the checked-out repository")

    if not source.is_file() or source.suffix != ".py":
        fail("source-path must name one repository-relative .py file; use a separate step per file")

    try:
        with tokenize.open(source) as source_file:
            ast.parse(source_file.read(), filename=str(source))
    except (SyntaxError, UnicodeError) as error:
        fail(f"{source}: {error}")

    print(f"Parsed {source} without executing it.")


if __name__ == "__main__":
    main()
