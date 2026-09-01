"""Create transparent, inspectable profile package scaffolds."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from .contracts import TARGET_TYPES


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _require_single_line(label: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip() or any(char in value for char in "\r\n"):
        raise ValueError(f"{label} must be a non-empty single line")


def scaffold_profile(output_dir: Path, slug: str, display_name: str, target_type: str) -> Path:
    """Create a draft profile package without source text or unsupported claims."""

    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError("slug must use lowercase hyphen-case")
    _require_single_line("display_name", display_name)
    if target_type not in TARGET_TYPES:
        raise ValueError(f"target_type must be one of: {', '.join(sorted(TARGET_TYPES))}")

    profile_dir = Path(output_dir) / slug
    if profile_dir.exists() and any(profile_dir.iterdir()):
        raise FileExistsError(f"profile directory is not empty: {profile_dir}")
    profile_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": "1.0",
        "slug": slug,
        "display_name": display_name,
        "target_type": target_type,
        "status": "draft",
        "intended_use": "Evidence-grounded reconstruction of bounded, reusable methods.",
        "identity_anchors": [],
        "boundaries": [
            "This profile is not an impersonation or a source of private mental states.",
            "Unsupported person-specific claims must be omitted or labeled insufficient-evidence.",
        ],
    }
    _write(profile_dir / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    _write(
        profile_dir / "SKILL.md",
        "\n".join(
            [
                "---",
                f"name: {slug}",
                f"description: Use when applying the evidence-grounded methods attributed to {display_name} within the supported scope of this profile.",
                "---",
                "",
                f"# {display_name}",
                "",
                "Use the method profile and evidence ledger as bounded guidance. This is not an impersonation.",
                "",
                "Read `method.md` for supported operations, `counterevidence.md` before strong attribution, and `manifest.json` for boundaries.",
                "",
            ]
        ),
    )
    _write(profile_dir / "method.md", "# Method profile\n\nNo supported methods have been distilled yet.\n")
    _write(profile_dir / "work.md", "# Work practices\n\nNo supported practices have been distilled yet.\n")
    _write(
        profile_dir / "communication.md",
        "# Communication\n\nCommunication guidance is optional and must not imitate signature phrases or claim to be the person.\n",
    )
    _write(profile_dir / "context.md", "# Context\n\nAdd dated intellectual, collaboration, and field context with sources.\n")
    _write(profile_dir / "counterevidence.md", "# Counterevidence\n\nRecord exceptions, changes over time, and attribution conflicts.\n")
    _write(
        profile_dir / "provenance.yaml",
        f"schema_version: '1.0'\ngenerated_at: '{datetime.now(UTC).isoformat()}'\ngenerator: everyone-is-skill\n",
    )
    _write(profile_dir / "evidence" / "claims.jsonl", "")
    _write(profile_dir / "evidence" / "corpus-index.jsonl", "")
    _write(profile_dir / "evidence" / "lineage.json", "{\n  \"nodes\": [],\n  \"edges\": []\n}\n")
    for filename in (
        "temporal-holdout.json",
        "matched-peers.json",
        "transfer-tests.json",
        "boundary-tests.json",
    ):
        _write(profile_dir / "evals" / filename, "{\n  \"status\": \"not-run\",\n  \"cases\": []\n}\n")
    return profile_dir


def scaffold_import_reference(
    output_dir: Path,
    slug: str,
    display_name: str,
    target_type: str,
    upstream_url: str,
    upstream_license: str,
) -> Path:
    """Create a local draft that references, but does not copy, an upstream profile."""

    _require_single_line("upstream_url", upstream_url)
    _require_single_line("upstream_license", upstream_license)
    if not upstream_url.startswith(("https://", "http://")):
        raise ValueError("upstream_url must be an HTTP(S) URL")
    profile_dir = scaffold_profile(output_dir, slug, display_name, target_type)
    manifest_path = profile_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["identity_anchors"] = [{"type": "upstream-profile", "value": upstream_url}]
    manifest["imported_from"] = {
        "url": upstream_url,
        "license": upstream_license,
        "content_bundled": False,
        "trust": "unreviewed",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write(
        profile_dir / "context.md",
        "# Context\n\n"
        f"Imported as a reference to `{upstream_url}` under the declared `{upstream_license}` license. "
        "No upstream profile text or code was copied. Re-evaluate every claim under the local evidence policy.\n",
    )
    _write(
        profile_dir / "provenance.yaml",
        f"schema_version: '1.0'\ngenerated_at: '{datetime.now(UTC).isoformat()}'\n"
        "generator: everyone-is-skill\n"
        f"upstream_url: {json.dumps(upstream_url, ensure_ascii=False)}\n"
        f"upstream_license: {json.dumps(upstream_license, ensure_ascii=False)}\n"
        "upstream_content_bundled: false\nreview_status: unreviewed\n",
    )
    return profile_dir
