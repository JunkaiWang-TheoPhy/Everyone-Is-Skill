"""Command-line entry point for profile scaffolding and validation."""

from __future__ import annotations

import argparse
import json
import os
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

    fetch_scholarly = subparsers.add_parser(
        "fetch-scholarly", help="fetch reviewed public scholarly metadata into local-ingestion JSONL"
    )
    fetch_scholarly.add_argument("--source", required=True, choices=("arxiv", "inspire", "openalex", "orcid"))
    fetch_scholarly.add_argument("--identifier", required=True)
    fetch_scholarly.add_argument("--output", required=True, type=Path)
    fetch_scholarly.add_argument("--token-env", default="EVERYONE_SKILL_ORCID_TOKEN")
    fetch_scholarly.add_argument("--api-key-env", default="EVERYONE_SKILL_OPENALEX_API_KEY")

    import_upstream = subparsers.add_parser(
        "import-upstream", help="map reviewed upstream Markdown/JSON artifacts to quarantined JSONL"
    )
    import_upstream.add_argument("--input", required=True, type=Path)
    import_upstream.add_argument(
        "--format",
        required=True,
        choices=(
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
        ),
    )
    import_upstream.add_argument("--upstream-url", required=True)
    import_upstream.add_argument("--upstream-license", required=True)
    import_upstream.add_argument(
        "--access", choices=("public", "authorized", "private-reference"), default="authorized"
    )
    import_upstream.add_argument("--output", required=True, type=Path)

    snapshot_profile = subparsers.add_parser("snapshot-profile", help="create an immutable profile snapshot")
    snapshot_profile.add_argument("profile", type=Path)
    snapshot_profile.add_argument("--reason", required=True)

    diff_profile = subparsers.add_parser("diff-profile", help="compare a profile with one history snapshot")
    diff_profile.add_argument("profile", type=Path)
    diff_profile.add_argument("--snapshot", required=True)

    update_claim = subparsers.add_parser(
        "update-claim", help="append one source-backed claim after snapshotting the profile"
    )
    update_claim.add_argument("profile", type=Path)
    update_claim.add_argument("--source", required=True, type=Path)
    update_claim.add_argument("--claim", required=True, type=Path)
    update_claim.add_argument("--reason", required=True)

    rollback_profile = subparsers.add_parser("rollback-profile", help="restore a snapshot after a safety snapshot")
    rollback_profile.add_argument("profile", type=Path)
    rollback_profile.add_argument("--snapshot", required=True)
    rollback_profile.add_argument("--reason", required=True)

    export_profile = subparsers.add_parser("export-profile", help="export a portable profile for a supported runtime")
    export_profile.add_argument("profile", type=Path)
    export_profile.add_argument("--runtime", required=True, choices=("codex", "claude-code", "openclaw", "agents-md"))
    export_profile.add_argument("--output", required=True, type=Path)

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
    if args.command == "fetch-scholarly":
        from .scholarly import fetch_scholarly, write_scholarly_jsonl

        documents = fetch_scholarly(
            args.source,
            args.identifier,
            access_token=os.environ.get(args.token_env),
            api_key=os.environ.get(args.api_key_env),
        )
        output = write_scholarly_jsonl(args.output, documents)
        print(output)
        return 0
    if args.command == "import-upstream":
        from .upstream import import_upstream_artifacts, write_upstream_jsonl

        records = import_upstream_artifacts(
            args.input,
            format_name=args.format,
            upstream_url=args.upstream_url,
            upstream_license=args.upstream_license,
            access=args.access,
        )
        output = write_upstream_jsonl(args.output, records)
        print(output)
        return 0
    if args.command == "snapshot-profile":
        from .versioning import snapshot_profile

        print(json.dumps(snapshot_profile(args.profile, reason=args.reason), ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "diff-profile":
        from .versioning import diff_profile

        print(json.dumps(diff_profile(args.profile, args.snapshot), ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "update-claim":
        from .versioning import update_profile_claim

        source = json.loads(args.source.read_text(encoding="utf-8"))
        claim = json.loads(args.claim.read_text(encoding="utf-8"))
        print(
            json.dumps(
                update_profile_claim(args.profile, source=source, claim=claim, reason=args.reason),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "rollback-profile":
        from .versioning import rollback_profile

        print(
            json.dumps(
                rollback_profile(args.profile, args.snapshot, reason=args.reason),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "export-profile":
        from .exporting import export_profile

        print(export_profile(args.profile, args.output, runtime=args.runtime))
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
