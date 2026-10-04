safe-outputs:
  create-pull-request:
    max: 1
    draft: true
    fallback-as-issue: false

Review the repository's existing tests and implementation for one bounded,
evidence-backed test gap. Prefer a focused regression test for behavior that is
already implemented; do not change production behavior, weaken assertions,
remove tests, or introduce unrelated refactoring.

If a small test-only change is justified, run the relevant existing test
commands and include their exact results in the draft pull request. Otherwise,
report the finding without proposing a change. A draft pull request is a
proposal for human review and must never be merged automatically.
