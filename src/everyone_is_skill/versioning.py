"""Append-only profile updates with recoverable snapshots and rollback."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from .contracts import validate_claim
from .evaluation import EVALUATION_SUITES
from .release import REQUIRED_PROFILE_FILES, validate_profile


SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
SNAPSHOT_ID = re.compile(r"^[A-Za-z0-9._-]+$")
SOURCE_REQUIRED = {"source_id", "source_type", "title", "authors", "published_at", "url", "access", "rights_basis"}
OPTIONAL_SNAPSHOT_FILES = {"peer-review.md"}


def _timestamp(value: str | None) -> str:
    return value or datetime.now(UTC).isoformat()


def _version(manifest: Mapping[str, object]) -> str:
    value = manifest.get("profile_version", "0.1.0")
    if not isinstance(value, str) or not SEMVER.fullmatch(value):
        raise ValueError("manifest.profile_version must use simple semantic versioning before updates")
    return value


def _bump_patch(version: str) -> str:
    match = SEMVER.fullmatch(version)
    if match is None:
        raise ValueError("profile version must use MAJOR.MINOR.PATCH")
    return f"{match.group(1)}.{match.group(2)}.{int(match.group(3)) + 1}"


def _snapshot_files(profile_dir: Path) -> list[str]:
    files = sorted(REQUIRED_PROFILE_FILES)
    files.extend(relative for relative in sorted(OPTIONAL_SNAPSHOT_FILES) if (profile_dir / relative).is_file())
    return files


def _hash_files(profile_dir: Path, files: list[str]) -> tuple[str, dict[str, str]]:
    file_hashes: dict[str, str] = {}
    combined = hashlib.sha256()
    for relative in files:
        path = profile_dir / relative
        if path.is_symlink():
            raise ValueError(f"profile snapshots do not follow symbolic links: {relative}")
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        file_hashes[relative] = digest
        combined.update(relative.encode("utf-8") + b"\0" + bytes.fromhex(digest))
    return combined.hexdigest(), file_hashes


def compute_source_snapshot(profile_dir: Path) -> str:
    digest = hashlib.sha256()
    for relative in ("evidence/corpus-index.jsonl", "evidence/claims.jsonl", "evidence/lineage.json"):
        payload = (profile_dir / relative).read_bytes()
        digest.update(relative.encode("utf-8") + b"\0" + payload)
    return digest.hexdigest()


def snapshot_profile(profile_dir: Path, *, reason: str, created_at: str | None = None) -> dict[str, object]:
    profile_dir = Path(profile_dir)
    if profile_dir.is_symlink():
        raise ValueError("profile directory cannot be a symbolic link")
    history_root = profile_dir / "history"
    if history_root.is_symlink():
        raise ValueError("history directory cannot be a symbolic link")
    errors = validate_profile(profile_dir)
    if errors:
        raise ValueError(f"cannot snapshot invalid profile: {'; '.join(errors)}")
    if not isinstance(reason, str) or not reason.strip() or any(char in reason for char in "\r\n"):
        raise ValueError("snapshot reason must be a non-empty single line")
    manifest = json.loads((profile_dir / "manifest.json").read_text(encoding="utf-8"))
    version = _version(manifest)
    files = _snapshot_files(profile_dir)
    digest, file_hashes = _hash_files(profile_dir, files)
    timestamp = _timestamp(created_at)
    compact_time = re.sub(r"[^0-9]", "", timestamp)[:14] or "undated"
    snapshot_id = f"{compact_time}-v{version}-{digest[:12]}"
    destination = history_root / snapshot_id
    if destination.exists():
        raise FileExistsError(f"snapshot already exists: {snapshot_id}")
    for relative in files:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(profile_dir / relative, target)
    metadata = {
        "schema_version": "1.0",
        "snapshot_id": snapshot_id,
        "created_at": timestamp,
        "reason": reason.strip(),
        "profile_version": version,
        "profile_digest": digest,
        "files": file_hashes,
    }
    (destination / "snapshot.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return metadata


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _validate_source(source: object) -> dict[str, object]:
    if not isinstance(source, dict):
        raise ValueError("source must be a JSON object")
    missing = SOURCE_REQUIRED - set(source)
    if missing:
        raise ValueError(f"source is missing fields: {', '.join(sorted(missing))}")
    if not isinstance(source["source_id"], str) or not source["source_id"].strip():
        raise ValueError("source_id must be a non-empty string")
    if not isinstance(source["url"], str) or not source["url"].startswith("https://"):
        raise ValueError("source url must use HTTPS")
    if not isinstance(source["authors"], list) or not all(isinstance(author, str) and author for author in source["authors"]):
        raise ValueError("source authors must be an array of non-empty strings")
    return source


def _append_history(profile_dir: Path, event: dict[str, object]) -> None:
    with (profile_dir / "history.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def update_profile_claim(
    profile_dir: Path,
    *,
    source: object,
    claim: object,
    reason: str,
    updated_at: str | None = None,
) -> dict[str, object]:
    """Append one source-backed claim after snapshotting and invalidating review."""

    profile_dir = Path(profile_dir)
    normalized_source = _validate_source(source)
    if not isinstance(claim, dict):
        raise ValueError("claim must be a JSON object")
    claim_errors = validate_claim(claim)
    if claim_errors:
        raise ValueError(f"invalid claim: {'; '.join(claim_errors)}")
    manifest_path = profile_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if claim["subject"] != manifest["slug"]:
        raise ValueError("claim subject must match manifest slug")
    sources = _read_jsonl(profile_dir / "evidence" / "corpus-index.jsonl")
    claims = _read_jsonl(profile_dir / "evidence" / "claims.jsonl")
    if normalized_source["source_id"] in {item.get("source_id") for item in sources}:
        raise ValueError(f"duplicate source_id: {normalized_source['source_id']}")
    if claim["claim_id"] in {item.get("claim_id") for item in claims}:
        raise ValueError(f"duplicate claim_id: {claim['claim_id']}")
    known_sources = {item.get("source_id") for item in sources} | {normalized_source["source_id"]}
    unknown_sources = set(claim["source_ids"]) - known_sources
    if unknown_sources:
        raise ValueError(f"claim references unknown sources: {', '.join(sorted(unknown_sources))}")

    timestamp = _timestamp(updated_at)
    snapshot = snapshot_profile(profile_dir, reason=reason, created_at=timestamp)
    previous_version = _version(manifest)
    next_version = _bump_patch(previous_version)
    with (profile_dir / "evidence" / "corpus-index.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(normalized_source, ensure_ascii=False, sort_keys=True) + "\n")
    with (profile_dir / "evidence" / "claims.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(claim, ensure_ascii=False, sort_keys=True) + "\n")

    lineage_path = profile_dir / "evidence" / "lineage.json"
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    lineage_node_ids = {node.get("id") for node in lineage["nodes"] if isinstance(node, dict)}
    if manifest["slug"] not in lineage_node_ids:
        lineage["nodes"].append(
            {
                "id": manifest["slug"],
                "label": manifest["display_name"],
                "kind": "team" if manifest["target_type"] == "team" else "person",
            }
        )
    lineage["nodes"].append(
        {
            "id": normalized_source["source_id"],
            "label": normalized_source["title"],
            "kind": "source",
        }
    )
    lineage["edges"].append(
        {
            "source": normalized_source["source_id"],
            "target": manifest["slug"],
            "relation": "evidence-reviewed-for",
        }
    )
    lineage_path.write_text(json.dumps(lineage, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest["profile_version"] = next_version
    manifest["status"] = "evidence-complete"
    manifest.pop("peer_review", None)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    peer_review_path = profile_dir / "peer-review.md"
    if peer_review_path.is_file():
        peer_review_path.unlink()
    for suite in EVALUATION_SUITES:
        (profile_dir / "evals" / f"{suite}.json").write_text(
            json.dumps(
                {"status": "not-run", "cases": [], "invalidated_at": timestamp, "invalidated_reason": reason},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    snapshot_digest = compute_source_snapshot(profile_dir)
    (profile_dir / "provenance.yaml").write_text(
        "schema_version: '1.0'\n"
        f"profile_version: '{next_version}'\n"
        f"source_snapshot: '{snapshot_digest}'\n"
        "review_status: unreviewed\n"
        f"updated_at: '{timestamp}'\n",
        encoding="utf-8",
    )
    event = {
        "action": "update-claim",
        "at": timestamp,
        "reason": reason,
        "snapshot_id": snapshot["snapshot_id"],
        "previous_version": previous_version,
        "profile_version": next_version,
        "source_id": normalized_source["source_id"],
        "claim_id": claim["claim_id"],
    }
    _append_history(profile_dir, event)
    return event


def rollback_profile(
    profile_dir: Path,
    snapshot_id: str,
    *,
    reason: str,
    rolled_back_at: str | None = None,
) -> dict[str, object]:
    """Restore an exact snapshot after first preserving the current state."""

    profile_dir = Path(profile_dir)
    if not SNAPSHOT_ID.fullmatch(snapshot_id):
        raise ValueError("invalid snapshot id")
    source = profile_dir / "history" / snapshot_id
    if not (source / "snapshot.json").is_file() or source.is_symlink():
        raise FileNotFoundError(f"snapshot does not exist: {snapshot_id}")
    timestamp = _timestamp(rolled_back_at)
    metadata = json.loads((source / "snapshot.json").read_text(encoding="utf-8"))
    approved_files = REQUIRED_PROFILE_FILES | OPTIONAL_SNAPSHOT_FILES
    if not isinstance(metadata.get("files"), dict):
        raise ValueError("snapshot file manifest must be an object")
    for relative, digest in metadata["files"].items():
        if relative not in approved_files:
            raise ValueError(f"unapproved snapshot file path: {relative}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"invalid snapshot digest for: {relative}")
    safety = snapshot_profile(profile_dir, reason=f"pre-rollback: {reason}", created_at=timestamp)
    for relative in OPTIONAL_SNAPSHOT_FILES - set(metadata["files"]):
        stale = profile_dir / relative
        if stale.is_file():
            stale.unlink()
    for relative in metadata["files"]:
        origin = source / relative
        if origin.is_symlink():
            raise ValueError(f"snapshot contains a symbolic link: {relative}")
        if hashlib.sha256(origin.read_bytes()).hexdigest() != metadata["files"][relative]:
            raise ValueError(f"snapshot file digest mismatch: {relative}")
        target = profile_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
    event = {
        "action": "rollback",
        "at": timestamp,
        "reason": reason,
        "restored_snapshot_id": snapshot_id,
        "safety_snapshot_id": safety["snapshot_id"],
        "profile_version": metadata["profile_version"],
    }
    _append_history(profile_dir, event)
    return event


def diff_profile(profile_dir: Path, snapshot_id: str) -> dict[str, object]:
    """Compare current profile artifacts with one immutable snapshot."""

    profile_dir = Path(profile_dir)
    if not SNAPSHOT_ID.fullmatch(snapshot_id):
        raise ValueError("invalid snapshot id")
    snapshot_path = profile_dir / "history" / snapshot_id / "snapshot.json"
    if not snapshot_path.is_file():
        raise FileNotFoundError(f"snapshot does not exist: {snapshot_id}")
    metadata = json.loads(snapshot_path.read_text(encoding="utf-8"))
    previous = metadata["files"]
    current_files = _snapshot_files(profile_dir)
    _, current = _hash_files(profile_dir, current_files)
    return {
        "snapshot_id": snapshot_id,
        "profile_version": json.loads((profile_dir / "manifest.json").read_text(encoding="utf-8")).get(
            "profile_version"
        ),
        "snapshot_version": metadata["profile_version"],
        "added": sorted(set(current) - set(previous)),
        "removed": sorted(set(previous) - set(current)),
        "changed": sorted(relative for relative in set(previous) & set(current) if previous[relative] != current[relative]),
        "unchanged": sorted(relative for relative in set(previous) & set(current) if previous[relative] == current[relative]),
    }
