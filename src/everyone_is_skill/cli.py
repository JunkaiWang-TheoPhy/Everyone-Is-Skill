"""Command-line entry point for profile scaffolding and validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .packaging import scaffold_import_reference, scaffold_profile
from .release import check_release_readiness, validate_profile


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

    release_check = subparsers.add_parser("release-check", help="fail closed unless one profile is release-ready")
    release_check.add_argument("profile", type=Path)

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
    if args.command == "release-check":
        errors = check_release_readiness(args.profile)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"Profile is release-ready: {args.profile}")
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
