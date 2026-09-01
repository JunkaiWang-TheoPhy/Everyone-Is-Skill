# Profile Contract

This document defines the stable package contract for profiles in this
repository.

## Compatibility rule

The current compatibility boundary is the combination of:

- `src/everyone_is_skill/contracts.py`
- `src/everyone_is_skill/packaging.py`
- `src/everyone_is_skill/cli.py`

If a field name, enum value, or required file is not recognized there, do not
make it mandatory in templates, schemas, or documentation. Additions are
allowed only as optional guidance.

## Required manifest fields

`manifest.json` must contain:

- `schema_version`
- `slug`
- `display_name`
- `target_type`
- `intended_use`
- `identity_anchors`
- `boundaries`

Additional fields such as `status`, `method_scope`, or `evaluation_focus` are
allowed as optional metadata but cannot be required for current validation.

`release-check` applies a stricter, status-aware contract without changing the
structural contract above. A release-ready profile must declare a semantic
`profile_version`, use `status: "release-ready"`, and repeat the same version in
`provenance.yaml`. Imported profiles must set `imported_from.trust: reviewed`.

## Required evidence claim fields

Each non-empty line in `evidence/claims.jsonl` must be a JSON object with:

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

Recommended optional extensions include:

- `transfer_scope`
- `counterevidence_ids`
- `notes`
- `reviewed_by`
- `method_tags`

These optional fields must never replace the required contract fields.

## Required files

The CLI currently checks for:

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

Release-ready profiles additionally require:

- `evals/coauthor-leakage.json`
- `evals/source-ablation.json`
- `evals/prompt-injection.json`

## Template rules

Templates in `templates/scientist/` and `templates/team/` must:

- validate with the current CLI without code changes,
- include at least one placeholder identity anchor,
- keep `evidence/claims.jsonl` empty,
- keep `evidence/lineage.json` as empty `nodes` and `edges`,
- and initialize all four evaluation files with `status: "not-run"`.

This gives downstream tooling a valid inert package while making the missing
evidence obvious.

## Release-ready rules

`everyone-skill release-check PROFILE` fails closed unless all of the following
are true:

- at least one identity anchor is real rather than a template value;
- `evidence/claims.jsonl` contains claims and every referenced source identifier
  resolves in `evidence/corpus-index.jsonl`;
- every `supported-method` claim uses at least two distinct sources;
- strong attribution has resolved coauthor risk and completed counterevidence;
- all seven release evaluation files have executed cases, reproducibility
  metadata, and `status: "passed"`;
- provenance is reviewed and its version matches the manifest; and
- any imported profile has passed an explicit trust review.

Structural `validate` deliberately continues to accept inert drafts. Passing
that command means the package can be inspected and migrated; it does not mean
the profile is publishable.

## Method-first contract

`method.md` is the primary operational file. It should capture:

- the smallest reusable method kernel,
- how to decide whether the method applies,
- what evidence is needed before strong use,
- and what failure modes require abstention.

`communication.md` is subordinate and optional in practice. It may describe
clarity, structure, or degree of compression, but it must not instruct the
agent to impersonate the subject or reproduce signature phrasing.

## Team-specific note

`target_type: "team"` still uses the same manifest contract. The difference is
semantic: claims should default to collective process, review path, division of
labor, and disagreement handling rather than attributing every pattern to a
single leader.
