# Changelog

All notable changes to this project are recorded here. Profile packages keep
their own version in `manifest.json` and `provenance.yaml`; repository releases
use the version declared in `pyproject.toml` and the Codex plugin manifest.

## Unreleased

### Added

- A fail-closed `release-check` command distinct from structural validation.
- Release gates for evidence resolution, attribution risk, counterevidence,
  reviewed imports, executed evaluations, and matching profile provenance.

## 0.1.0 - 2026-09-01

### Added

- Initial evidence contracts, profile scaffolds, repository validator, Codex
  plugin, example profiles, schemas, and legal review records.
