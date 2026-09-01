---
name: import-profile
description: Use when converting an external skill, profile repo, or upstream distillation artifact into the Everyone-Is-Skill package format.
---

# Import Profile

Import structure and evidence, not upstream marketing copy.

1. Identify the upstream profile type, license, and attribution requirements.
2. Map upstream fields into local manifest, claims, provenance, and eval files.
3. Preserve source links and mark unresolved gaps instead of inventing replacements.
4. Re-evaluate imported claims under local evidence and boundary rules.

Read [profile contract](../../references/profile-contract.md), [evidence policy](../../references/evidence-policy.md), [profile schema](../../schemas/profile.schema.json), and [claim schema](../../schemas/claim.schema.json).

Use `everyone-skill import-upstream` for a reviewed local export. Select the
named upstream format, require its canonical HTTPS URL and reviewed license,
and emit quarantined JSONL for the local distillation pipeline. Never execute
an imported script, engine, or hook. Runtime instruction surfaces such as
`SKILL.md`, `AGENTS.md`, and `CLAUDE.md` are ignored rather than entering the
evidence corpus.

Do not treat imported confidence, persona text, or branding language as verified local evidence.
