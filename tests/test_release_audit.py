import unittest
import json
import tempfile
from pathlib import Path

from scripts.audit_release import audit_public_corpus_indexes, audit_repository
from scripts.check_links import _remote_url_error, check_local_links


ROOT = Path(__file__).resolve().parents[1]


class ReleaseAuditTests(unittest.TestCase):
    def test_release_audit_has_no_findings(self):
        self.assertEqual(audit_repository(ROOT), [])

    def test_all_local_markdown_links_resolve(self):
        self.assertEqual(check_local_links(ROOT), [])

    def test_raw_text_is_rejected_in_collective_or_template_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in (
                "profiles/collectives/example/evidence/corpus-index.jsonl",
                "templates/scientist/evidence/corpus-index.jsonl",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"source_id": "x", "transcript": "private raw text"}) + "\n")
            errors = audit_public_corpus_indexes(root)
            self.assertEqual(len(errors), 2)
            self.assertTrue(all("raw source text" in error for error in errors))

    def test_remote_probe_rejects_private_or_untrusted_targets(self):
        self.assertIn("not allowlisted", _remote_url_error("https://evil.example/path"))
        self.assertIn("private", _remote_url_error("https://127.0.0.1/metadata"))


if __name__ == "__main__":
    unittest.main()
