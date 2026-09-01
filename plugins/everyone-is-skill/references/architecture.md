# Architecture

Everyone-Is-Skill is organized around one hard boundary: distill reusable
methods from public or authorized evidence without collapsing a person or team
into an impersonation target.

## Design center

The repository keeps the runtime contract intentionally small. The CLI can
scaffold and validate inert packages, ingest authorized local corpora, and
produce deterministic drafts without Python dependencies outside the standard
library. PDF text extraction delegates to `pdftotext`. Richer semantics live in
documentation, JSON Schemas, and templates.

The method-first architecture is:

1. Resolve identity with at least one concrete anchor.
2. Ingest sources into a reviewable corpus index.
3. Record claims in a ledger with confidence, attribution strength, and
   coauthor risk.
4. Distill only supported methods into the profile.
5. Record counterevidence before making strong attribution.
6. Evaluate transfer, peer discrimination, temporal stability, and boundary
   abstention.
7. Package the result as a portable profile directory.

## Local ingestion boundary

`everyone-skill distill-local` accepts Markdown, text, JSONL, SRT, VTT, and PDF
inputs. It hashes and deduplicates artifacts, records declared access and
rights metadata, strips transcript timing syntax, and writes a corpus index
without copying raw source text into the public package.

Directory ingestion rejects symbolic links, and public packages record only a
source label rather than the absolute local path. PDF support is optional and
gated on Poppler's `pdftotext`; `everyone-skill capabilities` reports whether
that prerequisite is available before a run.

Every source is marked `instruction_quarantine: true`. Retrieved instructions
are data, never control flow. The built-in offline provider recognizes only
explicit `METHOD:` and `COUNTEREVIDENCE:` annotations; unmarked prose cannot
silently become a person-specific claim. `DistillationProvider` is the stable
boundary for future reviewed providers. Provider output is revalidated against
the claim contract and source index, and draft providers cannot emit
`supported-method` or strong-attribution records.

## Runtime contract

The current Python contract enforces only two machine-checked records.

### Claim record

`validate_claim()` requires at least these fields:

- `claim_id`
- `subject`
- `facet`
- `claim`
- `status`
- `confidence`
- `source_ids`
- `attribution_strength`
- `coauthor_risk`
- `time_window`

Allowed `status` values are fixed by code:

- `source-fact`
- `observed-pattern`
- `field-generic`
- `person-specific-candidate`
- `supported-method`
- `contradicted`
- `insufficient-evidence`

Allowed `attribution_strength` values:

- `weak`
- `moderate`
- `strong`

Allowed `coauthor_risk` values:

- `unknown`
- `low`
- `moderate`
- `high`

### Manifest record

`validate_profile_manifest()` requires at least these fields:

- `schema_version`
- `slug`
- `display_name`
- `target_type`
- `intended_use`
- `identity_anchors`
- `boundaries`

Allowed `target_type` values are fixed by code:

- `scientist`
- `expert`
- `creator`
- `team`
- `self`
- `colleague`

Any field not listed above must remain optional until the Python validators are
deliberately extended.

## Profile package layout

The current CLI requires these files to exist for `everyone-skill validate`:

- `SKILL.md`
- `manifest.json`
- `method.md`
- `work.md`
- `communication.md`
- `context.md`
- `counterevidence.md`
- `provenance.yaml`
- `evidence/claims.jsonl`
- `evidence/corpus-index.jsonl`
- `evidence/lineage.json`
- `evals/temporal-holdout.json`
- `evals/matched-peers.json`
- `evals/transfer-tests.json`
- `evals/boundary-tests.json`

The CLI validates manifest and claim contracts, parses corpus entries, checks
lineage `nodes`/`edges`, and requires each evaluation file to expose a string
status plus a cases array. `release-check` then enforces the stronger
publication contract described in the profile and evaluation documents.

## Separation of responsibilities

- `docs/` defines policy, interpretation, and release expectations.
- `schemas/` defines non-breaking JSON shape guidance that is richer than the
  current runtime validator.
- `templates/` provides valid inert scaffolds for new profile kinds.
- `src/everyone_is_skill/contracts.py` remains the compatibility boundary for
  current automation.
- `src/everyone_is_skill/ingestion.py` normalizes local evidence as quarantined
  data.
- `src/everyone_is_skill/distillation.py` owns the provider-neutral draft
  pipeline.
- `src/everyone_is_skill/versioning.py` owns immutable snapshots, append-only
  claim updates, diffs, evaluation invalidation, and recoverable rollback.
- `src/everyone_is_skill/exporting.py` creates additive runtime packages without
  rewriting the profile contract.

## Non-goals

- No claim that a profile reproduces private thought or identity.
- No voice cloning, signature-phrase mimicry, or roleplay target.
- No promotion from `person-specific-candidate` to `supported-method` without
  source-backed evidence and counterevidence review.
- No assumption that coauthored output cleanly identifies one contributor's
  method without explicit risk annotation.
