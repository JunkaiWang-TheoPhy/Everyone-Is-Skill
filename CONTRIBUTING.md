# Contributing

Thank you for helping improve Everyone-Is-Skill.

## Before you change anything

- Add or update focused tests before changing runtime behavior.
- Keep the core validator dependency-free unless a dependency is explicitly
  approved and justified.
- Keep upstream code out of the repository unless the change is explicitly
  tracked as a vendored third-party file.
- Update `integrations/integrations.lock.yaml` before you update attribution
  files that depend on it.
- If you add a new upstream source, record the repository URL, license status,
  and the exact reason it belongs here.

## What to change for a new source

1. Add or update the lock entry in `integrations/integrations.lock.yaml`.
2. Mirror the same source in `docs/integrations.md`.
3. Add a human-readable acknowledgement in `ACKNOWLEDGEMENTS.md`.
4. If any upstream text or code is redistributed, add the exact file list to
   `THIRD_PARTY_NOTICES.md`.

## Style

- Keep entries factual and specific.
- Use the upstream repository name exactly as reviewed.
- Do not claim a license unless the repository metadata or upstream license
  file shows it.
- Mark unresolved items clearly instead of guessing.

## Review checklist

- Unit tests and repository validation pass.
- Changed Skills pass the Codex Skill validator.
- Plugin metadata passes the Codex plugin validator.
- JSON, YAML, CFF, and Markdown links are valid for the touched scope.
- The source is identified by repository URL.
- The license is declared or explicitly marked as unresolved.
- The file is classified as adapter, inspiration, reference-only, or
  unresolved.
- No upstream source files were copied unless the notices file was updated.

## Questions that should block a change

- Is the upstream repository actually the one we think it is?
- Are we copying code or only recording inspiration?
- Does the upstream license allow the intended use?

If any answer is unclear, stop and resolve the source record first.
