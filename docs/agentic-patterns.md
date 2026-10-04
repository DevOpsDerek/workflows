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
  contents: read
  issues: read
inlined-imports: true
imports:
  - DevOpsDerek/workflows/.github/workflows/shared/agentic/issue-triage.md@<40_CHARACTER_COMMIT_SHA>
tools:
  github:
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
permissions:
  actions: read
  contents: read
  issues: read
inlined-imports: true
imports:
  - DevOpsDerek/workflows/.github/workflows/shared/agentic/ci-failure-diagnosis.md@<40_CHARACTER_COMMIT_SHA>
tools:
  github:
---

Follow the imported CI diagnosis instructions for the completed run.
```

## Test-quality assistance

Use a manual or scheduled trigger initially. The component permits at most one
draft PR, restricted to a focused test-only improvement; a human must review
and merge it.

```markdown
---
on:
  workflow_dispatch:
permissions:
  contents: read
  pull-requests: read
inlined-imports: true
imports:
  - DevOpsDerek/workflows/.github/workflows/shared/agentic/test-quality.md@<40_CHARACTER_COMMIT_SHA>
tools:
  github:
---

Follow the imported test-quality instructions. Use only the repository's
documented test commands and report the commands and results.
```

## Documentation upkeep

Use a manual or scheduled trigger at first. The component permits at most one
draft PR, restricted to documentation-only changes and subject to human review.

```markdown
---
on:
  workflow_dispatch:
permissions:
  contents: read
  pull-requests: read
inlined-imports: true
imports:
  - DevOpsDerek/workflows/.github/workflows/shared/agentic/documentation-upkeep.md@<40_CHARACTER_COMMIT_SHA>
tools:
  github:
---

Follow the imported documentation-upkeep instructions. Use only the
repository's documented documentation checks and report the commands and
results.
```

In every case, install/configure gh-aw in the consumer, commit the Markdown
source and compiled `.lock.yml` together, and review both files before
enabling the trigger. After changing frontmatter or imports, rerun
`gh aw compile`; review body-only changes as well.

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
