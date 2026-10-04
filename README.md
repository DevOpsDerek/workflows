# DevOpsDerek Workflows

Public, centrally maintained reusable GitHub Actions and GitHub Agentic
Workflow (gh-aw) components for DevOpsDerek repositories.

- [Reusable workflow and composite-action catalog](docs/catalog.md)
- [Shared agentic patterns and consumer setup](docs/agentic-patterns.md)
- [Compatibility and privacy guidance](docs/compatibility.md)

Consumers should pin every reference to this repository to a full, immutable
40-character commit SHA. Each consuming repository keeps its own gh-aw trigger
source and generated `.lock.yml`; reusable prompt/configuration components are
imported from this catalog.
