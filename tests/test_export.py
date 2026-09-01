import json
import tempfile
import unittest
from pathlib import Path

from everyone_is_skill.exporting import RUNTIMES, export_profile
from everyone_is_skill.evaluation import EVALUATION_SUITES
from everyone_is_skill.packaging import scaffold_profile
from everyone_is_skill.release import REQUIRED_PROFILE_FILES, validate_profile


class RuntimeExportTests(unittest.TestCase):
    def test_portable_profile_exports_without_history_or_contract_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = scaffold_profile(root / "source", "example-scientist", "Example Scientist", "scientist")
            manifest_path = profile / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["identity_anchors"] = [{"type": "homepage", "value": "https://example.test"}]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            (profile / "history").mkdir()
            (profile / "history" / "private-snapshot.txt").write_text("not exported", encoding="utf-8")

            for runtime in RUNTIMES:
                with self.subTest(runtime=runtime):
                    exported = export_profile(profile, root / "exports", runtime=runtime)
                    self.assertEqual(validate_profile(exported), [])
                    self.assertTrue(REQUIRED_PROFILE_FILES <= {str(path.relative_to(exported)) for path in exported.rglob("*") if path.is_file()})
                    self.assertFalse((exported / "history").exists())
                    self.assertTrue(all((exported / "evals" / f"{suite}.json").is_file() for suite in EVALUATION_SUITES))
                    metadata = json.loads((exported / "runtime.json").read_text(encoding="utf-8"))
                    self.assertEqual(metadata["runtime"], runtime)
                    self.assertFalse(metadata["contract_modified"])
                    if runtime == "agents-md":
                        self.assertTrue((exported / "AGENTS.md").is_file())
                        self.assertIn("not an impersonation", (exported / "AGENTS.md").read_text(encoding="utf-8").lower())

    def test_export_rejects_symlinked_optional_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = scaffold_profile(root / "source", "example-scientist", "Example Scientist", "scientist")
            manifest_path = profile / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["identity_anchors"] = [{"type": "homepage", "value": "https://example.test"}]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            outside = root / "outside.txt"
            outside.write_text("private review material", encoding="utf-8")
            (profile / "peer-review.md").symlink_to(outside)

            with self.assertRaisesRegex(ValueError, "peer-review.md"):
                export_profile(profile, root / "exports", runtime="codex")

    def test_export_rejects_symlinked_destination_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = scaffold_profile(root / "source", "example-scientist", "Example Scientist", "scientist")
            manifest_path = profile / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["identity_anchors"] = [{"type": "homepage", "value": "https://example.test"}]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            outside = root / "outside"
            outside.mkdir()
            export_root = root / "exports"
            export_root.symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "destination path contains a symbolic link"):
                export_profile(profile, export_root, runtime="codex")


if __name__ == "__main__":
    unittest.main()
