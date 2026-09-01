import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "everyone_is_skill.cli", *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_new_profile_then_validate(self):
        with tempfile.TemporaryDirectory() as tmp:
            created = self.run_cli(
                "new-profile",
                "--output",
                tmp,
                "--slug",
                "alexei-kitaev",
                "--name",
                "Alexei Kitaev",
                "--kind",
                "scientist",
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            profile = Path(tmp) / "alexei-kitaev"

            manifest_path = profile / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["identity_anchors"] = [{"type": "orcid", "value": "0000"}]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            validated = self.run_cli("validate", str(profile))
            self.assertEqual(validated.returncode, 0, validated.stderr)
            self.assertIn("valid", validated.stdout.lower())

    def test_validate_reports_ungrounded_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            created = self.run_cli(
                "new-profile",
                "--output",
                tmp,
                "--slug",
                "alexei-kitaev",
                "--name",
                "Alexei Kitaev",
                "--kind",
                "scientist",
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            profile = Path(tmp) / "alexei-kitaev"
            manifest_path = profile / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["identity_anchors"] = [{"type": "orcid", "value": "0000"}]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            (profile / "evidence" / "claims.jsonl").write_text(
                json.dumps(
                    {
                        "claim_id": "bad",
                        "subject": "alexei-kitaev",
                        "facet": "method",
                        "claim": "Unsupported claim",
                        "status": "supported-method",
                        "confidence": 0.9,
                        "source_ids": [],
                        "attribution_strength": "strong",
                        "coauthor_risk": "low",
                        "time_window": "unknown",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            validated = self.run_cli("validate", str(profile))
            self.assertEqual(validated.returncode, 1)
            self.assertIn("source_ids", validated.stderr)

    def test_validate_rejects_missing_evaluation_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            created = self.run_cli(
                "new-profile",
                "--output",
                tmp,
                "--slug",
                "alexei-kitaev",
                "--name",
                "Alexei Kitaev",
                "--kind",
                "scientist",
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            profile = Path(tmp) / "alexei-kitaev"
            manifest_path = profile / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["identity_anchors"] = [{"type": "orcid", "value": "0000"}]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            (profile / "evals" / "boundary-tests.json").unlink()

            validated = self.run_cli("validate", str(profile))
            self.assertEqual(validated.returncode, 1)
            self.assertIn("evals/boundary-tests.json", validated.stderr)

    def test_validate_repository_command(self):
        result = self.run_cli("validate-repo", ".")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("repository is valid", result.stdout.lower())

    def test_release_check_fails_closed_for_a_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            created = self.run_cli(
                "new-profile",
                "--output",
                tmp,
                "--slug",
                "example-scientist",
                "--name",
                "Example Scientist",
                "--kind",
                "scientist",
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            checked = self.run_cli("release-check", str(Path(tmp) / "example-scientist"))
            self.assertEqual(checked.returncode, 1)
            self.assertIn("manifest.status must be release-ready", checked.stderr)

    def test_release_check_command_reports_release_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            created = self.run_cli(
                "new-profile",
                "--output",
                tmp,
                "--slug",
                "alexei-kitaev",
                "--name",
                "Alexei Kitaev",
                "--kind",
                "scientist",
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            profile = Path(tmp) / "alexei-kitaev"

            manifest_path = profile / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["identity_anchors"] = [{"type": "orcid", "value": "0000-0000-0000-0000"}]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            checked = self.run_cli("release-check", str(profile))
            self.assertEqual(checked.returncode, 1)
            self.assertIn("status must be release-ready", checked.stderr)
            self.assertIn("evidence/claims.jsonl must contain at least one claim", checked.stderr)

    def test_import_reference_records_upstream_without_copying_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(
                "import-reference",
                "--output",
                tmp,
                "--slug",
                "example-researcher",
                "--name",
                "Example Researcher",
                "--kind",
                "scientist",
                "--upstream-url",
                "https://github.com/example/profile",
                "--upstream-license",
                "MIT",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            profile = Path(tmp) / "example-researcher"
            manifest = json.loads((profile / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["identity_anchors"],
                [{"type": "upstream-profile", "value": "https://github.com/example/profile"}],
            )
            self.assertEqual(manifest["imported_from"]["license"], "MIT")
            self.assertFalse((profile / "upstream-SKILL.md").exists())
            validated = self.run_cli("validate", str(profile))
            self.assertEqual(validated.returncode, 0, validated.stderr)


if __name__ == "__main__":
    unittest.main()
