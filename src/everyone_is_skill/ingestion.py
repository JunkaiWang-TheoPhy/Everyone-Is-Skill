"""Normalize authorized local source material without trusting its instructions."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_SUFFIXES = {".jsonl", ".markdown", ".md", ".pdf", ".srt", ".txt", ".vtt"}
SOURCE_TYPES = {
    ".jsonl": "other",
    ".markdown": "notes",
    ".md": "notes",
    ".pdf": "paper",
    ".srt": "transcript",
    ".txt": "notes",
    ".vtt": "transcript",
}
ACCESS_LEVELS = {"public", "authorized", "private-reference"}


@dataclass(frozen=True)
class SourceDocument:
    source_id: str
    sha256: str
    title: str
    source_type: str
    text: str
    path: str
    access: str
    rights_basis: str
    published_at: str = ""
    url: str = ""
    instruction_quarantine: bool = True

    def index_entry(self) -> dict[str, object]:
        entry: dict[str, object] = {
            "source_id": self.source_id,
            "sha256": self.sha256,
            "title": self.title,
            "source_type": self.source_type,
            "path": self.path,
            "access": self.access,
            "rights_basis": self.rights_basis,
            "instruction_quarantine": self.instruction_quarantine,
        }
        if self.published_at:
            entry["published_at"] = self.published_at
        if self.url:
            entry["url"] = self.url
        return entry


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _source_id(payload: bytes) -> tuple[str, str]:
    digest = _digest(payload)
    return f"src-{digest[:16]}", digest


def _transcript_text(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip("\ufeff ")
        if not line or line.isdigit() or "-->" in line or line.upper() == "WEBVTT":
            continue
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def _pdf_text(path: Path) -> str:
    if not pdf_ingestion_available():
        raise RuntimeError(
            "PDF ingestion requires `pdftotext` from Poppler; install poppler (Homebrew) or poppler-utils (Debian/Ubuntu)"
        )
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("PDF ingestion requires the `pdftotext` executable") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"PDF extraction timed out: {path}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit {result.returncode}"
        raise ValueError(f"could not extract PDF text from {path}: {detail}")
    return result.stdout


def pdf_ingestion_available() -> bool:
    """Return whether the explicit external prerequisite for PDF text exists."""

    return shutil.which("pdftotext") is not None


def _title_from_text(path: Path, text: str) -> str:
    for line in text.splitlines():
        match = re.match(r"^#\s+(.+)$", line.strip())
        if match:
            return match.group(1).strip()
    return path.stem.replace("-", " ").replace("_", " ").strip() or path.name


def _document_from_text(path: Path, text: str, raw: bytes, access: str) -> SourceDocument:
    if path.suffix.lower() in {".srt", ".vtt"}:
        text = _transcript_text(text)
    source_id, digest = _source_id(raw)
    return SourceDocument(
        source_id=source_id,
        sha256=digest,
        title=_title_from_text(path, text),
        source_type=SOURCE_TYPES[path.suffix.lower()],
        text=text,
        path=path.name,
        access=access,
        rights_basis=f"user-declared-{access}",
    )


def _jsonl_documents(path: Path, access: str) -> list[SourceDocument]:
    documents: list[SourceDocument] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"JSONL entry must be an object at {path}:{line_number}")
        text = record.get("text", record.get("content", record.get("transcript")))
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"JSONL entry needs text, content, or transcript at {path}:{line_number}")
        payload = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        source_id, digest = _source_id(payload)
        documents.append(
            SourceDocument(
                source_id=source_id,
                sha256=digest,
                title=str(record.get("title") or f"{path.stem} line {line_number}"),
                source_type=str(record.get("source_type") or "other"),
                text=text,
                path=f"{path.name}:{line_number}",
                access=str(record.get("access") or access),
                rights_basis=str(record.get("rights_basis") or f"user-declared-{access}"),
                published_at=str(record.get("published_at") or ""),
                url=str(record.get("url") or ""),
            )
        )
    return documents


def _iter_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for candidate in paths:
        path = Path(candidate)
        if not path.exists():
            raise FileNotFoundError(f"source path does not exist: {path}")
        if path.is_symlink():
            raise ValueError(f"symbolic links are not allowed as source inputs: {path}")
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_symlink():
                    raise ValueError(f"symbolic links are not allowed inside source trees: {child}")
                if child.is_file() and child.suffix.lower() in SUPPORTED_SUFFIXES:
                    files.append(child)
        elif path.suffix.lower() in SUPPORTED_SUFFIXES:
            files.append(path)
    return files


def ingest_paths(paths: list[Path], access: str = "authorized") -> list[SourceDocument]:
    """Read supported files, deduplicate exact artifacts, and mark all text untrusted."""

    if access not in ACCESS_LEVELS:
        raise ValueError(f"access must be one of: {', '.join(sorted(ACCESS_LEVELS))}")
    documents: list[SourceDocument] = []
    for path in _iter_files(paths):
        suffix = path.suffix.lower()
        if suffix == ".jsonl":
            documents.extend(_jsonl_documents(path, access))
            continue
        raw = path.read_bytes()
        text = _pdf_text(path) if suffix == ".pdf" else raw.decode("utf-8-sig")
        documents.append(_document_from_text(path, text, raw, access))

    for document in documents:
        if document.access not in ACCESS_LEVELS:
            raise ValueError(f"source {document.path} has unsupported access value: {document.access}")

    unique: dict[str, SourceDocument] = {}
    for document in documents:
        unique.setdefault(document.sha256, document)
    if not unique:
        raise ValueError("no supported source documents were found")
    return sorted(unique.values(), key=lambda document: document.source_id)
