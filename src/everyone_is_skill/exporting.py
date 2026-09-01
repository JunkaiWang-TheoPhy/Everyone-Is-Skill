"""Cross-runtime exports that preserve the portable profile contract."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .evaluation import EVALUATION_SUITES
from .release import REQUIRED_PROFILE_FILES, validate_profile


RUNTIMES = ("codex", "claude-code", "openclaw", "agents-md")
PORTABLE_PROFILE_FILES = REQUIRED_PROFILE_FILES | {f"evals/{suite}.json" for suite in EVALUATION_SUITES}


def export_profile(profile_dir: Path, output_dir: Path, *, runtime: str) -> Path:
    profile_dir = Path(profile_dir)
    if runtime not in RUNTIMES:
        raise ValueError(f"runtime must be one of: {', '.join(RUNTIMES)}")
    errors = validate_profile(profile_dir)
    if errors:
        raise ValueError(f"cannot export invalid profile: {'; '.join(errors)}")
    manifest = json.loads((profile_dir / "manifest.json").read_text(encoding="utf-8"))
    output_dir = Path(output_dir)
    runtime_dir = output_dir / runtime
    destination = runtime_dir / manifest["slug"]
    for path in (output_dir, runtime_dir, destination):
        if path.is_symlink():
            raise ValueError(f"export destination path contains a symbolic link: {path}")
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"export destination is not empty: {destination}")
    for relative in sorted(PORTABLE_PROFILE_FILES):
        source = profile_dir / relative
        if source.is_symlink():
            raise ValueError(f"profile export does not follow symbolic links: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    optional_review = profile_dir / "peer-review.md"
    if optional_review.is_symlink():
        raise ValueError("profile export does not follow symbolic links: peer-review.md")
    if optional_review.is_file():
        shutil.copy2(optional_review, destination / "peer-review.md")
    entrypoint = "SKILL.md"
    if runtime == "agents-md":
        entrypoint = "AGENTS.md"
        method = (profile_dir / "method.md").read_text(encoding="utf-8")
        agents = (
            f"# {manifest['display_name']} — bounded method profile\n\n"
            "This is not an impersonation. Apply only evidence-grounded methods within `manifest.json` boundaries.\n\n"
            f"{method}"
        )
        (destination / "AGENTS.md").write_text(agents, encoding="utf-8")
    runtime_metadata = {
        "schema_version": "1.0",
        "runtime": runtime,
        "entrypoint": entrypoint,
        "profile_slug": manifest["slug"],
        "profile_version": manifest.get("profile_version", "unversioned"),
        "contract_modified": False,
        "history_exported": False,
    }
    (destination / "runtime.json").write_text(
        json.dumps(runtime_metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination
