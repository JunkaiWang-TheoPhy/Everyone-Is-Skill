# Evaluation

Evaluation exists to answer one question: did we recover a bounded reusable
method, or did we merely produce a convincing style wrapper?

## Required evaluation surfaces

Repository templates include four evaluation files:

- `evals/temporal-holdout.json`
- `evals/matched-peers.json`
- `evals/transfer-tests.json`
- `evals/boundary-tests.json`

New drafts also include three release suites:

- `evals/coauthor-leakage.json`
- `evals/source-ablation.json`
- `evals/prompt-injection.json`

The current CLI requires all four files and validates their minimal `status`
and `cases` shape. Release practice applies the stronger semantics below.

## Evaluation goals

- Method fidelity: the profile uses supported operations rather than generic
  expert prose.
- Peer discrimination: close peers should produce detectably different outputs.
- Transfer usefulness: the method should help outside the original source
  domain when the abstraction is valid.
- Boundary honesty: the profile should abstain from unsupported identity or
  private-state claims.

## File intent

### `temporal-holdout.json`

Use this to test whether earlier evidence predicts later work or whether the
profile only memorized seen material.

Typical case shape:

- prompt or task
- held-out time window
- expected method signals
- disallowed shortcuts
- result notes

### `matched-peers.json`

Use this to compare near neighbors in the same field or function. The point is
not leaderboard scoring. The point is whether the profile preserves distinct
method signatures under similar prompts.

### `transfer-tests.json`

Use this to test the method on unfamiliar but structurally related problems.
Good transfer preserves the operative kernel while dropping identity theater.

### `boundary-tests.json`

Use this to force abstention, uncertainty labeling, and anti-impersonation
behavior. A profile fails if it invents private beliefs, hidden motives, or
unsupported person-specific claims under pressure.

## Status values

Templates start every evaluation file with:

```json
{
  "status": "not-run",
  "cases": []
}
```

During drafting, values such as `specified`, `in-progress`, `passed`, `failed`,
or `mixed` remain useful. Structural validation only checks their shape.
`release-check` is stricter: every required file must use `status: "passed"`
and contain at least one case.

## Minimal scoring guidance

Evaluation results should distinguish at least four failure modes:

- generic expert answer with no subject-specific method
- persona imitation without evidence
- collaborator leakage or field-generic attribution
- brittle transfer that works only on near-copy tasks

## Release threshold

A profile should not be treated as release-ready when:

- all four evaluation files remain `not-run`,
- matched peers are not distinguishable,
- transfer works only by style imitation,
- or boundary tests show identity overclaiming.

The executable gate is `everyone-skill release-check PROFILE`. Its current
minimum is intentionally mechanical; a `passed` value must describe an
actually executed case and is still subject to review. The evaluation runner
records the execution evidence used to justify that value.

## Executable runner

`everyone-skill run-evals PROFILE --provider NAME --model VERSION --reviewer ID`
executes all seven suites from recorded `candidate_output` fields. A case
declares literal `expected` and `forbidden` signals plus an optional
`minimum_score`. `forbidden_reasons` can map each prohibited signal to a
specific failure label. This keeps generic answers (`missing-method-signal`),
identity theater (`identity-boundary-violation`), and followed source
instructions (`prompt-injection-followed`) distinguishable. The runner records:

- provider and exact model label;
- execution time and source snapshot;
- rubric version and prompt digest;
- method-fidelity and identity-boundary component scores;
- raw score, failure reasons, and verdict; and
- the reviewer identity supplied for the run.

All suites are parsed and scored before any file is overwritten. Invalid or
partial specifications therefore fail atomically. This deterministic literal
rubric is a reproducible baseline, not a substitute for scientific peer
review. Model-backed or human-scored providers can be added behind the same
result contract.

`release-check` checks internal result consistency as well as the presence of
metadata: a passed verdict cannot have a score below its minimum or retain any
forbidden hits.
