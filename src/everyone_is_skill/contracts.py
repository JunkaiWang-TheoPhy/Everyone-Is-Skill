"""Small dependency-free validators for generated profile artifacts."""

from __future__ import annotations

from collections.abc import Mapping


CLAIM_STATUSES = {
    "source-fact",
    "observed-pattern",
    "field-generic",
    "person-specific-candidate",
    "supported-method",
    "contradicted",
    "insufficient-evidence",
}

ATTRIBUTION_STRENGTHS = {"weak", "moderate", "strong"}
COAUTHOR_RISKS = {"unknown", "low", "moderate", "high"}
TARGET_TYPES = {"scientist", "expert", "creator", "team", "self", "colleague"}


def _missing(record: Mapping[str, object], required: set[str]) -> list[str]:
    return [f"missing required field: {key}" for key in sorted(required - set(record))]


def validate_claim(record: Mapping[str, object]) -> list[str]:
    """Return human-readable contract errors for one evidence claim."""

    required = {
        "claim_id",
        "subject",
        "facet",
        "claim",
        "status",
        "confidence",
        "source_ids",
        "attribution_strength",
        "coauthor_risk",
        "time_window",
    }
    errors = _missing(record, required)
    if errors:
        return errors

    status = record["status"]
    if status not in CLAIM_STATUSES:
        errors.append(f"status must be one of: {', '.join(sorted(CLAIM_STATUSES))}")

    confidence = record["confidence"]
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        errors.append("confidence must be between 0 and 1")

    sources = record["source_ids"]
    if not isinstance(sources, list) or not sources or not all(isinstance(item, str) and item for item in sources):
        errors.append("source_ids must contain at least one source")

    if record["attribution_strength"] not in ATTRIBUTION_STRENGTHS:
        errors.append(f"attribution_strength must be one of: {', '.join(sorted(ATTRIBUTION_STRENGTHS))}")
    if record["coauthor_risk"] not in COAUTHOR_RISKS:
        errors.append(f"coauthor_risk must be one of: {', '.join(sorted(COAUTHOR_RISKS))}")

    for key in ("claim_id", "subject", "facet", "claim", "time_window"):
        if not isinstance(record[key], str) or not record[key].strip():
            errors.append(f"{key} must be a non-empty string")
    return errors


def validate_profile_manifest(record: Mapping[str, object]) -> list[str]:
    """Return contract errors for the profile package manifest."""

    required = {
        "schema_version",
        "slug",
        "display_name",
        "target_type",
        "intended_use",
        "identity_anchors",
        "boundaries",
    }
    errors = _missing(record, required)
    if errors:
        return errors

    if record["target_type"] not in TARGET_TYPES:
        errors.append(f"target_type must be one of: {', '.join(sorted(TARGET_TYPES))}")
    anchors = record["identity_anchors"]
    if not isinstance(anchors, list) or not anchors:
        errors.append("identity_anchors must contain at least one anchor")
    elif not all(
        isinstance(anchor, Mapping)
        and isinstance(anchor.get("type"), str)
        and anchor.get("type", "").strip()
        and isinstance(anchor.get("value"), str)
        and anchor.get("value", "").strip()
        for anchor in anchors
    ):
        errors.append("identity_anchors entries must contain non-empty type and value")
    boundaries = record["boundaries"]
    if not isinstance(boundaries, list) or not boundaries:
        errors.append("boundaries must contain at least one boundary")
    elif not all(isinstance(boundary, str) and boundary.strip() for boundary in boundaries):
        errors.append("boundaries entries must be non-empty strings")
    return errors
