# Changelog

All notable changes to this project are recorded here. Profile packages keep
their own version in `manifest.json` and `provenance.yaml`; repository releases
use the version declared in `pyproject.toml` and the Codex plugin manifest.

## Unreleased

No unreleased changes.

## 1.0.0 - 2026-09-02

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
- Live, bounded metadata adapters for arXiv, INSPIRE, OpenAlex, and ORCID, with
  credential redaction and JSONL handoff to local distillation.
- Data-only adapters for ten reviewed upstream artifact layouts; runtime
  instruction surfaces and executable files are never copied, while accepted
  result data remains quarantined.
- Removal of the unresolved MirrorMind entry from the supported integration
  ledger.
- Nine evidence-complete scientist method profiles plus a comparative
  collective that preserves historical phases, roles, and dissent.
- Independent repository peer review and two-run, seven-suite behavior records
  for the Kitaev, Yau, and Maldacena profiles.
- Immutable profile snapshots, append-only source/claim updates, machine-readable
  diffs, evaluation invalidation, and safety-snapshotted rollback.
- Contract-preserving exports for Codex, Claude Code, OpenClaw, and AGENTS.md
  runtimes.

## 0.1.0 - 2026-09-01

### Added

- Initial evidence contracts, profile scaffolds, repository validator, Codex
  plugin, example profiles, schemas, and legal review records.
