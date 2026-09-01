---
name: evaluate-profile
description: Use when checking whether an Everyone-Is-Skill profile is evidence-backed, discriminative, bounded, and ready for release.
---

# Evaluate Profile

Check whether the profile is both grounded and actually distinctive.

1. Validate manifest, claims, provenance, and required eval files.
2. Test temporal holdout, matched-peer discrimination, coauthor leakage, source ablation, transfer, boundary abstention, and prompt injection.
3. Downgrade unsupported certainty and record counterevidence instead of hiding it.
4. Report release status with concrete blockers.

Use `everyone-skill run-evals` to execute recorded-output cases and persist the
provider, model, source snapshot, rubric, component scores, reviewer, and
verdict. Then use `everyone-skill release-check`; a handwritten `passed` label
without execution evidence must not pass.

Read [evaluation protocol](../../references/evaluation.md), [profile contract](../../references/profile-contract.md), [profile schema](../../schemas/profile.schema.json), and [claim schema](../../schemas/claim.schema.json).

A profile is not ready if it only sounds plausible, duplicates field-generic advice, or lacks evidence-linked claims.
