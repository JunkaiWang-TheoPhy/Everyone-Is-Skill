# Changelog

All notable changes to this project are recorded here. Profile packages keep
their own version in `manifest.json` and `provenance.yaml`; repository releases
use the version declared in `pyproject.toml` and the Codex plugin manifest.

## Unreleased

### Added

- A fail-closed `release-check` command distinct from structural validation.
- Release gates for evidence resolution, attribution risk, counterevidence,
  reviewed imports, executed evaluations, and matching profile provenance.
- Local Markdown, text, JSONL, transcript, and PDF ingestion with deterministic
  source identities, deduplication, rights metadata, and instruction quarantine.
- A provider-neutral distillation boundary and deterministic offline provider
  for complete, structurally valid draft packages.
- An atomic seven-suite evaluation runner with reproducibility metadata,
  separate method/boundary scores, negative-control failure reasons, and a
  release gate that rejects forged `passed` labels.

## 0.1.0 - 2026-09-01

### Added

- Initial evidence contracts, profile scaffolds, repository validator, Codex
  plugin, example profiles, schemas, and legal review records.
