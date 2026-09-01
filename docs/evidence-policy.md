# Evidence Policy

This repository accepts only evidence-grounded method distillation. The output
is a bounded operational profile, not a simulated person.

## Evidence standard

Every non-trivial claim must be traceable to one or more source identifiers in
`evidence/claims.jsonl`. Claims are valid only when they remain inside the
contract enforced by `validate_claim()` and the interpretation rules below.

### Claim status intent

- `source-fact`: directly supported source metadata or plain source content.
- `observed-pattern`: a recurring pattern observed across sources.
- `field-generic`: common field practice that should not be over-attributed.
- `person-specific-candidate`: plausible individual attribution awaiting
  stronger support.
- `supported-method`: sufficiently supported reusable method inside the scoped
  transfer domain.
- `contradicted`: challenged by direct counterevidence or later material.
- `insufficient-evidence`: too weak to operationalize or attribute.

Only `supported-method` claims belong in a release-ready method profile.

## Source requirements

- `source_ids` must be non-empty.
- The source list should span more than one artifact when a claim is both
  person-specific and high-impact.
- Sources should cover time, not just one public appearance.
- Coauthored material is allowed, but the claim must carry explicit
  `coauthor_risk`.

## Attribution and coauthor risk

`attribution_strength` and `coauthor_risk` are first-class fields because
person distillation fails when multi-author work is treated as single-author
evidence by default.

Use `coauthor_risk` this way:

- `unknown`: authorship contribution is unresolved.
- `low`: repeated single-author or strongly corroborated evidence supports the
  attribution.
- `moderate`: plausible attribution exists, but collaborator effects remain.
- `high`: the claim likely reflects team, field, or collaborator structure more
  than one subject.

High `coauthor_risk` should usually block promotion to `supported-method`
unless additional sources materially reduce uncertainty.

## Counterevidence policy

Counterevidence is mandatory whenever a claim is:

- strongly attributed,
- time-sensitive,
- contradicted by later work,
- difficult to separate from collaborator influence,
- or vulnerable to persona overreach.

`counterevidence.md` should record:

- direct exceptions,
- changes over time,
- rival explanations,
- scope limits,
- and reasons a tempting claim remained below `supported-method`.

## Anti-impersonation boundary

Evidence may justify method transfer. It does not justify:

- writing as if the subject is present,
- claiming access to intent or private states,
- copying signature wording as proof of fidelity,
- inferring hidden motivations from sparse evidence.

Profiles must prefer operational instructions and abstention rules over style
imitation.

## Corpus index expectations

`evidence/corpus-index.jsonl` should identify what entered review, even when a
claim was rejected. A useful entry usually includes source identity, source
type, date or time range, access status, and short notes about relevance. The
current CLI does not validate these fields yet, so the schema remains advisory
and all additions beyond basic JSON validity must stay optional.

## Release posture

A draft profile may contain empty evidence files. A release-ready profile may
not rely on empty evidence, placeholder anchors, or unreviewed
`person-specific-candidate` claims.
