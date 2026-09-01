<p align="center">
  🇺🇸 English | <a href="README.zh.md">🇨🇳 中文</a>
</p>

<h1 align="center">Everyone Is a Skill</h1>

<p align="center">
  <img alt="Visibility: Private" src="https://img.shields.io/badge/visibility-private-6f42c1">
  <img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-blue">
  <img alt="Version: 0.1.0" src="https://img.shields.io/badge/version-0.1.0-2ea44f">
  <img alt="Python: 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776ab">
</p>

![Public and authorized evidence becoming inspectable, revisable Agent Skills](assets/everyone-is-skill-banner.png)

## Introduction

Everyone Is a Skill turns public or authorized evidence about a person, team, research school, creator, or body of work into inspectable, revisable, and evaluated Agent Skills.

The project distills reusable methods, judgment criteria, evidence habits, work practices, and bounded communication guidance. It does not claim to clone a person, infer private mental states, or make a language model more knowledgeable by assigning it a famous name.

> Everyone leaves learnable methods. No person is reducible to a Skill.

Version `0.1.0` established the evidence contract and packaging foundation. Current `main` also includes dependency-free local ingestion and deterministic draft distillation for Markdown, text, JSONL, subtitles, and PDFs through `pdftotext`. Live upstream adapters remain documented but are not bundled yet.

## What is included

### Portable Skill plugin

The Codex plugin at [`plugins/everyone-is-skill`](plugins/everyone-is-skill/) contains eight focused Skills:

| Skill | Use |
|---|---|
| [`everyone-is-skill`](plugins/everyone-is-skill/skills/everyone-is-skill/SKILL.md) | Route a distillation, import, update, or evaluation request |
| [`distill-scientist`](plugins/everyone-is-skill/skills/distill-scientist/SKILL.md) | Reconstruct bounded scientific methods from scholarly evidence |
| [`distill-person`](plugins/everyone-is-skill/skills/distill-person/SKILL.md) | Distill an authorized or public person profile without impersonation |
| [`distill-team`](plugins/everyone-is-skill/skills/distill-team/SKILL.md) | Recover shared operating methods while preserving disagreement |
| [`distill-content`](plugins/everyone-is-skill/skills/distill-content/SKILL.md) | Convert a source corpus into reusable procedures and guardrails |
| [`evaluate-profile`](plugins/everyone-is-skill/skills/evaluate-profile/SKILL.md) | Test grounding, specificity, transfer, and abstention |
| [`update-profile`](plugins/everyone-is-skill/skills/update-profile/SKILL.md) | Revise a profile from new evidence without erasing history |
| [`import-profile`](plugins/everyone-is-skill/skills/import-profile/SKILL.md) | Import an external profile without silently trusting or relicensing it |

### Profile contracts

A generated profile separates its runtime entry point from the evidence that supports it:

```text
profiles/<slug>/
├── SKILL.md
├── manifest.json
├── method.md
├── work.md
├── communication.md
├── context.md
├── counterevidence.md
├── provenance.yaml
├── evidence/
│   ├── claims.jsonl
│   ├── corpus-index.jsonl
│   └── lineage.json
└── evals/
    ├── temporal-holdout.json
    ├── matched-peers.json
    ├── coauthor-leakage.json
    ├── source-ablation.json
    ├── transfer-tests.json
    ├── boundary-tests.json
    └── prompt-injection.json
```

The contracts are defined in [`schemas/`](schemas/) and explained in the [profile contract](docs/profile-contract.md), [evidence policy](docs/evidence-policy.md), and [evaluation protocol](docs/evaluation.md).

### Example method profiles

- [Alexei Kitaev](profiles/examples/alexei-kitaev/): minimal models, structural protection, exact reference points, and the distinction between a fine-tuned solvable point and a robust phase.
- [Shing-Tung Yau](profiles/examples/shing-tung-yau/): global geometric targets, controlling equations, a priori estimates, compactness, regularity, existence, and rigorous enumeration.

These are examples of evidence-grounded method reconstruction, not digital replicas or claims about private intent.

## Quick start

The core validator uses only the Python standard library.

```bash
git clone https://github.com/JunkaiWang-TheoPhy/Everyone-Is-Skill.git
cd Everyone-Is-Skill
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

Markdown, text, JSONL, SRT, and VTT ingestion needs no additional runtime.
PDF ingestion is explicitly gated on Poppler's `pdftotext` executable (`brew
install poppler` on macOS or `apt install poppler-utils` on Debian/Ubuntu).
Check the current machine before a run:

```bash
everyone-skill capabilities
```

Create an inert draft profile:

```bash
everyone-skill new-profile \
  --output profiles/local \
  --slug alexei-kitaev \
  --name "Alexei Kitaev" \
  --kind scientist
```

Or turn a public or authorized local corpus into a complete, auditable draft in
one command. The offline provider only treats explicit `METHOD:` and
`COUNTEREVIDENCE:` lines as claim candidates; all other source text remains
quarantined data.

```bash
everyone-skill distill-local \
  --input path/to/corpus \
  --output profiles/local \
  --slug example-scientist \
  --name "Example Scientist" \
  --kind scientist \
  --anchor orcid=0000-0002-1825-0097 \
  --access authorized
```

Add at least one stable identity anchor to `manifest.json`, add only grounded claims to `evidence/claims.jsonl`, then validate:

```bash
everyone-skill validate profiles/local/alexei-kitaev
everyone-skill release-check profiles/local/alexei-kitaev
```

`validate` checks whether a package is structurally inspectable.
`release-check` separately fails closed on evidence, attribution, provenance,
review, and executed-evaluation gaps.

After adding recorded candidate outputs and literal expected/forbidden signals
to every evaluation case, execute all seven suites atomically:

```bash
everyone-skill run-evals profiles/local/alexei-kitaev \
  --provider recorded-output \
  --model model-version \
  --reviewer reviewer-id
```

Reference an upstream profile without copying or relicensing its content:

```bash
everyone-skill import-reference \
  --output profiles/imported \
  --slug upstream-profile \
  --name "Upstream Profile" \
  --kind scientist \
  --upstream-url https://github.com/example/profile \
  --upstream-license MIT
```

The scaffold is deliberately incomplete: it starts as `draft`, contains no claims, and fails release-oriented validation until identity, evidence, and boundaries are present. A reference import records the upstream as unreviewed and bundles no upstream code or profile text.

## Architecture

```text
public or authorized sources
        ↓
identity resolution and rights boundary
        ↓
normalized corpus index
        ↓
claim-level evidence ledger
        ↓
method and capability distillation
        ↓
counterevidence and attribution audit
        ↓
temporal, peer, transfer, and boundary evaluation
        ↓
versioned portable Skill package
```

Read the full [architecture](docs/architecture.md) and [integration design](docs/integrations.md).

## Evidence rules

- Identity must be anchored before attribution.
- Person-specific claims must link to source IDs.
- Coauthored work carries explicit attribution risk.
- Field-generic good practice is not automatically person-specific.
- Counterevidence and changes over time remain visible.
- Communication guidance is optional and must not imitate signature phrases.
- Raw copyrighted or private corpora stay outside the public package.
- A useful answer is not proof of person fidelity.

## Evaluation

Profiles are evaluated along separate axes:

- citation and evidence coverage;
- temporal hold-out;
- matched-peer discrimination;
- coauthor leakage;
- source ablation;
- transfer to a nearby but unseen task;
- boundary abstention;
- retrieved-source prompt-injection resistance.

The repository includes synthetic baseline and forward-pressure specifications under [`evals/skill-behavior`](evals/skill-behavior/). They are test definitions, not claimed execution results.

## Upstream projects and acknowledgements

Everyone Is a Skill does not vendor third-party source code in `0.1.0`. It provides documented adapter boundaries and credits the projects that made this design space possible, including Distill-Everything, anything2skill, sci-brain, Research Taste Distillation, Nuwa, Distilly, Person Distillation, MirrorMind, Virtual Scientists, K-Dense scientific agents, and OmniScientist V2.

See [Acknowledgements](ACKNOWLEDGEMENTS.md), [Third-Party Notices](THIRD_PARTY_NOTICES.md), and the pinned [integration ledger](integrations/integrations.lock.yaml).

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src
```

Plugin and Skill validation uses the validators bundled with Codex:

```bash
python3 "$HOME/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py" \
  plugins/everyone-is-skill

for skill in plugins/everyone-is-skill/skills/*; do
  python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" "$skill"
done
```

See [Contributing](CONTRIBUTING.md) and [Security](SECURITY.md) before adding adapters or public profiles.

## License

Original Everyone Is a Skill code and documentation are licensed under the [Apache License 2.0](LICENSE). Referenced upstream projects retain their original licenses. Source corpora, generated profiles, quotations, and imported artifacts may have separate rights and must not be silently relicensed.
