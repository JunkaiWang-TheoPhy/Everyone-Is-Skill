#!/usr/bin/env python3
"""Check repository-local Markdown links and optionally probe remote URLs."""

from __future__ import annotations

import argparse
import concurrent.futures
import functools
import ipaddress
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
HTML_LINK = re.compile(r"(?:href|src)=[\"']([^\"']+)[\"']")
SKIP_DIRS = {".git", ".omx", ".superpowers", "dist", "build", "__pycache__"}
ALLOWED_REMOTE_HOSTS = {
    "arxiv.org",
    "daweb.qzc.tsinghua.edu.cn",
    "docs.pytest.org",
    "doi.org",
    "ep-news.web.cern.ch",
    "github.com",
    "help.openalex.org",
    "heritageproject.caltech.edu",
    "img.shields.io",
    "info.orcid.org",
    "link.springer.com",
    "numdam.org",
    "physics.mit.edu",
    "pirsa.org",
    "pmc.ncbi.nlm.nih.gov",
    "www.ias.edu",
    "www.ihes.fr",
    "www.macfound.org",
    "www.math.harvard.edu",
    "www.mathunion.org",
    "www.nobelprize.org",
    "www.sns.ias.edu",
    "www.stonybrook.edu",
    "www.tsinghua.edu.cn",
}


def _markdown_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if not any(part in SKIP_DIRS for part in path.relative_to(root).parts)
    )


def _targets(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return MARKDOWN_LINK.findall(text) + HTML_LINK.findall(text)


def _clean_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if " " in target and not target.startswith(("http://", "https://")):
        target = target.split(" ", 1)[0]
    return target


def check_local_links(root: Path) -> list[str]:
    root = Path(root).resolve()
    errors: list[str] = []
    for document in _markdown_files(root):
        for raw in _targets(document):
            target = _clean_target(raw)
            if not target or target.startswith(("#", "mailto:", "codex://", "data:")):
                continue
            parsed = urllib.parse.urlparse(target)
            if parsed.scheme in {"http", "https"}:
                continue
            relative_path = urllib.parse.unquote(parsed.path)
            if not relative_path:
                continue
            resolved = (document.parent / relative_path).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                errors.append(f"{document.relative_to(root)}: local link escapes repository: {target}")
                continue
            if not resolved.exists():
                errors.append(f"{document.relative_to(root)}: missing local link target: {target}")
    return errors


@functools.lru_cache(maxsize=256)
def _public_addresses(hostname: str) -> tuple[str, ...]:
    return tuple(sorted({item[4][0] for item in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)}))


def _remote_url_error(url: str, *, require_allowlist: bool = True) -> str | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return "remote URL must be credential-free HTTPS"
    if parsed.port not in {None, 443}:
        return "remote URL must use the standard HTTPS port"
    try:
        literal = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        literal = None
    if literal is not None and not literal.is_global:
        return "private or non-global address is forbidden"
    if require_allowlist and parsed.hostname.lower() not in ALLOWED_REMOTE_HOSTS:
        return f"host is not allowlisted: {parsed.hostname}"
    try:
        addresses = _public_addresses(parsed.hostname)
    except socket.gaierror:
        return "hostname did not resolve"
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        return "private or non-global DNS result is forbidden"
    return None


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        error = _remote_url_error(newurl, require_allowlist=False)
        if error:
            raise urllib.error.URLError(f"unsafe redirect blocked: {error}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


REMOTE_OPENER = urllib.request.build_opener(_SafeRedirectHandler())


def _probe(url: str) -> tuple[str, str | None]:
    safety_error = _remote_url_error(url)
    if safety_error:
        return url, safety_error
    last_error = "unreachable"
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 Everyone-Is-Skill-link-check/1.0", "Range": "bytes=0-1023"},
            method=method,
        )
        try:
            with REMOTE_OPENER.open(request, timeout=20) as response:
                if response.status >= 400:
                    last_error = f"HTTP {response.status}"
                    continue
                if method == "GET":
                    response.read(1024)
                return url, None
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403, 429}:
                return url, None
            last_error = f"HTTP {exc.code}"
            if method == "HEAD" and exc.code == 405:
                continue
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = type(exc).__name__
    return url, last_error


def check_remote_links(root: Path) -> list[str]:
    root = Path(root)
    urls = {
        _clean_target(target)
        for document in _markdown_files(root)
        for target in _targets(document)
        if _clean_target(target).startswith("https://")
    }
    for corpus_path in root.glob("profiles/*/*/evidence/corpus-index.jsonl"):
        for line in corpus_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                url = json.loads(line).get("url")
                if isinstance(url, str) and url.startswith("https://"):
                    urls.add(url)
    for manifest_path in root.glob("profiles/*/*/manifest.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for anchor in manifest.get("identity_anchors", []):
            value = anchor.get("value") if isinstance(anchor, dict) else None
            if isinstance(value, str) and value.startswith("https://"):
                urls.add(value)
    errors: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for url, error in pool.map(_probe, sorted(urls)):
            if error:
                errors.append(f"{url}: {error}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--remote", action="store_true")
    args = parser.parse_args()
    errors = check_local_links(args.root)
    if args.remote:
        errors.extend(check_remote_links(args.root))
    if errors:
        for error in errors:
            print(error)
        return 1
    print("Links are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
