#!/usr/bin/env python3
"""Fail-closed privacy, version, marketplace, and license-boundary audit."""

from __future__ import annotations

import json
import re
from pathlib import Path


SKIP_DIRS = {".git", ".omx", ".superpowers", ".venv", ".tox", "dist", "build", "__pycache__"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".jsonl", ".toml", ".yaml", ".yml", ".cff", ".txt"}
SENSITIVE_PATTERNS = {
    "absolute macOS user path": re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    "absolute Linux home path": re.compile(r"/home/[A-Za-z0-9._-]+/"),
    "Windows user path": re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+"),
    "private key": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{20,}\b"),
    "Hugging Face token": re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    "bearer token": re.compile(r"Bearer\s+[A-Za-z0-9._~-]{20,}"),
    "credential assignment": re.compile(
        r"(?i)\b(?:password|passwd|client_secret|api[_-]?key)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]"
    ),
}
FORBIDDEN_CORPUS_FIELDS = {"text", "content", "body", "full_text", "transcript"}
SUSPICIOUS_FILE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


def _files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def _project_version(root: Path) -> str:
    match = re.search(r'^version\s*=\s*"([^"]+)"', (root / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else ""


def audit_public_corpus_indexes(root: Path) -> list[str]:
    root = Path(root)
    errors: list[str] = []
    corpus_paths = list(root.glob("profiles/*/*/evidence/corpus-index.jsonl"))
    corpus_paths.extend(root.glob("templates/*/evidence/corpus-index.jsonl"))
    for corpus_path in sorted(corpus_paths):
        for line_number, line in enumerate(corpus_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            source = json.loads(line)
            embedded = FORBIDDEN_CORPUS_FIELDS & set(source) if isinstance(source, dict) else set()
            if embedded:
                errors.append(
                    f"{corpus_path.relative_to(root)}:{line_number}: public corpus index must not embed raw source text ({', '.join(sorted(embedded))})"
                )
    return errors


def audit_repository(root: Path) -> list[str]:
    root = Path(root).resolve()
    errors: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.name == ".env" or path.name.startswith(".env.") or path.suffix.lower() in SUSPICIOUS_FILE_SUFFIXES:
            errors.append(f"{path.relative_to(root)}: suspicious secret-bearing filename")
    for path in _files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{path.relative_to(root)}: {label}")

    version = _project_version(root)
    plugin = json.loads((root / "plugins/everyone-is-skill/.codex-plugin/plugin.json").read_text(encoding="utf-8"))
    citation = (root / "CITATION.cff").read_text(encoding="utf-8")
    for label, actual in (
        ("pyproject", version),
        ("plugin", str(plugin.get("version", ""))),
    ):
        if actual != "1.0.0":
            errors.append(f"{label} version must be 1.0.0, found {actual or 'missing'}")
    if 'version: "1.0.0"' not in citation and "version: 1.0.0" not in citation:
        errors.append("CITATION.cff version must be 1.0.0")

    license_text = (root / "LICENSE").read_text(encoding="utf-8")
    if "Apache License" not in license_text or "Version 2.0" not in license_text:
        errors.append("LICENSE must contain Apache-2.0 text")
    lock = (root / "integrations/integrations.lock.yaml").read_text(encoding="utf-8")
    if "bundled: true" in lock:
        errors.append("integration ledger must not mark upstream implementation code as bundled")
    if "mirrormind" in lock.lower():
        errors.append("unresolved MirrorMind must not re-enter the integration ledger")

    marketplace_path = root / ".agents/plugins/marketplace.json"
    if not marketplace_path.is_file():
        errors.append("missing repository plugin marketplace")
    else:
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        entries = marketplace.get("plugins", []) if isinstance(marketplace, dict) else []
        entry = next((item for item in entries if item.get("name") == "everyone-is-skill"), None)
        if not entry or entry.get("source", {}).get("path") != "./plugins/everyone-is-skill":
            errors.append("marketplace must point everyone-is-skill to ./plugins/everyone-is-skill")

    errors.extend(audit_public_corpus_indexes(root))
    return errors


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    args = parser.parse_args()
    errors = audit_repository(args.root)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("Release audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
