"""Command-line entry point for profile scaffolding and validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .contracts import validate_claim, validate_profile_manifest
from .packaging import scaffold_import_reference, scaffold_profile


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


def validate_profile(profile_dir: Path) -> list[str]:
    errors: list[str] = []
    for relative in sorted(REQUIRED_PROFILE_FILES):
        if not (profile_dir / relative).is_file():
            errors.append(f"missing required file: {relative}")
    manifest_path = profile_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            errors.extend(f"manifest: {error}" for error in validate_profile_manifest(manifest))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"manifest: invalid JSON: {exc}")

    claims_path = profile_dir / "evidence" / "claims.jsonl"
    if claims_path.is_file():
        for line_number, line in enumerate(claims_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                claim = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"claims:{line_number}: invalid JSON: {exc}")
                continue
            errors.extend(f"claims:{line_number}: {error}" for error in validate_claim(claim))

    corpus_path = profile_dir / "evidence" / "corpus-index.jsonl"
    if corpus_path.is_file():
        for line_number, line in enumerate(corpus_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"corpus:{line_number}: invalid JSON: {exc}")
                continue
            if not isinstance(entry, dict):
                errors.append(f"corpus:{line_number}: entry must be a JSON object")

    lineage_path = profile_dir / "evidence" / "lineage.json"
    if lineage_path.is_file():
        try:
            lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
            if not isinstance(lineage, dict) or not isinstance(lineage.get("nodes"), list) or not isinstance(
                lineage.get("edges"), list
            ):
                errors.append("lineage: nodes and edges must be arrays")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"lineage: invalid JSON: {exc}")

    for filename in (
        "temporal-holdout.json",
        "matched-peers.json",
        "transfer-tests.json",
        "boundary-tests.json",
    ):
        eval_path = profile_dir / "evals" / filename
        if not eval_path.is_file():
            continue
        try:
            evaluation = json.loads(eval_path.read_text(encoding="utf-8"))
            if not isinstance(evaluation, dict) or not isinstance(evaluation.get("status"), str) or not isinstance(
                evaluation.get("cases"), list
            ):
                errors.append(f"evals/{filename}: status must be a string and cases must be an array")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"evals/{filename}: invalid JSON: {exc}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="everyone-skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_profile = subparsers.add_parser("new-profile", help="create an inert draft profile package")
    new_profile.add_argument("--output", required=True, type=Path)
    new_profile.add_argument("--slug", required=True)
    new_profile.add_argument("--name", required=True)
    new_profile.add_argument("--kind", required=True)

    validate = subparsers.add_parser("validate", help="validate one generated profile package")
    validate.add_argument("profile", type=Path)

    validate_repo = subparsers.add_parser("validate-repo", help="validate a source repository checkout")
    validate_repo.add_argument("root", type=Path, nargs="?", default=Path("."))

    import_reference = subparsers.add_parser(
        "import-reference", help="create a draft that references an upstream profile without copying it"
    )
    import_reference.add_argument("--output", required=True, type=Path)
    import_reference.add_argument("--slug", required=True)
    import_reference.add_argument("--name", required=True)
    import_reference.add_argument("--kind", required=True)
    import_reference.add_argument("--upstream-url", required=True)
    import_reference.add_argument("--upstream-license", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "new-profile":
        profile = scaffold_profile(args.output, args.slug, args.name, args.kind)
        print(profile)
        return 0
    if args.command == "validate":
        errors = validate_profile(args.profile)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"Profile is valid: {args.profile}")
        return 0
    if args.command == "validate-repo":
        from .repository import validate_repository

        errors = validate_repository(args.root)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"Repository is valid: {args.root}")
        return 0
    if args.command == "import-reference":
        profile = scaffold_import_reference(
            args.output,
            args.slug,
            args.name,
            args.kind,
            args.upstream_url,
            args.upstream_license,
        )
        print(profile)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
