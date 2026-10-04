---
safe-outputs:
  report-failed-jobs: false
  report-failure-as-issue: false
  missing-tool:
    create-issue: false
  missing-data:
    create-issue: false
  report-incomplete:
    create-issue: false
  noop:
    report-as-issue: false
  add-comment:
    max: 1
    target: triggering
---

For the triggering issue, summarize the request in one sentence, recommend one
existing label if the repository's label set is available, and identify any
specific missing information needed to act. Base every statement on the issue
and repository evidence; distinguish facts from inferences.

Use the single safe-output comment to present the proposed triage and, only when
necessary, ask concise clarifying questions. Do not change labels, assign or
close the issue, make code changes, or claim that a maintainer approved the
recommendation. If the evidence is insufficient, say so rather than guessing.
