# Versioning, updates, and runtime export

Profiles are append-only evidence packages. New evidence must not silently
rewrite a reviewed profile.

## Update lifecycle

`update-claim` accepts one JSON source record and one JSON claim record. Before
writing either record, it creates an immutable snapshot under
`history/<snapshot-id>/`. A successful update:

- appends the source and claim;
- increments the profile patch version;
- lowers the profile to `evidence-complete`;
- removes the previous peer-review marker;
- invalidates all seven evaluations; and
- appends an event to `history.jsonl`.

```bash
everyone-skill update-claim profiles/local/example \
  --source new-source.json \
  --claim new-claim.json \
  --reason "add the 2026 follow-up paper"
```

Create an extra checkpoint or inspect drift:

```bash
everyone-skill snapshot-profile profiles/local/example --reason "before attribution review"
everyone-skill diff-profile profiles/local/example --snapshot SNAPSHOT_ID
```

`rollback-profile` first snapshots the current state, then restores the exact
recorded files. The safety snapshot means rollback is itself recoverable.

```bash
everyone-skill rollback-profile profiles/local/example \
  --snapshot SNAPSHOT_ID \
  --reason "restore the reviewed evidence set"
```

## Cross-runtime export

The same portable contract is exported for Codex, Claude Code, OpenClaw, and an
AGENTS.md-compatible host:

```bash
everyone-skill export-profile profiles/local/example \
  --runtime codex \
  --output dist/
```

Exports contain the profile contract and evidence but omit local history.
Runtime-specific metadata is additive. `contract_modified: false` records that
claims, boundaries, and evidence were not rewritten for the destination. The
`agents-md` export adds an `AGENTS.md` entrypoint while retaining `SKILL.md` and
the original evidence package.
