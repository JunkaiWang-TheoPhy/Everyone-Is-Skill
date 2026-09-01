---
name: update-profile
description: Use when an existing Everyone-Is-Skill profile needs revision because new evidence, corrections, or attribution changes have arrived.
---

# Update Profile

Revise incrementally and preserve auditability.

1. Load the existing profile, then identify exactly which claims the new evidence changes.
2. Preserve stable claim IDs when the claim meaning is unchanged; supersede or retire them when it is not.
3. Update counterevidence, provenance, and eval scenarios together with the skill text.
4. Record what changed, why it changed, and what remains unresolved.

Read [evidence policy](../../references/evidence-policy.md), [evaluation protocol](../../references/evaluation.md), [profile schema](../../schemas/profile.schema.json), and [claim schema](../../schemas/claim.schema.json).

Do not rewrite history, silently delete conflicting evidence, or widen the profile target without fresh identity checks.
