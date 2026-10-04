# Report-only contract proposals: runtime adoption blocked

These four trigger-free v1 interfaces are **non-deployable proposals**, not
enabled workflows. They preserve the existing catalog APIs and do not import
the write-capable issue-triage, CI diagnosis, test-quality, or documentation
upkeep components. No consumer adoption is part of this change.

| Central path under `.github/workflows/shared/agentic/` | Reviewed evidence | Findings |
| --- | --- | --- |
| `ci-failure-report.md` | Completed run identity, revision, job/step identifiers, redacted log excerpts | First actionable failure, confirmed cause versus hypothesis |
| `platform-pr-report.md` | Immutable PR base/head revisions, approved static IaC/platform/dependency diffs, supplied check results | IaC intent, manifest/policy consistency, pinning and supply-chain concerns |
| `test-lesson-report.md` | Revision, approved source/test/lesson excerpts, supplied results | Assertions, examples, prerequisites, edge cases, lesson objectives |
| `documentation-drift-report.md` | Revision, approved documentation/static configuration excerpts | Version/default/interface/example drift, not live environment drift |

The common interface is a human-reviewed, redacted evidence packet with an
immutable revision, exact approved source paths, explicitly excluded paths,
and excerpts labelled by path/line or run/job/step. The output is Markdown in
the ordinary agent response: scope/revision, a findings table (severity,
location, finding, evidence reference, confidence, human-verifiable next
check), and limitations/unrun checks. Missing evidence must not become a
clean bill of health. This is a prompt/output contract, not an automated
JSON schema or proof of model behavior.

## Supported compiler blocker

The supported and latest stable compiler is **gh-aw v0.89.21**. Its
[`applyDefaultCreateIssue`](https://github.com/github/gh-aw/blob/v0.89.21/pkg/workflow/safe_outputs_state.go)
unconditionally injects `create-issue` when no non-system safe output is
enabled. Omitting `safe-outputs`, using an empty mapping, or disabling all
system handlers does not prevent this. Its
[schema](https://github.com/github/gh-aw/blob/v0.89.21/pkg/parser/schemas/main_workflow_schema.json)
does not permit `safe-outputs: false` or `create-issue: false`.

The proposals disable checkout, repository/edit/shell tools, external network
domains, and system safe outputs in their source. **Nevertheless, compiling
them with v0.89.21 produces issue-writing safe-output/conclusion jobs.** They
must not be enabled, advertised as no-write runtime workflows, or adopted by
consumers. Disabling threat detection here does not make generated issue
outputs safe: all such locks are rejected regardless.

Do not hand-edit locks, downgrade or use a prerelease without a supported
compatibility decision, configure a dummy safe output, use comment/repository
memory as a loophole, or rely on read-only caller permissions to neutralize
compiler-generated write jobs. No unsafe generated lock is committed.
Issue #3 remains open; runtime acceptance is blocked pending a supported
source-level zero-output mode.

## Evidence and sensitive paths

No direct GitHub/file-reading, shell, web, cloud, cluster, or registry tools
are provided. Do not retrieve full PR diffs, raw logs, arbitrary artifacts, or
repository contents into model context. Before any future runtime adoption,
establish exact reviewed source paths and exclude credentials, `.env` files,
Terraform state/plans, customer/private data, exports/backups, and location
records. Sensitive-path fixtures reject these even if explicitly allowlisted.
Unknown paths are denied; wildcards, URLs, absolute paths, and traversal are
not evidence sources.

`tests/report_only_contracts.py::validate_evidence_path` is a central
metadata-only policy helper. It never opens paths. It is not a runtime intake
action, a secret detector, a symlink-safe file reader, or an automatic
redactor. Human review must exclude sensitive content regardless of filename;
future consumer tickets must wire a pre-model gate and verify every model
input surface. Reject symlinks and review exact files before reading them.
Do not place sensitive evidence in trigger inputs, workflow bodies, artifacts,
or compiler/runtime logs. Prompt instructions alone do not enforce privacy.
The existing prohibition on agentic adoption for `where-is-dad` remains.

## Immutable consumption and release gate

After the compiler blocker is resolved, reference exactly one approved central
component using the full immutable candidate/release SHA:

```yaml
inlined-imports: true
imports:
  - DevOpsDerek/workflows/.github/workflows/shared/agentic/ci-failure-report.md@<40_CHARACTER_COMMIT_SHA>
```

This fragment is **not a runnable example today**. Consumer tickets, not this
change, own unprivileged `pull_request` or manual triggers, sanitized evidence
intake, and local sources/generated locks. Do not use `pull_request_target`,
privileged `workflow_run` execution, inherited secrets, app/PAT credentials,
OIDC, write permissions, extra tools, checkout, steps, jobs, or additional
write-capable imports. Provider authentication for model inference is separate
from cloud/deployment credentials and must be reviewed without granting
repository write capability.

Treat changes to evidence fields, findings shape, tools, permissions, or path
policy as interface changes. Review a new full SHA deliberately; do not track
branches/tags. Keep existing APIs unchanged. Compile local sources with the
supported compiler and central validation workflow; never edit `.lock.yml`.
Before release/adoption, verify every generated job/token, merged tool
manifest, checkout/context transfer, and safe-output handler. There must be
zero write jobs, usable write-capability tokens, or safe-output operations.
The current regression guard is intentionally narrow; it is not sufficient
to certify a future compiler's entire runtime without that review.

## Focused verification

```bash
python3 tests/report_only_contracts.py
python3 tests/report_only_contracts.py --compile
python3 tests/report_only_contracts.py --catalog-ref <40_CHARACTER_COMMIT_SHA>
```

The first command checks the four source policies and positive/negative
capability and sensitive-path fixtures. The other commands use the supported
compiler's `--validate --actionlint` checks in a temporary checkout, then
assert that every compiled import is **rejected** for injected issue-writing
permissions. Temporary locks are removed automatically. A passing regression
means the blocker was reproduced, not that runtime acceptance criteria pass.
If compiler behavior changes, the regression fails and requires explicit
reassessment. Existing APIs remain covered by `tests/catalog_imports.py`.
