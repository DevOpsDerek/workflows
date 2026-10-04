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
  create-pull-request:
    max: 1
    draft: true
    fallback-as-issue: false
    allowed-files:
      - "tests/**"
      - "test/**"
      - "**/tests/**"
      - "**/test/**"
      - "**/*_test.*"
      - "**/test_*.*"
      - "**/*.test.*"
      - "**/*.spec.*"
      - "**/*Tests.cs"
      - "**/*Test.cs"
      - "**/*.tftest.hcl"
---

Review the repository's existing tests and implementation for one bounded,
evidence-backed test gap. Prefer a focused regression test for behavior that is
already implemented; do not change production behavior, weaken assertions,
remove tests, or introduce unrelated refactoring.

If a small test-only change is justified, include the repository's documented
test command and report whether it was actually run; never claim success
without completed output. If an appropriate command is unavailable, state that
the change is untested. Otherwise, report the finding without proposing a
change. A draft pull request is a proposal for human review and must never be
merged automatically.
