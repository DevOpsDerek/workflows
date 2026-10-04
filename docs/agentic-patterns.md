# Shared gh-aw agentic patterns

GitHub Agentic Workflows (gh-aw) uses a Markdown source plus generated
`.lock.yml` in each consuming repository's `.github/workflows/`. This catalog
hosts trigger-free shared components: callers select and import the pieces
they need, then compile and review the local source and lock file. Imports are
resolved at compile time and must use the catalog commit SHA.

These patterns are starting points, not automatic repository rollouts. Adapt
triggers, existing labels, toolsets, and test commands to each repository.
They are intentionally independent so a consumer can choose a suitable
pattern without inheriting another pattern's trigger or permissions.

For findings-only requirements, do not reuse the patterns below: they permit
bounded GitHub writes. See the distinct [report-only proposals and compiler
blocker](report-only-contracts.md). They are not runnable with the supported
compiler and must wait for separate consumer adoption tickets.

## Issue triage

The component proposes a concise summary, an existing label where evidence
supports it, and any necessary clarification. The agent cannot add labels,
assign, close, or edit issues; one bounded safe-output comment is permitted.

```markdown
---
on:
  issues:
    types: [opened, reopened]
permissions:
  issues: read
inlined-imports: true
imports:
  - DevOpsDerek/workflows/.github/workflows/shared/agentic/issue-triage.md@<40_CHARACTER_COMMIT_SHA>
tools:
  github:
    toolsets: [issues, labels]
    allowed: [issue_read, list_labels]
---

Follow the imported issue-triage instructions for the triggering issue.
```

## CI failure diagnosis

Use a `workflow_run` trigger restricted to named workflows and completed runs.
Grant only the read access needed to inspect actions, source, and issues. The
component may propose one diagnostic issue for an evidenced, non-duplicate
failure; it cannot rerun workflows or change code.

```markdown
---
on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    branches: [main] # replace with the consumer's protected branches
permissions:
  actions: read
  issues: read
inlined-imports: true
imports:
  - DevOpsDerek/workflows/.github/workflows/shared/agentic/ci-failure-diagnosis.md@<40_CHARACTER_COMMIT_SHA>
tools:
  github:
    toolsets: [actions, issues, search]
    allowed: [actions_get, actions_list, get_job_logs, search_issues]
---

Follow the imported CI diagnosis instructions for the completed run.
```

## Test-quality assistance

Use a manual or scheduled trigger initially. The component permits at most one
draft PR, restricted by `allowed-files` to common test directories and
test-named files only; a human must review and merge it.

```markdown
---
on:
  workflow_dispatch:
permissions:
  contents: read
inlined-imports: true
imports:
  - DevOpsDerek/workflows/.github/workflows/shared/agentic/test-quality.md@<40_CHARACTER_COMMIT_SHA>
tools:
  github:
    toolsets: [repos]
    allowed: [get_file_contents]
---

Follow the imported test-quality instructions. Use only documented commands;
report unrun checks honestly rather than claiming success.
```

## Documentation upkeep

Use a manual or scheduled trigger at first. The component permits at most one
draft PR, restricted by `allowed-files` to root README/CONTRIBUTING/CHANGELOG
files and Markdown files under `docs/` or `doc/`, subject to human review.
`protected-files: allowed` is scoped by that exclusive file allowlist so these
documentation paths can be proposed without opening protected workflow or
source paths.

```markdown
---
on:
  workflow_dispatch:
permissions:
  contents: read
inlined-imports: true
imports:
  - DevOpsDerek/workflows/.github/workflows/shared/agentic/documentation-upkeep.md@<40_CHARACTER_COMMIT_SHA>
tools:
  github:
    toolsets: [repos]
    allowed: [get_commit, get_file_contents, list_commits]
---

Follow the imported documentation-upkeep instructions. Use only documented
checks; report unrun checks honestly rather than claiming success.
```

In every case, install/configure gh-aw in the consumer, commit the Markdown
source and compiled `.lock.yml` together, and review both files before
enabling the trigger. After changing frontmatter or imports, rerun
`gh aw compile`; review body-only changes as well.

Each shared component disables gh-aw's automatic failed-job and failure-issue
reports, as well as issue creation by missing-tool, missing-data, incomplete,
and no-op system handlers. Only the bounded handler listed for that component
is enabled: one triage comment, one CI diagnosis issue, or one draft PR for
test/documentation assistance. The generated lock assertions in this catalog
verify those handlers, their configuration, and their resulting write scopes.

## Limits and human review

- Agent jobs should have read-only permissions. Declare only the specific read
  scopes required by the selected trigger and tools.
- GitHub writes, where enabled, are isolated to gh-aw safe outputs and bounded
  per run. The agent must not receive direct write credentials.
- Proposed code or documentation changes are draft PRs only. Do not enable
  automatic merge, release, infrastructure apply, deployment, or publishing.
- Review generated content, action logs, and compiler output before enabling
  schedules or broad event triggers.
- For public issue triage, decide explicitly whether the repository's
  integrity filtering should include issues from users without repository
  write access; do not broaden it implicitly.
- For private callers, set `inlined-imports: true` in the local source. The
  compiler embeds imported components in the consumer's generated lock file,
  so the runtime workflow does not need to check out this public catalog.

Remote import paths follow `owner/repo/path@ref`; pin `ref` to the catalog's
full 40-character commit SHA. gh-aw `import-schema` can declare typed required
or defaulted parameters for shared components (string, number, boolean,
choice, array, or one-level object). Such inputs remain part of the local
consumer source and are validated when that consumer compiles.

These patterns follow the gh-aw model described in the
[GitHub announcement](https://github.blog/ai-and-ml/automate-repository-tasks-with-github-agentic-workflows/),
the [official workflow authoring guide](https://github.github.io/gh-aw/setup/creating-workflows/),
and the current [imports](https://github.github.io/gh-aw/reference/imports/),
[safe outputs](https://github.github.io/gh-aw/reference/safe-outputs/), and
[permissions](https://github.github.io/gh-aw/reference/permissions/) references.
