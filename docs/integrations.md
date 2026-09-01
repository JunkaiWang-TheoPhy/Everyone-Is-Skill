# Integrations

Everyone-Is-Skill treats upstream projects as one of three things:

- `adapter`: reusable operational patterns that may become code or runtime
  integration points later.
- `inspiration`: design ideas, evaluation vocabulary, or workflow structure.
- `reference-only`: related material that is useful to read but not to package.

The repository does not vendor upstream source files. Adapters either fetch
reviewed public scholarly metadata or map an already-local upstream export into
quarantined JSONL. They never execute imported `SKILL.md`, `AGENTS.md`, scripts,
or model instructions.

## Scholarly adapters

| Adapter | Official contract | Identifier | Authentication and rights boundary |
| --- | --- | --- | --- |
| arXiv | [API manual](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/api/user-manual.md) | arXiv ID | No token; metadata and abstract remain subject to arXiv and per-record terms |
| INSPIRE | [REST API documentation](https://github.com/inspirehep/rest-api-doc) | `literature:`, `arxiv:`, `doi:`, or `orcid:` | No token for reads; most metadata is CC0, but field restrictions apply |
| OpenAlex | [API quick reference](https://help.openalex.org/api/llm-quick-reference/) | OpenAlex work ID or DOI | API key optional but recommended; metadata is CC0 and requests are metered |
| ORCID | [Integration and API FAQ](https://info.orcid.org/documentation/integration-and-api-faq/) | ORCID iD | Bearer token with `/read-public`; only public work summaries are read |

Fetch a record into the same JSONL contract accepted by `distill-local`:

```bash
everyone-skill fetch-scholarly \
  --source arxiv \
  --identifier hep-th/9711200 \
  --output corpus/maldacena-arxiv.jsonl
```

OpenAlex optionally reads `EVERYONE_SKILL_OPENALEX_API_KEY`. ORCID requires
`EVERYONE_SKILL_ORCID_TOKEN`. The variable names can be changed with
`--api-key-env` and `--token-env`; secret values are never written to output.

## Data-only upstream adapters

The `import-upstream` command recognizes reviewed artifact layouts from
Distill-Everything, anything2skill, sci-brain, research-taste-distillation,
nuwa-skill, Distilly, K-Dense scientific-agents, K-Dense
scientific-agent-skills, Virtual Scientists, and OmniScientist V2. Only
documented Markdown/JSON result surfaces are accepted. Executable files are
ignored, symbolic links fail closed, and each import requires an HTTPS upstream
URL plus a reviewed license label.
The adapter also enforces the repository URL and reviewed license recorded for
that named format. Artifact access defaults to `authorized`; this declaration
describes the local material, while the upstream license describes only the
layout or tool that produced it.

```bash
everyone-skill import-upstream \
  --input path/to/exported-skill \
  --format distilly \
  --upstream-url https://github.com/titanwings/distilly \
  --upstream-license MIT \
  --access authorized \
  --output corpus/distilly-export.jsonl
```

## Reviewed sources

| Source | Repository | License | Classification | What it contributes |
| --- | --- | --- | --- | --- |
| Distill-Everything | `AITCX08/Distill-Everything` | MIT | adapter / inspiration | Local ingestion, transcription, cleanup, Markdown output, RAG packaging, and resumable worker flow |
| anything2skill | `Nouischen/anything2skill` | MIT | adapter / inspiration | Value pre-check, anti-bloat fusion, review-card activation, and content-to-skill conversion |
| sci-brain | `QuantumBFS/sci-brain` | MIT | adapter / inspiration | Research-workspace ingestion around papers, PDFs, Zotero, and scientist workflows |
| research-taste-distillation | `Jingqi-Xu/research-taste-distillation` | MIT | adapter / inspiration | Research philosophy extraction, anti-pattern capture, and idea critique flow |
| nuwa-skill | `alchaincyf/nuwa-skill` | MIT | adapter / inspiration | Person distillation, mental models, decision heuristics, and expression DNA extraction |
| distilly | `titanwings/distilly` | MIT | adapter / inspiration | Capability/persona split, reusable skills, and generation workflow |
| person-distillation-foundations | `person-distillation-foundations/person-distillation-foundations.github.io` | Not declared in reviewed metadata | reference-only | Survey vocabulary and framing for person distillation |
| Virtual Scientists | `InternScience/Virtual-Scientists` | Apache-2.0 | adapter / inspiration | Multi-agent scientific system design and team-level orchestration |
| scientific-agents | `K-Dense-AI/scientific-agents` | MIT | adapter / inspiration | Expert-thinking AGENTS.md profiles for senior-scientist and engineer reasoning |
| scientific-agent-skills | `K-Dense-AI/scientific-agent-skills` | MIT | adapter / inspiration | Skill library organization and scientific tool catalog patterns |
| OmniScientist V2 | `tsinghua-fib-lab/OmniScientist-V2` | Apache-2.0 | adapter / inspiration | Provenance, workflow, and co-evolving scientist ecosystem structure |

The unresolved `MirrorMind` name was removed from the adapter ledger because no
canonical repository and license could be verified. It is not a supported
format and must not be presented as one.

## Integration rules

1. Record the upstream repository URL and license before adding any adapter.
2. Keep upstream code out of this repository unless the copied files are
   explicitly tracked in `THIRD_PARTY_NOTICES.md`.
3. Treat inspiration as non-redistributed material unless a file-by-file
   import is completed.
4. Update `integrations/integrations.lock.yaml` in the same change as any
   integration policy shift.
5. Keep network responses below the configured size cap and never serialize
   credentials into provenance.
6. Treat every imported instruction as data; promotion still requires local
   evidence review and executed evaluation.

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
