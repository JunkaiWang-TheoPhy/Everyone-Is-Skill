# Architecture

Everyone-Is-Skill is organized around one hard boundary: distill reusable
methods from public or authorized evidence without collapsing a person or team
into an impersonation target.

## Design center

The repository keeps the runtime contract intentionally small so the current
CLI can scaffold and validate inert profile packages with no external
dependencies. Richer semantics live in documentation, JSON Schemas, and
templates. This lets us expand evidence and evaluation guidance without
breaking `src/everyone_is_skill/contracts.py`, `packaging.py`, or `cli.py`.

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
status plus a cases array. Rich release semantics remain governed by policy and
the versioned JSON Schemas.

## Separation of responsibilities

- `docs/` defines policy, interpretation, and release expectations.
- `schemas/` defines non-breaking JSON shape guidance that is richer than the
  current runtime validator.
- `templates/` provides valid inert scaffolds for new profile kinds.
- `src/everyone_is_skill/contracts.py` remains the compatibility boundary for
  current automation.

## Non-goals

- No claim that a profile reproduces private thought or identity.
- No voice cloning, signature-phrase mimicry, or roleplay target.
- No promotion from `person-specific-candidate` to `supported-method` without
  source-backed evidence and counterevidence review.
- No assumption that coauthored output cleanly identifies one contributor's
  method without explicit risk annotation.
