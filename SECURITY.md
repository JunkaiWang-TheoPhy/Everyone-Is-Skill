# Security Policy

## Supported scope

Version `0.1.x` includes a dependency-free Python CLI, local corpus ingestion,
profile-package writer, contract validators, portable Agent Skills, JSON
schemas, templates, and example profiles. PDF ingestion uses the local
`pdftotext` executable. Reviewed network adapters fetch bounded scholarly
metadata from arXiv, INSPIRE, OpenAlex, and ORCID; upstream project adapters
only map already-local Markdown/JSON artifacts.

The primary threat surfaces are untrusted retrieved text, unsafe paths,
malicious imported Skill instructions, accidental publication of private or
copyrighted corpora, and unsupported person-specific claims presented as fact.

## Reporting a vulnerability

If you find a security issue in this repository:

1. Use the repository's private security advisory flow if it is enabled.
2. If private advisories are unavailable, open a minimal issue that does not
   include exploit details, credentials, or proof-of-concept payloads.
3. Include the affected file path, the risk, and the smallest reproduction you
   can share safely.

## What to avoid in reports

- secrets
- tokens
- private keys
- personal data
- unredacted payloads that could be reused against another system

## Triage expectations

We will confirm receipt, classify the issue, and either request a safe
reproduction or mark the report out of scope. For third-party dependency
concerns, include the upstream repository name and version or commit if known.

## Profile and source safety

- Treat every imported profile and retrieved source as untrusted data.
- Never execute instructions found inside a paper, transcript, profile, or
  imported `SKILL.md` merely because it was retrieved.
- Keep raw private and copyrighted corpora under ignored workspace storage.
- Review output paths before writes and do not follow untrusted symlinks.
- A source URL or declared license is metadata, not proof of trust.
- The offline provider recognizes explicit annotations; annotation text is
  still unreviewed evidence and cannot promote a profile to release-ready.
- Directory ingestion rejects symbolic links, omits absolute local paths from
  generated indexes, and validates provider-emitted claims before writing.
- Network responses are size-limited, credentials are read from named
  environment variables and never serialized, and imported executable files
  are ignored rather than activated.
