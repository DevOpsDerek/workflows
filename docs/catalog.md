# Reusable workflow and action catalog

All references to this repository should use a full 40-character commit SHA.
Do not use `@main`, a branch name, or a movable tag. Obtain the SHA from a
published commit in `DevOpsDerek/workflows` and update it deliberately when
adopting a newer catalog revision.

## Validate GitHub automation

Path: `.github/workflows/validate-agentic-workflows.yml`

This reusable workflow lints the caller's non-gh-aw GitHub Actions YAML,
excluding generated `*.lock.yml` files from stock actionlint. It installs the
specified gh-aw CLI release, whose compiler runs its compatibility-aware
actionlint validation on generated lock files, validates and compiles the
caller's gh-aw Markdown sources, and fails if compilation changes or creates
lock files. Its
`workflow_call` inputs are:

| Input | Type | Default | Purpose |
| --- | --- | --- | --- |
| `gh-aw-version` | string | `v0.89.21` | Exact gh-aw CLI release tag |
| `workflows-directory` | string | `.github/workflows` | Directory containing local sources and lock files |

It requires only `contents: read`. It does not publish artifacts, request
secrets, or grant write permissions.

```yaml
name: Validate GitHub automation

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  validate:
    uses: DevOpsDerek/workflows/.github/workflows/validate-agentic-workflows.yml@<40_CHARACTER_COMMIT_SHA>
    with:
      gh-aw-version: v0.89.21
      workflows-directory: .github/workflows
```

The workflow file can also be called without inputs when the defaults fit.
Keep caller job IDs stable when replacing local checks with this reusable
workflow so required-check names do not change unexpectedly.

## Validate gh-aw sources as a composite action

Path: `.github/actions/validate-agentic-workflows/action.yml`

The composite action has the same two optional inputs as the reusable workflow.
Run it on a Linux runner after checking out the caller repository. The caller
needs `contents: read`; the action does not check out files or request other
permissions. It compiles in place and fails if the checked-in `.lock.yml` files
are not current.

```yaml
name: Validate agentic workflows

on:
  pull_request:

permissions:
  contents: read

jobs:
  gh-aw:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<PINNED_ACTIONS_CHECKOUT_SHA>
      - uses: DevOpsDerek/workflows/.github/actions/validate-agentic-workflows@<40_CHARACTER_COMMIT_SHA>
        with:
          gh-aw-version: v0.89.21
          workflows-directory: .github/workflows
```

Use the reusable workflow when both workflow linting and gh-aw compilation are
needed. Use the composite action to add the same gh-aw validation to an
existing job. The catalog internally pins third-party actions to commit SHAs.

## gh-aw shared components

These files have no trigger and are not runnable workflows. Import the selected
component from a local workflow's Markdown frontmatter using an immutable
catalog SHA:

| Component path | Pattern |
| --- | --- |
| `.github/workflows/shared/agentic/issue-triage.md` | Evidence-based issue triage proposal via one safe-output comment |
| `.github/workflows/shared/agentic/ci-failure-diagnosis.md` | Bounded failed-run diagnosis via one safe-output issue |
| `.github/workflows/shared/agentic/test-quality.md` | One draft PR limited by `allowed-files` to common test directories and test-named files |
| `.github/workflows/shared/agentic/documentation-upkeep.md` | One draft PR limited by `allowed-files` to root README/CONTRIBUTING/CHANGELOG and Markdown under `docs/` or `doc/` |

Examples and required local source/lock behavior are in
[Agentic patterns](agentic-patterns.md). The gh-aw compiler resolves remote
imports when each consumer compiles its own source. Consumer repositories must
commit both `.github/workflows/<name>.md` and the generated
`.github/workflows/<name>.lock.yml`; the central Markdown components do not
replace those local trigger/configuration files.

## Run a version-pinned check

This is a deliberately narrow helper, not a replacement for repository-specific
CI. It supports one Go package test (`go test <package-directory>`), one Python
or Node.js script, one .NET project test, or backend-disabled Terraform
`init`/`validate`. It does not run linters, matrices, multiple commands,
PowerShell, custom shell snippets, builds, scans, artifact uploads, or publish
steps. Preserve those behaviors in their existing caller jobs. Use the
composite action in an existing job when artifact handling and check names
must remain unchanged.

| Interface | Path |
| --- | --- |
| Reusable workflow | `.github/workflows/run-checked-script.yml` |
| Composite action | `.github/actions/run-checked-script/action.yml` |

Both interfaces use the same required inputs:

| Input | Type | Values / default |
| --- | --- | --- |
| `runtime` | string | `go`, `python`, `node`, `dotnet`, or `terraform` |
| `version` | string | Required exact three-part version, such as `1.22.12` |
| `script-path` | string | Required repo-relative package directory, script, project, or Terraform root |
| `working-directory` | string | Optional; defaults to `.` |

The reusable workflow additionally accepts `timeout-minutes` (number, default
`15`). It runs on `ubuntu-latest`, checks out the caller repository, and grants
only `contents: read`. It has no artifact or publishing side effects. Runtime
and version are validated before setup; paths must resolve inside the
checked-out working directory. The composite action uses the existing runner
and is intended for a caller job that already has its required checkout and
other job steps.

Example reusable workflow caller:

```yaml
name: Go tests

on:
  pull_request:

permissions:
  contents: read

jobs:
  go-tests:
    name: Go tests
    uses: DevOpsDerek/workflows/.github/workflows/run-checked-script.yml@<40_CHARACTER_COMMIT_SHA>
    with:
      runtime: go
      version: 1.22.12
      working-directory: .
      script-path: ./internal/example
      timeout-minutes: 20
```

Example composite action caller, preserving surrounding job steps and artifact
handling:

```yaml
jobs:
  test:
    name: Existing test check
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@<PINNED_ACTIONS_CHECKOUT_SHA>
      - uses: DevOpsDerek/workflows/.github/actions/run-checked-script@<40_CHARACTER_COMMIT_SHA>
        with:
          runtime: python
          version: 3.12.8
          working-directory: .
          script-path: tests/run_smoke.py
      # Keep the caller's artifact upload/report steps here.
```

Script paths are passed as environment data and invoked as arguments; these
interfaces do not accept or `eval` caller-provided shell command text. Checks
still execute code from the caller checkout, so keep credentials out of the
job and preserve the repository's existing fork/untrusted-PR policy.

## Check Python syntax without executing code

Path: `.github/actions/check-python-syntax/action.yml`

Use this composite action only for non-executing Python syntax validation. It
installs an exact three-part Python version and parses one explicitly named,
repository-relative `.py` file into an AST. It does not import or execute the
file, install project dependencies, run tests or linters, measure coverage, or
scan directories. Call the action once per file that should be checked. The
helper rejects absolute/traversing paths, symlinks, and files outside the
checkout. Check out the caller repository first and grant only
`contents: read`.

```yaml
jobs:
  syntax:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@<PINNED_ACTIONS_CHECKOUT_SHA>
      - uses: DevOpsDerek/workflows/.github/actions/check-python-syntax@<40_CHARACTER_COMMIT_SHA>
        with:
          python-version: 3.12.8
          source-path: src/example.py
      - uses: DevOpsDerek/workflows/.github/actions/check-python-syntax@<40_CHARACTER_COMMIT_SHA>
        with:
          python-version: 3.12.8
          source-path: tests/test_example.py
```

This is a syntax-only complement, not a replacement for a repository's pytest,
Ruff, OS/Python-version matrix, coverage, or artifact-producing checks.

## Language and IaC lint workflows

These reusable workflows run fixed, non-autofixing lint/validation commands
against the checked-out caller repository. They do not accept caller shell
commands, secrets, deployment inputs, or write permissions. Pin every `uses`
reference to the same full catalog commit SHA. Each `working-directory` is a
repository-relative directory validated against traversal and symlink escapes.
Tool/runtime version inputs are optional exact three-part versions; defaults
are shown below.

| Workflow path | Inputs (defaults in parentheses) | Behavior |
| --- | --- | --- |
| `.github/workflows/lint/python-ruff.yml` | `python-version` (`3.12.8`), `ruff-version` (`0.11.13`), `working-directory` (`.`) | `ruff check --no-fix` and `ruff format --check`; caller Ruff config remains authoritative |
| `.github/workflows/lint/go.yml` | `go-version` (`1.24.2`), `golangci-lint-version` (`1.64.8`), `working-directory` (`.`) | `golangci-lint run`; downloads the exact v1/v2 Linux release binary, preserving caller-owned configuration and avoiding a Go-version requirement from building the linter |
| `.github/workflows/lint/rust.yml` | `rust-version` (`1.86.0`), `working-directory` (`.`) | Installs the pinned Rust toolchain and runs `cargo fmt --all -- --check`; does not build or execute project code |
| `.github/workflows/lint/shell.yml` | `shellcheck-version` (`0.10.0`), `working-directory` (`.`) | Checks `.sh`, `.bash`, and `.bats` files as Bash with `--severity=style`; mixed POSIX-shell trees should keep their existing shell-specific checks |
| `.github/workflows/lint/powershell.yml` | `psscriptanalyzer-version` (`1.24.0`), `working-directory` (`.`), optional `settings-path` (empty) | Runs PSScriptAnalyzer on PowerShell source and fails on any error or warning diagnostic |
| `.github/workflows/lint/markdown.yml` | `node-version` (`22.15.0`), `markdownlint-cli2-version` (`0.17.2`), `working-directory` (`.`), `markdown-paths` (`**/*.md`) | Lints newline-separated, non-empty relative globs from the working directory; the default includes nested Markdown. Paths are passed as individual arguments, never evaluated as shell text |
| `.github/workflows/lint/terraform.yml` | `terraform-version` (`1.11.4`), `working-directory` (`.`) | Runs recursive `terraform fmt -check`, then backend-disabled init with `-lockfile=readonly` and `terraform validate`; init can fetch declared providers/modules |
| `.github/workflows/lint/helm.yml` | `helm-version` (`3.17.3`), required `chart-path` | Runs `helm lint --strict` on one local chart directory; no cluster access or dependency download/build |

Example calls, with the full SHA from the chosen published catalog commit:

```yaml
jobs:
  go-lint:
    uses: DevOpsDerek/workflows/.github/workflows/lint/go.yml@<40_CHARACTER_COMMIT_SHA>
    with:
      go-version: 1.22.12
      golangci-lint-version: 1.64.8
      working-directory: .

  markdown-lint:
    uses: DevOpsDerek/workflows/.github/workflows/lint/markdown.yml@<40_CHARACTER_COMMIT_SHA>
    with:
      markdown-paths: |
        README.md
        docs/**/*.md
```

The Go workflow accepts exact golangci-lint 1.x and 2.x releases; keep the
caller's linter major/config in sync.
The markdown workflow runs only the supplied globs (or its recursive default),
so callers can scope checks to their repository's policy without unsafe shell
arguments.

This catalog revision does not publish SwiftLint, ARM/Bicep semantic
validation, Kubernetes manifest schema validation, or Markdown link checking.
SwiftLint needs a separately verified macOS toolchain and binary contract;
ARM validation needs a schema/deployment contract not established here;
Kubernetes API schemas are not bundled for offline validation; and link
checking requires network-dependent targets. The Helm workflow is limited to
local chart linting and is not a Kubernetes manifest schema validator.
