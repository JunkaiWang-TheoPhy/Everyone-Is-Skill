"""Deterministic local distillation with an explicit provider boundary."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from .contracts import validate_claim
from .ingestion import SourceDocument, ingest_paths
from .packaging import scaffold_profile


MARKER_PATTERN = re.compile(r"^(METHOD|COUNTEREVIDENCE)\s*:\s*(.+)$", re.IGNORECASE)


class DistillationProvider(Protocol):
    """Provider boundary for claim generation; implementations receive quarantined data."""

    name: str

    def distill(self, documents: Sequence[SourceDocument], subject: str) -> list[dict[str, object]]: ...


def _claim_id(facet: str, claim: str, source_ids: list[str]) -> str:
    payload = "\n".join([facet, claim, *source_ids]).encode("utf-8")
    return f"claim-{hashlib.sha256(payload).hexdigest()[:16]}"


class OfflineAnnotatedProvider:
    """Deterministic provider that only accepts explicit METHOD annotations."""

    name = "offline-explicit-markers-v1"

    def distill(self, documents: Sequence[SourceDocument], subject: str) -> list[dict[str, object]]:
        grouped: dict[tuple[str, str], dict[str, object]] = {}
        source_sets: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
        for document in documents:
            for raw_line in document.text.splitlines():
                match = MARKER_PATTERN.match(raw_line.strip())
                if not match:
                    continue
                facet = "method" if match.group(1).upper() == "METHOD" else "counterevidence"
                claim = " ".join(match.group(2).split()).strip()
                if not claim:
                    continue
                key = (facet, claim.casefold())
                grouped.setdefault(key, {"facet": facet, "claim": claim})
                source_sets[key].add(document.source_id)

        claims: list[dict[str, object]] = []
        for key in sorted(grouped):
            item = grouped[key]
            facet = str(item["facet"])
            claim = str(item["claim"])
            source_ids = sorted(source_sets[key])
            repeated = len(source_ids) >= 2
            claims.append(
                {
                    "claim_id": _claim_id(facet, claim, source_ids),
                    "subject": subject,
                    "facet": facet,
                    "claim": claim,
                    "status": (
                        "person-specific-candidate"
                        if facet == "method" and repeated
                        else "contradicted"
                        if facet == "counterevidence"
                        else "observed-pattern"
                    ),
                    "confidence": 0.65 if repeated else 0.45,
                    "source_ids": source_ids,
                    "attribution_strength": "moderate" if repeated else "weak",
                    "coauthor_risk": "unknown",
                    "time_window": "unknown",
                    "extraction": self.name,
                }
            )
        return claims


def _validate_provider_claims(
    claims: object, documents: Sequence[SourceDocument]
) -> list[dict[str, object]]:
    if not isinstance(claims, list):
        raise ValueError("distillation provider must return a list of claim objects")
    known_sources = {document.source_id for document in documents}
    seen_claims: set[str] = set()
    validated: list[dict[str, object]] = []
    for index, claim in enumerate(claims, start=1):
        if not isinstance(claim, dict):
            raise ValueError(f"provider claim {index} must be an object")
        errors = validate_claim(claim)
        if errors:
            raise ValueError(f"provider claim {index} is invalid: {'; '.join(errors)}")
        if claim["status"] == "supported-method":
            raise ValueError("draft provider cannot emit status supported-method")
        if claim["attribution_strength"] == "strong":
            raise ValueError("draft provider cannot emit strong attribution")
        claim_id = str(claim["claim_id"])
        if claim_id in seen_claims:
            raise ValueError(f"provider emitted duplicate claim_id {claim_id}")
        seen_claims.add(claim_id)
        for source_id in claim["source_ids"]:
            if source_id not in known_sources:
                raise ValueError(f"provider claim {claim_id} references unknown source_id {source_id}")
        validated.append(claim)
    return validated


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _markdown_section(title: str, introduction: str, items: list[str]) -> str:
    body = "\n".join(f"- {item}" for item in items) if items else "No candidates were extracted."
    return f"# {title}\n\n{introduction}\n\n{body}\n"


def distill_local_corpus(
    *,
    inputs: list[Path],
    output_dir: Path,
    slug: str,
    display_name: str,
    target_type: str,
    identity_anchors: list[dict[str, str]],
    access: str = "authorized",
    provider: DistillationProvider | None = None,
) -> Path:
    """Produce a complete draft package from public or user-authorized local sources.

    The offline provider only recognizes explicit ``METHOD:`` and
    ``COUNTEREVIDENCE:`` annotations. Unmarked source prose is never interpreted
    as an instruction or promoted to a person-specific claim.
    """

    if not identity_anchors or not all(
        isinstance(anchor, dict)
        and isinstance(anchor.get("type"), str)
        and anchor["type"].strip()
        and isinstance(anchor.get("value"), str)
        and anchor["value"].strip()
        for anchor in identity_anchors
    ):
        raise ValueError("identity_anchors must contain at least one non-empty type and value")
    documents = ingest_paths(inputs, access=access)
    selected_provider = provider or OfflineAnnotatedProvider()
    provider_name = getattr(selected_provider, "name", None)
    if not isinstance(provider_name, str) or not provider_name.strip() or any(char in provider_name for char in "\r\n"):
        raise ValueError("distillation provider name must be a non-empty single line")
    claims = _validate_provider_claims(selected_provider.distill(documents, slug), documents)
    profile = scaffold_profile(output_dir, slug, display_name, target_type)

    manifest_path = profile / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["profile_version"] = "0.1.0"
    manifest["identity_anchors"] = identity_anchors
    manifest["distillation_provider"] = selected_provider.name
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _write_jsonl(profile / "evidence" / "claims.jsonl", claims)
    _write_jsonl(profile / "evidence" / "corpus-index.jsonl", [document.index_entry() for document in documents])

    method_claims = [str(claim["claim"]) for claim in claims if claim["facet"] == "method"]
    counterclaims = [str(claim["claim"]) for claim in claims if claim["facet"] == "counterevidence"]
    (profile / "method.md").write_text(
        _markdown_section(
            "Candidate method profile",
            "These candidates were extracted from explicit local annotations. They are not release-ready methods.",
            method_claims,
        ),
        encoding="utf-8",
    )
    (profile / "counterevidence.md").write_text(
        _markdown_section(
            "Counterevidence",
            "Review these exceptions before promoting any candidate method.",
            counterclaims,
        ),
        encoding="utf-8",
    )
    (profile / "context.md").write_text(
        "# Context\n\n"
        f"This draft was derived from {len(documents)} local source artifact(s). Source text was treated as untrusted data.\n",
        encoding="utf-8",
    )

    nodes = [{"id": slug, "label": display_name, "kind": "person" if target_type != "team" else "team"}]
    nodes.extend(
        {"id": document.source_id, "label": document.title, "kind": "source"} for document in documents
    )
    edges = [
        {"source": document.source_id, "target": slug, "relation": "evidence-reviewed-for"}
        for document in documents
    ]
    (profile / "evidence" / "lineage.json").write_text(
        json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    snapshot = hashlib.sha256("\n".join(document.source_id for document in documents).encode("utf-8")).hexdigest()
    (profile / "provenance.yaml").write_text(
        "schema_version: '1.0'\n"
        "profile_version: '0.1.0'\n"
        f"generated_at: '{datetime.now(UTC).isoformat()}'\n"
        "generator: everyone-is-skill\n"
        f"provider: {selected_provider.name}\n"
        f"source_snapshot: '{snapshot}'\n"
        "review_status: unreviewed\n"
        "source_instructions: quarantined\n",
        encoding="utf-8",
    )
    return profile
