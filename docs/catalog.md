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

## Lint Swift on macOS

Path: `.github/workflows/swiftlint.yml` (a top-level reusable workflow, separate
from the language/IaC lint catalog).

| Input | Type | Default / contract |
| --- | --- | --- |
| `swiftlint-version` | string | `0.65.1`; exact three-part release, no `v`, ranges, or prereleases |
| `xcode-version` | string | `16.4`; exact installed Xcode release, not `latest` |
| `source-roots` | string | Required non-empty JSON array of repository-relative directories |
| `config-path` | string | Required repository-relative caller-owned `.yml` or `.yaml` file |
| `strict` | boolean | `true`; warnings fail the check as well as errors |

The workflow uses `macos-15`, selects the requested installed Xcode release
through `DEVELOPER_DIR`, verifies its version, and prints its Swift toolchain
version. Xcode pins the toolchain/SDK selection; runner images remain
GitHub-managed, so a removed Xcode release fails explicitly rather than silently
switching toolchains. Match the caller's build Xcode release when adopting it.

SwiftLint is downloaded from its exact official release's
`portable_swiftlint.zip`, installed in an isolated temporary directory, and
version-checked before use. This is a version pin, not an independently pinned
archive checksum. There is no Homebrew upgrade or fallback to a preinstalled
SwiftLint. Only `lint` runs: no analyzer, build, formatter, `--fix`, or source
mutation. Diagnostics use the GitHub Actions reporter and preserve SwiftLint's
nonzero exit status; `strict: false` retains normal error-only failure behavior.

Each root must exist and contain Swift files. Absolute paths, traversal,
globs, empty/duplicate roots, control characters, and symlinks (including inside
source trees) are rejected. Overlapping roots are deduplicated. Files from all
roots are passed as literal script-input-file environment values in one lint
invocation, so caller settings are applied consistently. `--force-exclude`
honors caller-owned exclusions; do not exclude an entire root that you intend
to lint. No rules or severity policy are supplied by the catalog, and there is
no arbitrary command/argument input. Review caller configs, including nested,
parent/remote configs and custom rules, as trusted policy; this is not a
sandbox for untrusted configuration.

The workflow checks out the caller with persisted credentials disabled, grants
only `contents: read`, and accepts no secrets. Call it from ordinary PR/push
checks, not credential-bearing `pull_request_target` jobs.

Example caller for both application and test sources (add `.swiftlint.yml`
and choose its rules in the caller repository):

```yaml
name: Swift lint
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  swiftlint:
    uses: DevOpsDerek/workflows/.github/workflows/swiftlint.yml@0bc15e409d9e00429e6ace3b4c535c23765ff073
    with:
      swiftlint-version: 0.65.1
      xcode-version: '16.4'
      source-roots: '["Supercar", "SupercarTests"]'
      config-path: .swiftlint.yml
      strict: true
```

No consumer repository is changed by publishing this workflow. Contract tests
run the embedded validation/invocation code with isolated app/test fixtures
and a fake linter to check argument boundaries and exit codes:
`python3 tests/swiftlint_contracts.py`.

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

GitHub requires reusable workflows directly under `.github/workflows/`.
The nested `.github/workflows/lint/` paths in the initial publication were
not callable; use the top-level entrypoints below at a corrected catalog SHA.

| Workflow path | Inputs (defaults in parentheses) | Behavior |
| --- | --- | --- |
| `.github/workflows/lint-python-ruff.yml` | `python-version` (`3.12.8`), `ruff-version` (`0.11.13`), `working-directory` (`.`) | `ruff check --no-fix` and `ruff format --check`; caller Ruff config remains authoritative |
| `.github/workflows/lint-go.yml` | `go-version` (`1.24.2`), `golangci-lint-version` (`1.64.8`), `working-directory` (`.`) | `golangci-lint run`; downloads the exact v1/v2 Linux release binary, preserving caller-owned configuration and avoiding a Go-version requirement from building the linter |
| `.github/workflows/lint-rust.yml` | `rust-version` (`1.86.0`), `working-directory` (`.`) | Installs the pinned Rust toolchain and runs `cargo fmt --all -- --check`; does not build or execute project code |
| `.github/workflows/lint-shell.yml` | `shellcheck-version` (`0.10.0`), `working-directory` (`.`) | Checks `.sh`, `.bash`, and `.bats` files as Bash with `--severity=style`; mixed POSIX-shell trees should keep their existing shell-specific checks |
| `.github/workflows/lint-powershell.yml` | `psscriptanalyzer-version` (`1.24.0`), `working-directory` (`.`), optional `settings-path` (empty) | Runs PSScriptAnalyzer on PowerShell source and fails on any error or warning diagnostic |
| `.github/workflows/lint-markdown.yml` | `node-version` (`22.15.0`), `markdownlint-cli2-version` (`0.17.2`), `working-directory` (`.`), `markdown-paths` (`**/*.md`) | Lints newline-separated, non-empty relative globs from the working directory; the default includes nested Markdown. Paths are passed as individual arguments, never evaluated as shell text |
| `.github/workflows/lint-terraform.yml` | `terraform-version` (`1.11.4`), `working-directory` (`.`) | Runs recursive `terraform fmt -check`, then backend-disabled init with `-lockfile=readonly` and `terraform validate`; init can fetch declared providers/modules |
| `.github/workflows/lint-helm.yml` | `helm-version` (`3.17.3`), required `chart-path` | Runs `helm lint --strict` on one local chart directory; no cluster access or dependency download/build |

Example calls, with the full SHA from the chosen published catalog commit:

```yaml
jobs:
  go-lint:
    uses: DevOpsDerek/workflows/.github/workflows/lint-go.yml@<40_CHARACTER_COMMIT_SHA>
    with:
      go-version: 1.22.12
      golangci-lint-version: 1.64.8
      working-directory: .

  markdown-lint:
    uses: DevOpsDerek/workflows/.github/workflows/lint-markdown.yml@<40_CHARACTER_COMMIT_SHA>
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

This lint family does not include SwiftLint (see the separate macOS workflow
above), ARM/Bicep semantic validation, Kubernetes manifest schema validation,
or Markdown link checking (see the separate link-check workflow below).
ARM validation needs a schema/deployment contract not established here, and
Kubernetes API schemas are not bundled for offline validation. The Helm
workflow is limited to local chart linting and is not a Kubernetes manifest
schema validator.

## Check Markdown links

Path: `.github/workflows/markdown-link-check.yml` (a top-level reusable
workflow, separate from `lint-markdown.yml`, whose API is unchanged).

| Input | Type | Default / contract |
| --- | --- | --- |
| `python-version` | string | `3.12.8`; exact three-part version, 3.9.0 or newer, for the bundled checker, verified at run time |
| `working-directory` | string | `.`; repository-relative directory without traversal, `.git`, or symlinks |
| `markdown-paths` | string | `**/*.md`; newline-separated globs relative to `working-directory` |
| `exclude-paths` | string | Empty; newline-separated globs of Markdown files to skip |
| `exclude-links` | string | Empty; newline-separated literal link-target prefixes to skip |
| `external-links` | string | `skip` (network-free) or `check` |
| `timeout-seconds` | number | `10`; per-request timeout, 1-60 |
| `max-retries` | number | `2`; retries for transient external failures, 0-5 |
| `fail-on-unconfirmed` | boolean | `false`; fail instead of warn on transient/unverified external results |

The checker is a Python standard-library script embedded in the workflow, so
the checker revision is pinned by the catalog SHA and the runtime by
`python-version` (installed through a SHA-pinned `actions/setup-python` with
`check-latest: false`). It installs no packages, does not use a local action
from the caller, and accepts no secrets or shell text. Inputs are passed as
environment data and validated before any file is read. The workflow checks
out the caller with persisted credentials disabled, grants only
`contents: read`, and never edits files, auto-fixes links, comments, or opens
pull requests.

Globs support `*` and `?` (within one path segment) and `**` (any number of
directories). Absolute paths, `..` components, backslashes, and control
characters are rejected; `.git` is never scanned; matching nothing is an
error. Inline links, images, reference definitions, `<https://...>` autolinks,
and double-quoted, single-quoted, or unquoted `href`/`src` attributes on
`<a>` and `<img>` tags are checked. Links in fenced code blocks,
inline code spans, HTML comments, and backslash-escaped brackets are ignored.

Local links are checked deterministically without network access: query
strings and fragments are removed, percent-encoding is decoded, `/`-prefixed
targets resolve from the repository root, and other targets resolve from the
containing file. A target must exist with exact path case (as on GitHub) and
remain inside the checkout; empty targets fail. Same-document `#fragment`
links and non-HTTP schemes such as `mailto:` are skipped.

External `http(s)` links are only contacted when `external-links: check`.
In both modes, malformed URLs (including whitespace, control characters, or
invalid ports), URLs without a host, and URLs with embedded
`user:password@` credentials are rejected offline as confirmed broken and are
never requested; credentials are redacted as `***@` in annotations.
Each unique URL (fragment removed) is requested once with `GET`, a fixed
User-Agent, no credentials or cookies, followed redirects, and the per-request
timeout. Results are classified as:

| Result | Causes | Retried | Outcome |
| --- | --- | --- | --- |
| OK | 2xx after redirects | - | Pass |
| Broken (confirmed) | HTTP 404 or 410; malformed, host-less, or credential-bearing URL (validated offline, never requested) | No | Error; always fails |
| Transient | Timeout, DNS/connection error, HTTP 408, 425, 429, or 5xx | Up to `max-retries`, backoff 1s, 2s, 4s | Warning, or error when `fail-on-unconfirmed: true` |
| Unverified | Other statuses (for example 401/403), TLS verification failure | No | Warning, or error when `fail-on-unconfirmed: true` |

Exit status 1 means at least one confirmed broken link (local or external),
2 means invalid input or configuration, and 3 means only transient/unverified
external results with `fail-on-unconfirmed: true`. Annotations include the
repository-relative file and line. External checks use up to eight concurrent
requests and stop starting new probes after a ten-minute budget (remaining
URLs are reported as transient); the job times out after 20 minutes.

Example caller (replace the placeholder with the full SHA of the published
catalog commit you adopt; do not use a branch or tag):

```yaml
name: Markdown links
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  markdown-links:
    uses: DevOpsDerek/workflows/.github/workflows/markdown-link-check.yml@<40_CHARACTER_COMMIT_SHA>
    with:
      markdown-paths: |
        README.md
        docs/**/*.md
      exclude-paths: |
        docs/generated/**
      exclude-links: |
        https://internal.example.com/
      external-links: skip
```

Use `external-links: check` in a separate scheduled or non-required job if
external reachability should be reported without making pull requests depend
on third-party availability.

Limitations: heading anchors/fragments are not validated; reference-style
link usages are checked through their definitions; links inside indented code
blocks, block-quoted or list-nested fences, and bare (non-angle-bracket) URLs
follow simple parsing rules and may be checked or missed; HTML is matched by
pattern rather than a full HTML parser, so only `href`/`src` on `<a>`/`<img>`
are read (not `srcset` or other elements) and HTML character entities such as
`&amp;` are not decoded; local targets are percent-decoded once; protocol-relative
`//host` links and non-HTTP schemes are skipped; external results reflect the
runner's network at that moment, and some sites block automated requests
(reported as unverified rather than broken). No consumer repository is
changed by publishing this workflow. Contract tests run the embedded checker
against isolated fixtures and a local HTTP server:
`python3 tests/markdown_link_check_contracts.py`.
