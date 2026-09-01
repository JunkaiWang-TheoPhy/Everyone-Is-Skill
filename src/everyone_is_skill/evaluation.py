"""Reproducible, provider-recorded profile evaluation runner."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


EVALUATION_SUITES = (
    "temporal-holdout",
    "matched-peers",
    "coauthor-leakage",
    "source-ablation",
    "transfer-tests",
    "boundary-tests",
    "prompt-injection",
)
RUBRIC_VERSION = "literal-signals-v1"


def _require_label(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(char in value for char in "\r\n"):
        raise ValueError(f"{name} must be a non-empty single line")
    return value.strip()


def _source_snapshot(profile_dir: Path) -> str:
    provenance = profile_dir / "provenance.yaml"
    if not provenance.is_file():
        return "unknown"
    for raw_line in provenance.read_text(encoding="utf-8").splitlines():
        key, separator, value = raw_line.partition(":")
        if separator and key.strip() == "source_snapshot":
            return value.strip().strip("'\"") or "unknown"
    return "unknown"


def _signals(case_id: str, key: str, value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"evaluation case {case_id} {key} must be an array of non-empty strings")
    return [item.strip() for item in value]


def _score_case(case: object) -> dict[str, object]:
    if not isinstance(case, dict):
        raise ValueError("evaluation cases must be objects")
    case_id = case.get("case_id", case.get("id"))
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("evaluation case needs a non-empty case_id")
    prompt = case.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(f"evaluation case {case_id} needs a non-empty prompt")
    candidate = case.get("candidate_output")
    if not isinstance(candidate, str):
        raise ValueError(f"evaluation case {case_id} needs candidate_output")
    expected = _signals(case_id, "expected", case.get("expected", []))
    forbidden = _signals(case_id, "forbidden", case.get("forbidden", []))
    forbidden_reasons = case.get("forbidden_reasons", {})
    if not isinstance(forbidden_reasons, dict) or not all(
        isinstance(signal, str) and isinstance(reason, str) and reason.strip()
        for signal, reason in forbidden_reasons.items()
    ):
        raise ValueError(f"evaluation case {case_id} forbidden_reasons must map strings to reason labels")
    if not expected and not forbidden:
        raise ValueError(f"evaluation case {case_id} needs expected or forbidden signals")
    minimum_score = case.get("minimum_score", 1.0)
    if (
        not isinstance(minimum_score, (int, float))
        or isinstance(minimum_score, bool)
        or not 0 <= minimum_score <= 1
    ):
        raise ValueError(f"evaluation case {case_id} minimum_score must be between 0 and 1")

    normalized = candidate.casefold()
    expected_hits = [signal for signal in expected if signal.casefold() in normalized]
    expected_misses = [signal for signal in expected if signal.casefold() not in normalized]
    forbidden_hits = [signal for signal in forbidden if signal.casefold() in normalized]
    total = len(expected) + len(forbidden)
    raw_score = (len(expected_hits) + len(forbidden) - len(forbidden_hits)) / total
    method_fidelity = len(expected_hits) / len(expected) if expected else 1.0
    identity_boundary = 1 - len(forbidden_hits) / len(forbidden) if forbidden else 1.0
    failure_reasons: list[str] = []
    if expected_misses:
        failure_reasons.append("missing-method-signal")
    for signal in forbidden_hits:
        reason = str(forbidden_reasons.get(signal, "forbidden-content"))
        if reason not in failure_reasons:
            failure_reasons.append(reason)
    verdict = "passed" if raw_score >= minimum_score and not forbidden_hits else "failed"
    return {
        **case,
        "case_id": case_id,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "raw_output_sha256": hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
        "expected_hits": expected_hits,
        "expected_misses": expected_misses,
        "forbidden_hits": forbidden_hits,
        "method_fidelity_score": round(method_fidelity, 6),
        "identity_boundary_score": round(identity_boundary, 6),
        "raw_score": round(raw_score, 6),
        "minimum_score": minimum_score,
        "failure_reasons": failure_reasons,
        "verdict": verdict,
    }


def _prepare_suite(
    path: Path,
    suite: str,
    *,
    provider: str,
    model: str,
    reviewer: str,
    executed_at: str,
    source_snapshot: str,
) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"missing evaluation suite: evals/{suite}.json")
    try:
        specification = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid evaluation JSON in evals/{suite}.json: {exc}") from exc
    if not isinstance(specification, dict) or not isinstance(specification.get("cases"), list):
        raise ValueError(f"evals/{suite}.json must contain a cases array")
    if not specification["cases"]:
        raise ValueError(f"evals/{suite}.json must contain at least one case")
    cases = [_score_case(case) for case in specification["cases"]]
    status = "passed" if all(case["verdict"] == "passed" for case in cases) else "failed"
    return {
        "schema_version": "1.0",
        "suite": suite,
        "status": status,
        "executed_at": executed_at,
        "provider": provider,
        "model": model,
        "reviewer": reviewer,
        "source_snapshot": source_snapshot,
        "rubric_version": RUBRIC_VERSION,
        "rubric": {
            "method_fidelity": "fraction of expected literal signals present",
            "identity_boundary": "fraction of forbidden literal signals absent",
            "verdict": "raw score meets minimum and no forbidden signal is present",
        },
        "cases": cases,
    }


def run_evaluations(
    profile_dir: Path,
    *,
    provider: str,
    model: str,
    reviewer: str,
    executed_at: str | None = None,
) -> dict[str, object]:
    """Score every required suite atomically from recorded candidate outputs."""

    profile_dir = Path(profile_dir)
    provider = _require_label("provider", provider)
    model = _require_label("model", model)
    reviewer = _require_label("reviewer", reviewer)
    timestamp = executed_at or datetime.now(UTC).isoformat()
    snapshot = _source_snapshot(profile_dir)
    prepared = {
        suite: _prepare_suite(
            profile_dir / "evals" / f"{suite}.json",
            suite,
            provider=provider,
            model=model,
            reviewer=reviewer,
            executed_at=timestamp,
            source_snapshot=snapshot,
        )
        for suite in EVALUATION_SUITES
    }
    for suite, result in prepared.items():
        (profile_dir / "evals" / f"{suite}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    status = "passed" if all(result["status"] == "passed" for result in prepared.values()) else "failed"
    return {
        "profile": str(profile_dir),
        "status": status,
        "executed_at": timestamp,
        "provider": provider,
        "model": model,
        "reviewer": reviewer,
        "source_snapshot": snapshot,
        "suites": {suite: result["status"] for suite, result in prepared.items()},
    }
