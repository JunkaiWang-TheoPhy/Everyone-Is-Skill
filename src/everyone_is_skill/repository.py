"""Repository-wide structural checks without third-party dependencies."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .cli import validate_profile


REQUIRED_ROOT_FILES = {
    "LICENSE",
    "NOTICE",
    "THIRD_PARTY_NOTICES.md",
    "ACKNOWLEDGEMENTS.md",
    "CITATION.cff",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "CHANGELOG.md",
    "README.md",
    "README.zh.md",
}

REQUIRED_DOCS = {
    "architecture.md",
    "evidence-policy.md",
    "profile-contract.md",
    "evaluation.md",
    "integrations.md",
    "versioning.md",
}

REQUIRED_SCHEMAS = {
    "claim.schema.json",
    "corpus-entry.schema.json",
    "profile.schema.json",
    "lineage.schema.json",
    "eval-result.schema.json",
}

REQUIRED_PLUGIN_SKILLS = {
    "everyone-is-skill",
    "distill-scientist",
    "distill-person",
    "distill-team",
    "distill-content",
    "evaluate-profile",
    "update-profile",
    "import-profile",
}

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def _frontmatter_value(lines: list[str], key: str) -> str | None:
    prefix = f"{key}:"
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix) :].strip().strip('"\'')
    return None


def validate_skill_directory(skill_dir: Path) -> list[str]:
    """Check the portable subset of the Agent Skill contract."""

    path = skill_dir / "SKILL.md"
    if not path.is_file():
        return ["missing SKILL.md"]
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) < 4 or lines[0] != "---" or "---" not in lines[1:]:
        return ["invalid skill frontmatter"]
    end = lines[1:].index("---") + 1
    frontmatter = lines[1:end]
    name = _frontmatter_value(frontmatter, "name")
    description = _frontmatter_value(frontmatter, "description")
    errors: list[str] = []
    if name != skill_dir.name:
        errors.append(f"invalid skill name: expected {skill_dir.name}")
    if not description or not description.startswith("Use when"):
        errors.append("invalid skill description: must start with Use when")
    if "TODO" in text or "[TODO:" in text:
        errors.append("invalid skill: unresolved TODO")
    return errors


def validate_repository(root: Path) -> list[str]:
    """Return structural errors for a source checkout."""

    root = Path(root)
    errors: list[str] = []
    for relative in sorted(REQUIRED_ROOT_FILES):
        if not (root / relative).is_file():
            errors.append(f"missing root file: {relative}")
    for filename in sorted(REQUIRED_DOCS):
        if not (root / "docs" / filename).is_file():
            errors.append(f"missing documentation: docs/{filename}")
    for filename in sorted(REQUIRED_SCHEMAS):
        if not (root / "schemas" / filename).is_file():
            errors.append(f"missing schema: schemas/{filename}")

    manifest_path = root / "plugins" / "everyone-is-skill" / ".codex-plugin" / "plugin.json"
    if not manifest_path.is_file():
        errors.append("missing Codex plugin manifest")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("name") != "everyone-is-skill":
                errors.append("plugin manifest name must be everyone-is-skill")
            if not isinstance(manifest.get("version"), str) or not SEMVER_PATTERN.fullmatch(manifest["version"]):
                errors.append("plugin manifest version must be semantic version")
            if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
                errors.append("plugin manifest description is required")
            if manifest.get("skills") != "./skills/":
                errors.append("plugin manifest skills path must be ./skills/")
            interface = manifest.get("interface")
            if not isinstance(interface, dict) or not isinstance(interface.get("displayName"), str):
                errors.append("plugin manifest interface.displayName is required")
        except json.JSONDecodeError as exc:
            errors.append(f"invalid plugin manifest JSON: {exc}")

    marketplace_path = root / ".agents" / "plugins" / "marketplace.json"
    if not marketplace_path.is_file():
        errors.append("missing repository plugin marketplace")
    else:
        try:
            marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
            if marketplace.get("name") != "everyone-is-skill":
                errors.append("marketplace name must be everyone-is-skill")
            entries = marketplace.get("plugins")
            if not isinstance(entries, list):
                errors.append("marketplace plugins must be an array")
            else:
                entry = next((item for item in entries if isinstance(item, dict) and item.get("name") == "everyone-is-skill"), None)
                if entry is None:
                    errors.append("marketplace must list everyone-is-skill")
                elif entry.get("source", {}).get("path") != "./plugins/everyone-is-skill":
                    errors.append("marketplace source path must be ./plugins/everyone-is-skill")
        except json.JSONDecodeError as exc:
            errors.append(f"invalid marketplace JSON: {exc}")

    skills_root = root / "plugins" / "everyone-is-skill" / "skills"
    actual_skills = {path.name for path in skills_root.iterdir() if path.is_dir()} if skills_root.is_dir() else set()
    for skill in sorted(REQUIRED_PLUGIN_SKILLS - actual_skills):
        errors.append(f"missing plugin skill: {skill}")
    for skill in sorted(REQUIRED_PLUGIN_SKILLS & actual_skills):
        errors.extend(
            f"invalid skill {skill}: {error}" for error in validate_skill_directory(skills_root / skill)
        )

    shared_pairs = [
        (root / "docs" / filename, root / "plugins" / "everyone-is-skill" / "references" / filename)
        for filename in ("architecture.md", "evidence-policy.md", "profile-contract.md", "evaluation.md", "versioning.md")
    ]
    shared_pairs.extend(
        (source, root / "plugins" / "everyone-is-skill" / "schemas" / source.name)
        for source in (root / "schemas").glob("*.json")
    )
    for source, packaged in shared_pairs:
        if not packaged.is_file():
            errors.append(f"plugin package missing shared file: {packaged.relative_to(root)}")
        elif source.is_file() and source.read_bytes() != packaged.read_bytes():
            errors.append(f"plugin shared file is stale: {packaged.relative_to(root)}")

    for json_path in root.rglob("*.json"):
        if ".git" in json_path.parts:
            continue
        try:
            json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"invalid JSON {json_path.relative_to(root)}: {exc}")

    examples_root = root / "profiles" / "examples"
    if examples_root.is_dir():
        for profile_dir in sorted(path for path in examples_root.iterdir() if path.is_dir()):
            errors.extend(
                f"profile {profile_dir.name}: {error}" for error in validate_profile(profile_dir)
            )
    collectives_root = root / "profiles" / "collectives"
    if collectives_root.is_dir():
        for profile_dir in sorted(path for path in collectives_root.iterdir() if path.is_dir()):
            errors.extend(
                f"collective {profile_dir.name}: {error}" for error in validate_profile(profile_dir)
            )
    templates_root = root / "templates"
    if templates_root.is_dir():
        for template_dir in sorted(path for path in templates_root.iterdir() if path.is_dir()):
            errors.extend(
                f"template {template_dir.name}: {error}" for error in validate_profile(template_dir)
            )
    return errors
