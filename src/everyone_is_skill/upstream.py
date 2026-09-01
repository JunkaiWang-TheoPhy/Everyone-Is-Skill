"""Safe, data-only import adapters for reviewed upstream artifact layouts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse


UPSTREAM_FORMATS = (
    "distill-everything",
    "anything2skill",
    "sci-brain",
    "research-taste-distillation",
    "nuwa-skill",
    "distilly",
    "scientific-agents",
    "scientific-agent-skills",
    "virtual-scientists",
    "omniscientist-v2",
)
CANONICAL_UPSTREAMS = {
    "distill-everything": "https://github.com/AITCX08/Distill-Everything",
    "anything2skill": "https://github.com/Nouischen/anything2skill",
    "sci-brain": "https://github.com/QuantumBFS/sci-brain",
    "research-taste-distillation": "https://github.com/Jingqi-Xu/research-taste-distillation",
    "nuwa-skill": "https://github.com/alchaincyf/nuwa-skill",
    "distilly": "https://github.com/titanwings/distilly",
    "scientific-agents": "https://github.com/K-Dense-AI/scientific-agents",
    "scientific-agent-skills": "https://github.com/K-Dense-AI/scientific-agent-skills",
    "virtual-scientists": "https://github.com/InternScience/Virtual-Scientists",
    "omniscientist-v2": "https://github.com/tsinghua-fib-lab/OmniScientist-V2",
}
CANONICAL_LICENSES = {
    **{name: "MIT" for name in UPSTREAM_FORMATS if name not in {"virtual-scientists", "omniscientist-v2"}},
    "virtual-scientists": "Apache-2.0",
    "omniscientist-v2": "Apache-2.0",
}
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
MAX_IMPORT_BYTES = 10 * 1024 * 1024


def _accepted(format_name: str, relative: str) -> bool:
    path = Path(relative)
    name = path.name
    suffix = path.suffix.lower()
    parts = path.parts
    if format_name == "distill-everything":
        return (parts and parts[0] == "episodes" and suffix == ".md") or (
            parts and parts[0] == "rag" and suffix == ".json"
        )
    if format_name == "anything2skill":
        return parts and parts[0] == "output" and suffix == ".json"
    if format_name == "sci-brain":
        return parts and parts[0] in {"knowledge", "reports"} and suffix in {".md", ".json"}
    if format_name == "research-taste-distillation":
        return parts and parts[0] == "examples" and suffix == ".md"
    if format_name == "nuwa-skill":
        return parts and parts[0] in {"profiles", "examples"} and suffix in {".md", ".json"}
    if format_name == "distilly":
        return name in {
            "work.md",
            "persona.md",
            "work_skill.md",
            "persona_skill.md",
            "manifest.json",
            "meta.json",
        }
    if format_name == "scientific-agents":
        return name == "catalog.json"
    if format_name == "scientific-agent-skills":
        return "references" in parts and suffix == ".md"
    if format_name == "virtual-scientists":
        return name == "provenance.json"
    if format_name == "omniscientist-v2":
        return name == "provenance.json"
    return False


def _candidate_files(root: Path) -> list[tuple[Path, str]]:
    if not root.exists():
        raise FileNotFoundError(f"upstream artifact path does not exist: {root}")
    if root.is_symlink():
        raise ValueError(f"symbolic links are not allowed as upstream inputs: {root}")
    if root.is_file():
        return [(root, root.name)]
    candidates: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symbolic links are not allowed inside upstream artifacts: {path}")
        if path.is_file():
            candidates.append((path, path.relative_to(root).as_posix()))
    return candidates


def _validate_metadata(format_name: str, upstream_url: str, upstream_license: str) -> None:
    if format_name not in UPSTREAM_FORMATS:
        raise ValueError(f"unknown upstream format: {format_name}")
    parsed = urlparse(upstream_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("upstream_url must be an HTTPS URL")
    normalized_url = upstream_url.rstrip("/")
    if normalized_url.endswith(".git"):
        normalized_url = normalized_url[:-4]
    if normalized_url.casefold() != CANONICAL_UPSTREAMS[format_name].casefold():
        raise ValueError(f"upstream_url must match the canonical upstream URL for {format_name}")
    if not upstream_license.strip() or upstream_license.strip().lower() in {
        "unknown",
        "unresolved",
        "none",
        "not-declared",
        "not_declared",
    }:
        raise ValueError("a reviewed upstream license is required before import")
    if upstream_license.strip().casefold() != CANONICAL_LICENSES[format_name].casefold():
        raise ValueError(f"upstream license must match the reviewed license for {format_name}")


def import_upstream_artifacts(
    root: Path,
    *,
    format_name: str,
    upstream_url: str,
    upstream_license: str,
    access: str = "authorized",
) -> list[dict[str, object]]:
    """Map reviewed Markdown/JSON outputs to quarantined records; never import code."""

    _validate_metadata(format_name, upstream_url, upstream_license)
    if access not in {"public", "authorized", "private-reference"}:
        raise ValueError("upstream access must be public, authorized, or private-reference")
    records: list[dict[str, object]] = []
    total_size = 0
    for path, relative in _candidate_files(Path(root)):
        if not _accepted(format_name, relative):
            continue
        payload = path.read_bytes()
        if len(payload) > MAX_ARTIFACT_BYTES:
            raise ValueError(f"upstream artifact exceeds the 2 MiB limit: {relative}")
        total_size += len(payload)
        if total_size > MAX_IMPORT_BYTES:
            raise ValueError("upstream import exceeds the 10 MiB total limit")
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError(f"upstream artifact must be UTF-8 text: {relative}") from exc
        if path.suffix.lower() == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid upstream JSON in {relative}: {exc}") from exc
        digest = hashlib.sha256(
            b"\0".join(
                [
                    format_name.encode("utf-8"),
                    upstream_url.encode("utf-8"),
                    relative.encode("utf-8"),
                    payload,
                ]
            )
        ).hexdigest()
        records.append(
            {
                "source_id": f"upstream-{digest[:16]}",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "title": relative,
                "source_type": "notes",
                "text": text,
                "source_locator": relative,
                "path": relative,
                "url": upstream_url,
                "access": access,
                "rights_basis": (
                    f"user-declared-{access}; layout mapped from upstream {upstream_license}; "
                    "artifact content rights remain separate"
                ),
                "upstream_format": format_name,
                "upstream_url": upstream_url,
                "upstream_license": upstream_license,
                "instruction_quarantine": True,
                "executable_content_imported": False,
            }
        )
    if not records:
        raise ValueError(f"no recognized {format_name} artifacts were found")
    return records


def write_upstream_jsonl(path: Path, records: list[dict[str, object]]) -> Path:
    path = Path(path)
    if path.is_symlink():
        raise ValueError("upstream output cannot be a symbolic link")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    return path
