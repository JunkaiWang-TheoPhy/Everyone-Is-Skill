import json
import unittest
from pathlib import Path

from everyone_is_skill.repository import validate_repository


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_repository_has_required_legal_and_governance_files(self):
        for relative in (
            "LICENSE",
            "NOTICE",
            "THIRD_PARTY_NOTICES.md",
            "ACKNOWLEDGEMENTS.md",
            "CITATION.cff",
            "SECURITY.md",
            "CONTRIBUTING.md",
            "CODE_OF_CONDUCT.md",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_all_json_files_parse(self):
        for path in ROOT.rglob("*.json"):
            if ".git" in path.parts:
                continue
            with self.subTest(path=path):
                json.loads(path.read_text(encoding="utf-8"))

    def test_repository_validator_reports_no_errors(self):
        self.assertEqual(validate_repository(ROOT), [])

    def test_plugin_packages_shared_docs_and_schemas(self):
        plugin = ROOT / "plugins" / "everyone-is-skill"
        for filename in ("architecture.md", "evidence-policy.md", "profile-contract.md", "evaluation.md"):
            self.assertEqual(
                (ROOT / "docs" / filename).read_bytes(),
                (plugin / "references" / filename).read_bytes(),
                filename,
            )
        for source in (ROOT / "schemas").glob("*.json"):
            self.assertEqual(source.read_bytes(), (plugin / "schemas" / source.name).read_bytes(), source.name)

    def test_repository_validator_rejects_invalid_skill_frontmatter(self):
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp) / "repo"
            shutil.copytree(ROOT, checkout, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info"))
            skill = checkout / "plugins" / "everyone-is-skill" / "skills" / "everyone-is-skill" / "SKILL.md"
            skill.write_text("not valid skill frontmatter\n", encoding="utf-8")
            errors = validate_repository(checkout)
            self.assertTrue(any("invalid skill" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
