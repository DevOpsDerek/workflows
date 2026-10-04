safe-outputs:
  create-pull-request:
    max: 1
    draft: true
    fallback-as-issue: false

Compare the repository's public documentation with recent, directly relevant
code changes. Propose at most one small documentation-only correction where
the mismatch is clear. Do not infer undocumented product behavior, edit source
code, update generated API references without running their documented
generator, or include secrets, credentials, or private user data.

Run the repository's relevant documentation checks and report their exact
results in the draft pull request. A draft pull request is a proposal for human
review and must never be merged automatically.
