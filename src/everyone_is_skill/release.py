"""Structural validation and release-readiness gates for profile packages."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path

from .contracts import validate_claim, validate_profile_manifest


REQUIRED_PROFILE_FILES = {
    "SKILL.md",
    "manifest.json",
    "method.md",
    "work.md",
    "communication.md",
    "context.md",
    "counterevidence.md",
    "provenance.yaml",
    "evidence/claims.jsonl",
    "evidence/corpus-index.jsonl",
    "evidence/lineage.json",
    "evals/temporal-holdout.json",
    "evals/matched-peers.json",
    "evals/transfer-tests.json",
    "evals/boundary-tests.json",
}

REQUIRED_EVAL_FILES = (
    "temporal-holdout.json",
    "matched-peers.json",
    "transfer-tests.json",
    "boundary-tests.json",
)

RELEASE_EVAL_FILES = (
    "temporal-holdout.json",
    "matched-peers.json",
    "coauthor-leakage.json",
    "source-ablation.json",
    "transfer-tests.json",
    "boundary-tests.json",
    "prompt-injection.json",
)

RELEASE_READY_STATUS = "release-ready"
REVIEWED_IMPORT_TRUST = {"reviewed"}
SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
COUNTEREVIDENCE_PLACEHOLDERS = {
    "# counterevidence\n\nrecord exceptions, changes over time, and attribution conflicts.",
}


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> tuple[list[tuple[int, object]], list[str]]:
    records: list[tuple[int, object]] = []
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return records, [f"invalid JSON: {exc}"]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            records.append((line_number, json.loads(line)))
        except json.JSONDecodeError as exc:
            errors.append(f"{line_number}: invalid JSON: {exc}")
    return records, errors


def _load_flat_yaml(path: Path) -> tuple[dict[str, str], list[str]]:
    data: dict[str, str] = {}
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return data, [f"invalid YAML: {exc}"]

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in raw_line:
            errors.append(f"line {line_number}: expected key: value")
            continue
        key, value = raw_line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            errors.append(f"line {line_number}: missing key")
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        data[key] = value
    return data, errors


def _is_non_placeholder_anchor(anchor: object) -> bool:
    if not isinstance(anchor, Mapping):
        return False
    anchor_type = anchor.get("type")
    anchor_value = anchor.get("value")
    if not isinstance(anchor_type, str) or not isinstance(anchor_value, str):
        return False
    normalized_type = anchor_type.strip().lower()
    normalized_value = anchor_value.strip().lower()
    if not normalized_type or not normalized_value:
        return False
    compact_value = re.sub(r"[^a-z0-9]", "", normalized_value)
    if normalized_type == "placeholder":
        return False
    if (
        "replace-with-" in normalized_value
        or normalized_value in {"placeholder", "unknown", "todo", "tbd", "example", "0000"}
        or compact_value and set(compact_value) == {"0"}
    ):
        return False
    return True


def _anchor_is_placeholder(anchor: object) -> str | None:
    if not isinstance(anchor, Mapping):
        return None
    value = anchor.get("value")
    if isinstance(value, str) and value.strip() and not _is_non_placeholder_anchor(anchor):
        return value.strip()
    return None


def _counterevidence_is_placeholder(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in COUNTEREVIDENCE_PLACEHOLDERS


def validate_profile(profile_dir: Path) -> list[str]:
    errors: list[str] = []
    for relative in sorted(REQUIRED_PROFILE_FILES):
        if not (profile_dir / relative).is_file():
            errors.append(f"missing required file: {relative}")

    manifest_path = profile_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = _load_json(manifest_path)
            if not isinstance(manifest, Mapping):
                errors.append("manifest: must be a JSON object")
            else:
                errors.extend(f"manifest: {error}" for error in validate_profile_manifest(manifest))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"manifest: invalid JSON: {exc}")

    claims_path = profile_dir / "evidence" / "claims.jsonl"
    if claims_path.is_file():
        claims, load_errors = _load_jsonl(claims_path)
        errors.extend(f"claims:{error}" for error in load_errors)
        for line_number, claim in claims:
            if not isinstance(claim, Mapping):
                errors.append(f"claims:{line_number}: claim must be a JSON object")
                continue
            errors.extend(f"claims:{line_number}: {error}" for error in validate_claim(claim))

    corpus_path = profile_dir / "evidence" / "corpus-index.jsonl"
    if corpus_path.is_file():
        entries, load_errors = _load_jsonl(corpus_path)
        errors.extend(f"corpus:{error}" for error in load_errors)
        for line_number, entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"corpus:{line_number}: entry must be a JSON object")

    lineage_path = profile_dir / "evidence" / "lineage.json"
    if lineage_path.is_file():
        try:
            lineage = _load_json(lineage_path)
            if not isinstance(lineage, dict) or not isinstance(lineage.get("nodes"), list) or not isinstance(
                lineage.get("edges"), list
            ):
                errors.append("lineage: nodes and edges must be arrays")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"lineage: invalid JSON: {exc}")

    for filename in RELEASE_EVAL_FILES:
        eval_path = profile_dir / "evals" / filename
        if not eval_path.is_file():
            continue
        try:
            evaluation = _load_json(eval_path)
            if not isinstance(evaluation, dict) or not isinstance(evaluation.get("status"), str) or not isinstance(
                evaluation.get("cases"), list
            ):
                errors.append(f"evals/{filename}: status must be a string and cases must be an array")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"evals/{filename}: invalid JSON: {exc}")
    return errors


def check_release_readiness(profile_dir: Path) -> list[str]:
    errors = list(validate_profile(profile_dir))

    manifest: Mapping[str, object] | None = None
    manifest_path = profile_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            loaded_manifest = _load_json(manifest_path)
        except (json.JSONDecodeError, OSError):
            loaded_manifest = None
        if isinstance(loaded_manifest, Mapping):
            manifest = loaded_manifest

    if manifest is not None:
        if manifest.get("status") != RELEASE_READY_STATUS:
            errors.append("manifest.status must be release-ready")
        profile_version = manifest.get("profile_version")
        if not isinstance(profile_version, str) or not SEMVER_PATTERN.fullmatch(profile_version):
            errors.append("manifest.profile_version must be semantic versioning (for example 1.0.0)")
        anchors = manifest.get("identity_anchors")
        if isinstance(anchors, list):
            placeholders = [value for anchor in anchors if (value := _anchor_is_placeholder(anchor))]
            for value in placeholders:
                errors.append(f"manifest.identity_anchors contains a placeholder value: {value}")
        if not isinstance(anchors, list) or not any(_is_non_placeholder_anchor(anchor) for anchor in anchors):
            if not anchors:
                errors.append("manifest.identity_anchors must contain at least one non-placeholder anchor")
        imported_from = manifest.get("imported_from")
        if imported_from is not None:
            trust = imported_from.get("trust") if isinstance(imported_from, Mapping) else None
            if trust not in REVIEWED_IMPORT_TRUST:
                errors.append("manifest.imported_from.trust must be reviewed")

    source_ids: set[str] = set()
    corpus_path = profile_dir / "evidence" / "corpus-index.jsonl"
    if corpus_path.is_file():
        corpus, load_errors = _load_jsonl(corpus_path)
        if not load_errors:
            source_ids = {
                entry["source_id"]
                for _, entry in corpus
                if isinstance(entry, Mapping) and isinstance(entry.get("source_id"), str) and entry["source_id"]
            }

    claims_path = profile_dir / "evidence" / "claims.jsonl"
    strong_claim_present = False
    if claims_path.is_file():
        claims, load_errors = _load_jsonl(claims_path)
        if not load_errors and not claims:
            errors.append("evidence/claims.jsonl must contain at least one claim")
        for line_number, claim in claims:
            if not isinstance(claim, Mapping):
                continue
            claim_id = claim.get("claim_id") if isinstance(claim.get("claim_id"), str) else f"line-{line_number}"
            referenced_sources = claim.get("source_ids")
            if isinstance(referenced_sources, list):
                for source_id in sorted({item for item in referenced_sources if isinstance(item, str)} - source_ids):
                    errors.append(f"claim {claim_id} references unknown source_id: {source_id}")
            if claim.get("status") == "supported-method":
                if not isinstance(referenced_sources, list) or len(
                    {item for item in referenced_sources if isinstance(item, str) and item}
                ) < 2:
                    errors.append(f"supported-method claim {claim_id} requires at least two distinct source_ids")
            if claim.get("attribution_strength") == "strong":
                strong_claim_present = True
                if claim.get("coauthor_risk") in {"high", "unknown"}:
                    errors.append(f"strong claim {claim_id} cannot have coauthor_risk {claim.get('coauthor_risk')}")

    if strong_claim_present:
        counterevidence_path = profile_dir / "counterevidence.md"
        try:
            counterevidence = counterevidence_path.read_text(encoding="utf-8")
        except OSError:
            counterevidence = ""
        if not counterevidence.strip() or _counterevidence_is_placeholder(counterevidence):
            errors.append("counterevidence.md must be completed before releasing strong claims")

    evaluation_snapshots: set[str] = set()
    for filename in RELEASE_EVAL_FILES:
        eval_path = profile_dir / "evals" / filename
        if not eval_path.is_file():
            errors.append(f"missing release evaluation: evals/{filename}")
            continue
        try:
            evaluation = _load_json(eval_path)
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(evaluation, dict):
            continue
        if evaluation.get("status") != "passed":
            errors.append(f"evals/{filename} must have status passed")
        cases = evaluation.get("cases")
        if not isinstance(cases, list) or not cases:
            errors.append(f"evals/{filename} must contain at least one case")
            continue
        for field in ("executed_at", "provider", "model", "reviewer", "source_snapshot", "rubric_version"):
            if not isinstance(evaluation.get(field), str) or not evaluation[field].strip():
                errors.append(f"evals/{filename} missing execution field: {field}")
        snapshot = evaluation.get("source_snapshot")
        if isinstance(snapshot, str) and snapshot.strip():
            evaluation_snapshots.add(snapshot)
        for index, case in enumerate(cases, start=1):
            case_id = case.get("case_id", f"case-{index}") if isinstance(case, Mapping) else f"case-{index}"
            if not isinstance(case, Mapping) or case.get("verdict") != "passed":
                errors.append(f"evals/{filename} case {case_id} must have verdict passed")
            raw_score = case.get("raw_score") if isinstance(case, Mapping) else None
            minimum_score = case.get("minimum_score") if isinstance(case, Mapping) else None
            forbidden_hits = case.get("forbidden_hits") if isinstance(case, Mapping) else None
            raw_score_valid = isinstance(raw_score, (int, float)) and not isinstance(raw_score, bool)
            minimum_score_valid = isinstance(minimum_score, (int, float)) and not isinstance(minimum_score, bool)
            if not raw_score_valid:
                errors.append(f"evals/{filename} case {case_id} must record raw_score")
            if not minimum_score_valid:
                errors.append(f"evals/{filename} case {case_id} must record minimum_score")
            if not isinstance(forbidden_hits, list):
                errors.append(f"evals/{filename} case {case_id} must record forbidden_hits")
            elif forbidden_hits:
                errors.append(f"evals/{filename} case {case_id} contains forbidden hits")
            if (
                isinstance(case, Mapping)
                and case.get("verdict") == "passed"
                and (
                    raw_score_valid
                    and minimum_score_valid
                    and raw_score < minimum_score
                    or isinstance(forbidden_hits, list)
                    and bool(forbidden_hits)
                )
            ):
                errors.append(f"evals/{filename} case {case_id} passed verdict contradicts recorded score")
            prompt_sha256 = case.get("prompt_sha256") if isinstance(case, Mapping) else None
            if not isinstance(prompt_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", prompt_sha256):
                errors.append(f"evals/{filename} case {case_id} must record prompt_sha256")

    provenance_path = profile_dir / "provenance.yaml"
    if provenance_path.is_file():
        provenance, load_errors = _load_flat_yaml(provenance_path)
        errors.extend(f"provenance: {error}" for error in load_errors)
        if not provenance.get("schema_version"):
            errors.append("provenance.schema_version is required")
        if provenance.get("review_status") != "reviewed":
            errors.append("provenance.review_status must be reviewed")
        manifest_version = manifest.get("profile_version") if manifest is not None else None
        if provenance.get("profile_version") != manifest_version:
            errors.append("provenance.profile_version must match manifest.profile_version")
        provenance_snapshot = provenance.get("source_snapshot")
        if evaluation_snapshots and (
            not provenance_snapshot or evaluation_snapshots != {provenance_snapshot}
        ):
            errors.append("evaluation source_snapshot must match provenance.source_snapshot")

    return errors


release_check = check_release_readiness
