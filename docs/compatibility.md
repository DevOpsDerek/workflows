# Compatibility and consumer guidance

The central validation workflow is stack-neutral: it lints GitHub Actions
workflow files and validates the caller's gh-aw Markdown plus generated lock
files. The `run-checked-script` API is intentionally narrower: one version-
pinned check for Go, Python, Node.js, .NET, or backend-free Terraform validation.
Language/IaC lint interfaces are separate fixed reusable workflows documented
in the [catalog](catalog.md). The GitHub Actions and gh-aw validator remains
authoritative for those sources; the language workflows do not duplicate it.
None of these workflows replaces repository-specific test matrices, scanners,
artifact handling, or existing required checks. Keep those jobs and check names
stable while adopting this catalog.

Consumers should preserve their own tool versions, working directories,
commands, outputs, artifact names/paths, triggers, platform-specific runners,
and failure behavior. Split central calls or keep specialized checks local
when a repository has distinct jobs (for example, PowerShell analysis versus
Pester tests and XML artifacts, Terraform static validation versus multiple
negative fixtures, or container validation versus release publishing). The
simple reusable workflow is Linux-only and does not publish artifacts; use its
composite action in an existing job or retain specialized local jobs where
runner, command, output, or artifact behavior differs. Grant write permissions
only to the narrowly scoped publishing job, if any; never pass publishing
credentials to agentic workflows.

The Python syntax-only composite action parses one explicitly named `.py` file
without importing or executing it. It does not replace pytest, Ruff, an OS or
Python-version matrix, coverage, or artifact-producing checks. The
`run-checked-script` helper executes caller code and must not be treated as a
syntax-only alternative.

Language and IaC lint workflows accept only fixed tool/version/path inputs.
Their policy files remain caller-owned and are loaded by the corresponding
tool where supported. Python lint also checks formatting without applying
changes. Go lint supports golangci-lint v1 and v2; callers must select the
matching configuration format. The shell workflow treats its selected source
files as Bash. Terraform init uses no backend and a read-only lockfile, but can
still download declared providers/modules. Helm lint operates only on a local
chart and does not fetch dependencies or contact a cluster.

Workflow permissions do not replace repository rulesets, branch protection,
environment protection, or required human approvals. Verify those controls in
each target repository's settings; do not infer that they exist from workflow
YAML or documentation.

The top-level `swiftlint.yml` helper is macOS-only, separate from the generic
language/IaC lint helpers. It requires explicit source roots and a caller-owned
SwiftLint config, pins SwiftLint and the installed Xcode release, and performs
lint-only checks. Keep the caller's build/test toolchain, rules, exclusions,
and required-check names consistent with its existing policy. The default
strict mode fails on warnings; callers may select normal error-only failure.
It does not format, autofix, build, or replace XCTest.

Treat gh-aw shared patterns as prompts/configuration components, not a
universal workflow to enable unmodified. Each consumer owns its local triggers,
permissions, tool access, labels, and `.lock.yml`. Keep these sources and
generated lock files in version control and validate them with the composite
action or reusable workflow documented in the catalog.

## Location-sensitive repositories

For `where-is-dad`, an agentic workflow must not receive live location data or
data files that reveal location history. Before adding a consumer workflow:

1. Identify the exact live-data stores, exports, backups, fixtures, and
   generated files from the repository itself; do not guess their names.
2. Configure the gh-aw checkout to include only reviewed source, tests, and
   documentation paths. Use an explicit sparse-checkout allowlist rather than
   checking out the full repository and relying only on prompt instructions.
3. Verify the compiled lock file and the actual workflow run context cannot
   expose location records or paths to the model. Do not configure tools or
   network access that can query live location services.

If a safe allowlist cannot be established, do not enable the agentic workflow.
This precaution is specific to location-bearing data and should be applied
before choosing any general-purpose pattern.

For `where-is-dad`, the central static validation workflow is the appropriate
catalog fit. Do not enable the shared documentation-upkeep or other agentic
patterns, or use the code-executing `run-checked-script` helper, for that
repository. Keep live location records and their data files out of any model
context; this catalog does not provide a location-data agent workflow.

## Deferred static-analysis interfaces

The Helm lint workflow is not a Kubernetes API-schema validator. No offline
Kubernetes manifest schema bundle has been established, so Kubernetes
schema/policy validation remains local to consumers. ARM/Bicep semantic
validation is also not provided by this catalog revision. Keep those checks
in their existing consumer jobs until their exact tool versions, input/config
contracts, and normal/failure behavior can be tested centrally.

The separate `markdown-link-check.yml` workflow validates local Markdown
links without network access by default. External link checking is opt-in;
only HTTP 404/410 and malformed, host-less, or credential-bearing URLs are
treated as confirmed broken, while
timeouts, connection errors, rate limits, server errors, and access-restricted
responses are reported as transient or unverified warnings unless the caller
sets `fail-on-unconfirmed: true`. Keep required pull-request checks
network-free unless the repository accepts third-party availability as a
merge dependency.

## Private repositories

The shared catalog in this repository is public; private consumers can import
it by commit SHA. Do not include credentials, customer data, or private
repository contents in shared patterns or examples. Consumers should inspect
their own source and issue/project data before enabling any agentic trigger.
