safe-outputs:
  create-issue:
    max: 1
    title-prefix: "[CI diagnosis] "
    labels:
      - automation
      - ci-diagnosis

Investigate only the completed workflow run that triggered this workflow.
Inspect the failing job's available logs, identify the first actionable failure,
and distinguish a confirmed root cause from a hypothesis. Check for an existing
issue describing the same failure before proposing a new one.

Use the bounded safe output to propose a diagnostic issue only when the failure
is reproducible from the available evidence and no duplicate is apparent.
Include the run link, affected job and step, concise evidence, and a small
human-verifiable next step. Do not rerun jobs, modify source or workflows,
change repository settings, or propose a merge, deployment, release, or
publishing action.
