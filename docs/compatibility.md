# Compatibility and consumer guidance

The central validation workflow is stack-neutral: it lints GitHub Actions
workflow files and validates the caller's gh-aw Markdown plus generated lock
files. The `run-checked-script` API is intentionally narrower: one version-
pinned check for Go, Python, Node.js, .NET, or backend-free Terraform validation.
It does not replace language-specific lint/test matrices, formatters, scanners,
artifact handling, or existing required checks. Keep those jobs and check
names stable while adopting this catalog.

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

Workflow permissions do not replace repository rulesets, branch protection,
environment protection, or required human approvals. Verify those controls in
each target repository's settings; do not infer that they exist from workflow
YAML or documentation.

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

## Private repositories

The shared catalog in this repository is public; private consumers can import
it by commit SHA. Do not include credentials, customer data, or private
repository contents in shared patterns or examples. Consumers should inspect
their own source and issue/project data before enabling any agentic trigger.
