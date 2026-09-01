# Integrations

Everyone-Is-Skill treats upstream projects as one of three things:

- `adapter`: reusable operational patterns that may become code or runtime
  integration points later.
- `inspiration`: design ideas, evaluation vocabulary, or workflow structure.
- `reference-only`: related material that is useful to read but not to package.

The current repository scaffold does not vendor upstream source files. That
boundary is deliberate: we want to preserve provenance, keep license terms
separable, and avoid blurring inspiration with redistribution.

## Reviewed sources

| Source | Repository | License | Classification | What it contributes |
| --- | --- | --- | --- | --- |
| Distill-Everything | `AITCX08/Distill-Everything` | MIT | adapter / inspiration | Local ingestion, transcription, cleanup, Markdown output, RAG packaging, and resumable worker flow |
| anything2skill | `Nouischen/anything2skill` | MIT | inspiration | Value pre-check, anti-bloat fusion, review-card activation, and content-to-skill conversion |
| sci-brain | `QuantumBFS/sci-brain` | MIT | adapter / inspiration | Research-workspace ingestion around papers, PDFs, Zotero, and scientist workflows |
| research-taste-distillation | `Jingqi-Xu/research-taste-distillation` | MIT | inspiration | Research philosophy extraction, anti-pattern capture, and idea critique flow |
| nuwa-skill | `alchaincyf/nuwa-skill` | MIT | inspiration | Person distillation, mental models, decision heuristics, and expression DNA extraction |
| distilly | `titanwings/distilly` | MIT | inspiration | Capability/persona split, reusable skills, and generation workflow |
| person-distillation-foundations | `person-distillation-foundations/person-distillation-foundations.github.io` | Not declared in reviewed metadata | reference-only | Survey vocabulary and framing for person distillation |
| Virtual Scientists | `InternScience/Virtual-Scientists` | Apache-2.0 | inspiration | Multi-agent scientific system design and team-level orchestration |
| scientific-agents | `K-Dense-AI/scientific-agents` | MIT | adapter / inspiration | Expert-thinking AGENTS.md profiles for senior-scientist and engineer reasoning |
| scientific-agent-skills | `K-Dense-AI/scientific-agent-skills` | MIT | adapter / inspiration | Skill library organization and scientific tool catalog patterns |
| OmniScientist V2 | `tsinghua-fib-lab/OmniScientist-V2` | Apache-2.0 | adapter / inspiration | Provenance, workflow, and co-evolving scientist ecosystem structure |

## Unresolved reference

`MirrorMind` was listed during review, but a single canonical GitHub repository
could not be confirmed with enough confidence to enter the lock file. Do not
copy code or record license terms for that name until the exact upstream
repository is identified.

## Integration rules

1. Record the upstream repository URL and license before adding any adapter.
2. Keep upstream code out of this repository unless the copied files are
   explicitly tracked in `THIRD_PARTY_NOTICES.md`.
3. Treat inspiration as non-redistributed material unless a file-by-file
   import is completed.
4. Update `integrations/integrations.lock.yaml` in the same change as any
   integration policy shift.

## What belongs here

- source repo identity
- license status
- what we reuse
- what we do not reuse
- the date the source was reviewed

## What does not belong here

- copied upstream source code
- private notes about maintainers
- unverified claims about licensing or provenance
- marketing language that cannot be tied back to a source
