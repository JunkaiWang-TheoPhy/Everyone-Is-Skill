"""Command-line entry point for profile scaffolding and validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .packaging import scaffold_import_reference, scaffold_profile
from .release import check_release_readiness, validate_profile


def _anchor(value: str) -> dict[str, str]:
    anchor_type, separator, anchor_value = value.partition("=")
    if not separator or not anchor_type.strip() or not anchor_value.strip():
        raise argparse.ArgumentTypeError("anchor must use TYPE=VALUE")
    return {"type": anchor_type.strip(), "value": anchor_value.strip()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="everyone-skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("capabilities", help="report optional local runtime prerequisites")

    new_profile = subparsers.add_parser("new-profile", help="create an inert draft profile package")
    new_profile.add_argument("--output", required=True, type=Path)
    new_profile.add_argument("--slug", required=True)
    new_profile.add_argument("--name", required=True)
    new_profile.add_argument("--kind", required=True)

    validate = subparsers.add_parser("validate", help="validate one generated profile package")
    validate.add_argument("profile", type=Path)

    release_check = subparsers.add_parser("release-check", help="fail closed unless one profile is release-ready")
    release_check.add_argument("profile", type=Path)

    distill_local = subparsers.add_parser(
        "distill-local", help="build a complete draft from public or authorized local source files"
    )
    distill_local.add_argument("--input", required=True, action="append", type=Path)
    distill_local.add_argument("--output", required=True, type=Path)
    distill_local.add_argument("--slug", required=True)
    distill_local.add_argument("--name", required=True)
    distill_local.add_argument("--kind", required=True)
    distill_local.add_argument("--anchor", required=True, action="append", type=_anchor)
    distill_local.add_argument(
        "--access", choices=("public", "authorized", "private-reference"), default="authorized"
    )

    run_evals = subparsers.add_parser("run-evals", help="execute all recorded-output profile evaluation suites")
    run_evals.add_argument("profile", type=Path)
    run_evals.add_argument("--provider", required=True)
    run_evals.add_argument("--model", required=True)
    run_evals.add_argument("--reviewer", required=True)

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
    if args.command == "capabilities":
        from .ingestion import pdf_ingestion_available

        print(
            json.dumps(
                {
                    "local_formats": ["jsonl", "markdown", "srt", "text", "vtt"],
                    "pdf": {"available": pdf_ingestion_available(), "requires": "pdftotext (Poppler)"},
                },
                sort_keys=True,
            )
        )
        return 0
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
    if args.command == "distill-local":
        from .distillation import distill_local_corpus

        profile = distill_local_corpus(
            inputs=args.input,
            output_dir=args.output,
            slug=args.slug,
            display_name=args.name,
            target_type=args.kind,
            identity_anchors=args.anchor,
            access=args.access,
        )
        print(profile)
        return 0
    if args.command == "run-evals":
        from .evaluation import run_evaluations

        summary = run_evaluations(
            args.profile,
            provider=args.provider,
            model=args.model,
            reviewer=args.reviewer,
        )
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0 if summary["status"] == "passed" else 1
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
