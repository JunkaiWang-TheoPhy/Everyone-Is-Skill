---
name: evaluate-profile
description: Use when checking whether an Everyone-Is-Skill profile is evidence-backed, discriminative, bounded, and ready for release.
---

# Evaluate Profile

Check whether the profile is both grounded and actually distinctive.

1. Validate manifest, claims, provenance, and required eval files.
2. Test temporal holdout, matched-peer discrimination, transfer, and boundary abstention.
3. Downgrade unsupported certainty and record counterevidence instead of hiding it.
4. Report release status with concrete blockers.

Read [evaluation protocol](../../references/evaluation.md), [profile contract](../../references/profile-contract.md), [profile schema](../../schemas/profile.schema.json), and [claim schema](../../schemas/claim.schema.json).

A profile is not ready if it only sounds plausible, duplicates field-generic advice, or lacks evidence-linked claims.
