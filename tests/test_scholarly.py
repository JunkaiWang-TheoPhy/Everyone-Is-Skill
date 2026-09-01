import json
import tempfile
import unittest
from pathlib import Path

from everyone_is_skill.ingestion import ingest_paths
from everyone_is_skill.scholarly import fetch_scholarly, write_scholarly_jsonl


ARXIV_FIXTURE = b"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'>
  <entry>
    <id>http://arxiv.org/abs/hep-th/9711200v3</id>
    <updated>1998-01-22T00:00:00Z</updated>
    <published>1997-11-27T00:00:00Z</published>
    <title>The Large N Limit of Superconformal Field Theories</title>
    <summary>We study a duality using a controlled large N limit.</summary>
    <author><name>Juan Maldacena</name></author>
    <link href='https://arxiv.org/abs/hep-th/9711200v3' rel='alternate'/>
  </entry>
</feed>
"""

INSPIRE_FIXTURE = {
    "id": "451647",
    "links": {"self": "https://inspirehep.net/api/literature/451647"},
    "metadata": {
        "titles": [{"title": "The Large N Limit"}],
        "abstracts": [{"value": "A dual description is proposed."}],
        "authors": [{"full_name": "Maldacena, Juan Martin"}],
        "preprint_date": "1997-11-27",
        "arxiv_eprints": [{"value": "hep-th/9711200"}],
    },
}

OPENALEX_FIXTURE = {
    "id": "https://openalex.org/W123",
    "display_name": "A Work",
    "publication_date": "2024-02-03",
    "type": "article",
    "authorships": [{"author": {"display_name": "A. Researcher"}}],
    "abstract_inverted_index": {"Test": [0], "the": [1], "limit": [2]},
    "primary_location": {"landing_page_url": "https://doi.org/10.1/example"},
}

ORCID_FIXTURE = {
    "group": [
        {
            "work-summary": [
                {
                    "put-code": 42,
                    "title": {"title": {"value": "An ORCID Work"}},
                    "type": "journal-article",
                    "publication-date": {"year": {"value": "2023"}},
                    "external-ids": {
                        "external-id": [
                            {"external-id-type": "doi", "external-id-value": "10.1/example"}
                        ]
                    },
                    "url": {"value": "https://example.test/work"},
                }
            ]
        }
    ]
}


class ScholarlyAdapterTests(unittest.TestCase):
    def fake_fetcher(self, payload):
        calls = []

        def fetch(url, headers):
            calls.append((url, headers))
            return payload

        return fetch, calls

    def test_arxiv_atom_is_normalized(self):
        fetcher, calls = self.fake_fetcher(ARXIV_FIXTURE)
        documents = fetch_scholarly("arxiv", "hep-th/9711200", fetcher=fetcher)
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].source_type, "preprint")
        self.assertEqual(documents[0].authors, ("Juan Maldacena",))
        self.assertIn("controlled large N limit", documents[0].text)
        self.assertEqual(documents[0].source_id, "arxiv:hep-th/9711200")
        self.assertEqual(documents[0].canonical_id, "hep-th/9711200")
        self.assertIn("id_list=hep-th%2F9711200", calls[0][0])

        changed = ARXIV_FIXTURE.replace(b"controlled large N limit", b"different abstract wording")
        changed_fetcher, _ = self.fake_fetcher(changed)
        changed_document = fetch_scholarly("arxiv", "hep-th/9711200", fetcher=changed_fetcher)[0]
        self.assertEqual(changed_document.source_id, documents[0].source_id)
        self.assertNotEqual(changed_document.sha256, documents[0].sha256)

    def test_arxiv_rejects_xml_entity_declarations(self):
        malicious = b"<!DOCTYPE feed [<!ENTITY x 'expanded'>]><feed>&x;</feed>"
        fetcher, _ = self.fake_fetcher(malicious)
        with self.assertRaisesRegex(ValueError, "DTD or entity"):
            fetch_scholarly("arxiv", "hep-th/9711200", fetcher=fetcher)

    def test_inspire_json_is_normalized(self):
        fetcher, calls = self.fake_fetcher(json.dumps(INSPIRE_FIXTURE).encode())
        documents = fetch_scholarly("inspire", "literature:451647", fetcher=fetcher)
        self.assertEqual(documents[0].title, "The Large N Limit")
        self.assertEqual(documents[0].authors, ("Maldacena, Juan Martin",))
        self.assertEqual(calls[0][0], "https://inspirehep.net/api/literature/451647")

    def test_openalex_json_reconstructs_abstract(self):
        fetcher, calls = self.fake_fetcher(json.dumps(OPENALEX_FIXTURE).encode())
        documents = fetch_scholarly("openalex", "W123", fetcher=fetcher, api_key="secret")
        self.assertIn("Test the limit", documents[0].text)
        self.assertNotIn("secret", calls[0][0])
        self.assertEqual(calls[0][1]["Authorization"], "Bearer secret")
        self.assertNotIn("secret", documents[0].index_entry().values())

    def test_orcid_requires_token_and_exports_public_work_metadata(self):
        with self.assertRaisesRegex(ValueError, "ORCID.*access token"):
            fetch_scholarly("orcid", "0000-0002-1825-0097", fetcher=lambda *_: b"")
        fetcher, calls = self.fake_fetcher(json.dumps(ORCID_FIXTURE).encode())
        documents = fetch_scholarly(
            "orcid", "0000-0002-1825-0097", fetcher=fetcher, access_token="token-value"
        )
        self.assertEqual(documents[0].title, "An ORCID Work")
        self.assertEqual(calls[0][1]["Authorization"], "Bearer token-value")
        self.assertNotIn("token-value", json.dumps(documents[0].index_entry()))

    def test_export_is_compatible_with_local_ingestion(self):
        fetcher, _ = self.fake_fetcher(ARXIV_FIXTURE)
        documents = fetch_scholarly("arxiv", "hep-th/9711200", fetcher=fetcher)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp, "arxiv.jsonl")
            write_scholarly_jsonl(output, documents)
            record = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(record["source_id"], documents[0].source_id)
            self.assertEqual(record["adapter"], "arxiv")
            self.assertEqual(record["canonical_id"], "hep-th/9711200")
            self.assertIn("text", record)
            self.assertEqual(record["access"], "public")
            self.assertEqual(ingest_paths([output], access="public")[0].source_id, documents[0].source_id)


if __name__ == "__main__":
    unittest.main()
