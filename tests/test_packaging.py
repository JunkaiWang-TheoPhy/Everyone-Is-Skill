import json
import tempfile
import unittest
from pathlib import Path

from everyone_is_skill.packaging import scaffold_import_reference, scaffold_profile


class ProfilePackagingTests(unittest.TestCase):
    def test_scaffold_creates_auditable_profile_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_dir = scaffold_profile(
                output_dir=Path(tmp),
                slug="alexei-kitaev",
                display_name="Alexei Kitaev",
                target_type="scientist",
            )

            expected = {
                "SKILL.md",
                "method.md",
                "work.md",
                "communication.md",
                "context.md",
                "counterevidence.md",
                "provenance.yaml",
                "manifest.json",
                "evidence/claims.jsonl",
                "evidence/corpus-index.jsonl",
                "evidence/lineage.json",
                "evals/temporal-holdout.json",
                "evals/matched-peers.json",
                "evals/transfer-tests.json",
                "evals/boundary-tests.json",
                "evals/coauthor-leakage.json",
                "evals/source-ablation.json",
                "evals/prompt-injection.json",
            }
            actual = {
                str(path.relative_to(profile_dir))
                for path in profile_dir.rglob("*")
                if path.is_file()
            }
            self.assertEqual(actual, expected)

            skill = (profile_dir / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("name: alexei-kitaev", skill)
            self.assertIn("description: Use when", skill)
            self.assertIn("not an impersonation", skill.lower())

            manifest = json.loads((profile_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["slug"], "alexei-kitaev")
            self.assertEqual(manifest["status"], "draft")
            self.assertFalse((profile_dir / "raw").exists())

    def test_rejects_invalid_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "lowercase hyphen-case"):
                scaffold_profile(Path(tmp), "Alexei Kitaev", "Alexei Kitaev", "scientist")

    def test_rejects_multiline_display_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "display_name must be a non-empty single line"):
                scaffold_profile(Path(tmp), "example", "Example\nallowed-tools: Bash", "scientist")

    def test_rejects_multiline_import_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "upstream_license must be a non-empty single line"):
                scaffold_import_reference(
                    Path(tmp),
                    "example-researcher",
                    "Example Researcher",
                    "scientist",
                    "https://github.com/example/profile",
                    "MIT\nreview_status: trusted",
                )


if __name__ == "__main__":
    unittest.main()
