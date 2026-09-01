"""Dependency-free adapters for reviewed scholarly metadata APIs."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

from .ingestion import SourceDocument


MAX_RESPONSE_BYTES = 10 * 1024 * 1024
USER_AGENT = "Everyone-Is-Skill/0.1 (+https://github.com/JunkaiWang-TheoPhy/Everyone-Is-Skill)"
Fetcher = Callable[[str, dict[str, str]], bytes]
ADAPTERS = {"arxiv", "inspire", "openalex", "orcid"}


def _http_get(url: str, headers: dict[str, str]) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"scholarly API request failed: {type(exc).__name__}") from exc
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("scholarly API response exceeds the 10 MiB safety limit")
    return payload


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def _document(
    *,
    adapter: str,
    canonical_id: str,
    title: str,
    text: str,
    source_type: str,
    url: str,
    authors: list[str] | tuple[str, ...] = (),
    published_at: str = "",
    rights_basis: str,
) -> SourceDocument:
    normalized = {
        "adapter": adapter,
        "canonical_id": canonical_id,
        "title": title,
        "text": text,
        "url": url,
        "authors": list(authors),
        "published_at": published_at,
    }
    payload = json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return SourceDocument(
        source_id=f"{adapter}:{canonical_id}",
        sha256=digest,
        title=title,
        source_type=source_type,
        text=text,
        path=url,
        access="public",
        rights_basis=rights_basis,
        authors=tuple(authors),
        published_at=published_at,
        url=url,
        adapter=adapter,
        canonical_id=canonical_id,
    )


def _arxiv(identifier: str, fetcher: Fetcher) -> list[SourceDocument]:
    if not re.fullmatch(r"(?:[a-z-]+(?:\.[A-Z]{2})?/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?", identifier):
        raise ValueError("invalid arXiv identifier")
    query = urllib.parse.urlencode({"id_list": identifier, "max_results": 1})
    payload = fetcher(f"https://export.arxiv.org/api/query?{query}", {"Accept": "application/atom+xml"})
    lowered_payload = payload.lower()
    if b"<!doctype" in lowered_payload or b"<!entity" in lowered_payload:
        raise ValueError("arXiv XML response must not contain a DTD or entity declaration")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ValueError(f"invalid arXiv Atom response: {exc}") from exc
    atom = "{http://www.w3.org/2005/Atom}"
    entry = root.find(f"{atom}entry")
    if entry is None:
        raise ValueError(f"arXiv returned no entry for {identifier}")
    title = _clean(entry.findtext(f"{atom}title"))
    abstract = _clean(entry.findtext(f"{atom}summary"))
    canonical_id = _clean(entry.findtext(f"{atom}id")) or identifier
    authors = [_clean(author.findtext(f"{atom}name")) for author in entry.findall(f"{atom}author")]
    authors = [author for author in authors if author]
    url = canonical_id
    for link in entry.findall(f"{atom}link"):
        if link.attrib.get("rel") == "alternate" and link.attrib.get("href"):
            url = link.attrib["href"]
            break
    return [
        _document(
            adapter="arxiv",
            canonical_id=identifier,
            title=title,
            text=f"# {title}\n\n{abstract}\n",
            source_type="preprint",
            url=url,
            authors=authors,
            published_at=_clean(entry.findtext(f"{atom}published")),
            rights_basis="arXiv API metadata terms; source text remains subject to its own license",
        )
    ]


def _inspire(identifier: str, fetcher: Fetcher) -> list[SourceDocument]:
    identifier_type, separator, value = identifier.partition(":")
    if not separator or identifier_type not in {"literature", "arxiv", "doi", "orcid"} or not value:
        raise ValueError("INSPIRE identifier must use literature:, arxiv:, doi:, or orcid:")
    if identifier_type == "literature" and not value.isdigit():
        raise ValueError("INSPIRE literature identifier must be numeric")
    encoded = urllib.parse.quote(value, safe="")
    payload = fetcher(
        f"https://inspirehep.net/api/{identifier_type}/{encoded}",
        {"Accept": "application/json"},
    )
    try:
        record = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid INSPIRE JSON response: {exc}") from exc
    if not isinstance(record, dict) or not isinstance(record.get("metadata"), dict):
        raise ValueError("INSPIRE response is missing metadata")
    metadata = record["metadata"]
    titles = metadata.get("titles", [])
    abstracts = metadata.get("abstracts", [])
    title = _clean(titles[0].get("title")) if titles and isinstance(titles[0], dict) else ""
    abstract = _clean(abstracts[0].get("value")) if abstracts and isinstance(abstracts[0], dict) else ""
    authors = [
        _clean(author.get("full_name"))
        for author in metadata.get("authors", [])
        if isinstance(author, dict) and author.get("full_name")
    ]
    links = record.get("links") if isinstance(record.get("links"), dict) else {}
    url = _clean(links.get("self")) or f"https://inspirehep.net/api/{identifier_type}/{encoded}"
    return [
        _document(
            adapter="inspire",
            canonical_id=f"literature:{record.get('id')}" if record.get("id") else identifier,
            title=title,
            text=f"# {title}\n\n{abstract}\n",
            source_type="preprint" if metadata.get("arxiv_eprints") else "paper",
            url=url,
            authors=authors,
            published_at=_clean(metadata.get("preprint_date") or metadata.get("earliest_date")),
            rights_basis="INSPIRE API terms; most metadata CC0, with field-level restrictions",
        )
    ]


def _openalex_abstract(index: object) -> str:
    if not isinstance(index, dict):
        return ""
    positions: list[tuple[int, str]] = []
    for word, offsets in index.items():
        if isinstance(word, str) and isinstance(offsets, list):
            positions.extend((offset, word) for offset in offsets if isinstance(offset, int) and offset >= 0)
    return " ".join(word for _, word in sorted(positions))


def _openalex(identifier: str, fetcher: Fetcher, api_key: str | None) -> list[SourceDocument]:
    if not re.fullmatch(r"W\d+", identifier) and not identifier.startswith("10."):
        raise ValueError("OpenAlex identifier must be a W-id or DOI")
    external_id = identifier if identifier.startswith("W") else f"https://doi.org/{identifier}"
    encoded = urllib.parse.quote(external_id, safe="")
    url = f"https://api.openalex.org/works/{encoded}"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = fetcher(url, headers)
    try:
        record = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid OpenAlex JSON response: {exc}") from exc
    if not isinstance(record, dict):
        raise ValueError("OpenAlex response must be an object")
    title = _clean(record.get("display_name") or record.get("title"))
    abstract = _openalex_abstract(record.get("abstract_inverted_index"))
    authors = [
        _clean(authorship.get("author", {}).get("display_name"))
        for authorship in record.get("authorships", [])
        if isinstance(authorship, dict) and isinstance(authorship.get("author"), dict)
    ]
    authors = [author for author in authors if author]
    location = record.get("primary_location") if isinstance(record.get("primary_location"), dict) else {}
    landing_page = _clean(location.get("landing_page_url"))
    return [
        _document(
            adapter="openalex",
            canonical_id=(_clean(record.get("id")).rsplit("/", 1)[-1] if record.get("id") else identifier),
            title=title,
            text=f"# {title}\n\n{abstract}\n",
            source_type="preprint" if record.get("type") == "preprint" else "paper",
            url=landing_page or _clean(record.get("id")),
            authors=authors,
            published_at=_clean(record.get("publication_date")),
            rights_basis="OpenAlex API terms and CC0 metadata",
        )
    ]


def _orcid(identifier: str, fetcher: Fetcher, access_token: str | None) -> list[SourceDocument]:
    if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-[\dX]{4}", identifier):
        raise ValueError("invalid ORCID iD")
    if not access_token:
        raise ValueError("ORCID Public API requires an access token with /read-public scope")
    url = f"https://pub.orcid.org/v3.0/{identifier}/works"
    payload = fetcher(url, {"Accept": "application/vnd.orcid+json", "Authorization": f"Bearer {access_token}"})
    try:
        record = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid ORCID JSON response: {exc}") from exc
    documents: list[SourceDocument] = []
    for group in record.get("group", []) if isinstance(record, dict) else []:
        if not isinstance(group, dict):
            continue
        summaries = group.get("work-summary", [])
        if not isinstance(summaries, list) or not summaries:
            continue
        summary = summaries[0]
        if not isinstance(summary, dict):
            continue
        title_record = summary.get("title") if isinstance(summary.get("title"), dict) else {}
        title_value = title_record.get("title") if isinstance(title_record.get("title"), dict) else {}
        title = _clean(title_value.get("value"))
        external_ids = summary.get("external-ids") if isinstance(summary.get("external-ids"), dict) else {}
        identifiers = [
            f"{_clean(item.get('external-id-type'))}: {_clean(item.get('external-id-value'))}"
            for item in external_ids.get("external-id", [])
            if isinstance(item, dict)
        ]
        publication = summary.get("publication-date") if isinstance(summary.get("publication-date"), dict) else {}
        year = publication.get("year") if isinstance(publication.get("year"), dict) else {}
        work_url = summary.get("url") if isinstance(summary.get("url"), dict) else {}
        canonical_id = f"{identifier}:{summary.get('put-code', title)}"
        documents.append(
            _document(
                adapter="orcid",
                canonical_id=canonical_id,
                title=title,
                text=f"# {title}\n\n" + "\n".join(identifiers) + "\n",
                source_type="paper",
                url=_clean(work_url.get("value")) or f"https://orcid.org/{identifier}",
                published_at=_clean(year.get("value")),
                rights_basis="ORCID Public API terms; public record metadata only",
            )
        )
    if not documents:
        raise ValueError(f"ORCID returned no public works for {identifier}")
    return documents


def fetch_scholarly(
    source: str,
    identifier: str,
    *,
    fetcher: Fetcher = _http_get,
    access_token: str | None = None,
    api_key: str | None = None,
) -> list[SourceDocument]:
    """Fetch and normalize one scholarly identifier through a reviewed adapter."""

    source = source.lower().strip()
    identifier = identifier.strip()
    if source not in ADAPTERS:
        raise ValueError(f"unknown scholarly adapter: {source}")
    if source == "arxiv":
        return _arxiv(identifier, fetcher)
    if source == "inspire":
        return _inspire(identifier, fetcher)
    if source == "openalex":
        return _openalex(identifier, fetcher, api_key)
    return _orcid(identifier, fetcher, access_token)


def write_scholarly_jsonl(path: Path, documents: list[SourceDocument]) -> Path:
    """Write normalized metadata plus quarantined text for ``distill-local``."""

    path = Path(path)
    if path.is_symlink():
        raise ValueError("scholarly output cannot be a symbolic link")
    path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for document in documents:
        record = document.index_entry()
        record["text"] = document.text
        records.append(record)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    return path
