import json
import tempfile
import unittest
from pathlib import Path

from everyone_is_skill.packaging import scaffold_profile
from everyone_is_skill.release import validate_profile
from everyone_is_skill.versioning import diff_profile, rollback_profile, update_profile_claim


class ProfileVersioningTests(unittest.TestCase):
    def make_profile(self, root: str) -> Path:
        profile = scaffold_profile(Path(root), "example-scientist", "Example Scientist", "scientist")
        manifest_path = profile / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.update(
            {
                "profile_version": "1.2.3",
                "status": "peer-reviewed",
                "identity_anchors": [{"type": "homepage", "value": "https://example.test"}],
                "peer_review": {
                    "independent": True,
                    "reviewer": "reviewer",
                    "reviewed_at": "2026-09-02",
                    "scope": "profile",
                },
            }
        )
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (profile / "provenance.yaml").write_text(
            "schema_version: '1.0'\nprofile_version: '1.2.3'\n"
            "source_snapshot: 'old'\nreview_status: peer-reviewed\n",
            encoding="utf-8",
        )
        (profile / "peer-review.md").write_text("# Prior review\n", encoding="utf-8")
        return profile

    def test_update_snapshots_then_invalidates_review_and_evaluations(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self.make_profile(tmp)
            source = {
                "source_id": "source-1",
                "source_type": "paper",
                "title": "A source",
                "authors": ["Example Scientist"],
                "published_at": "2026",
                "url": "https://example.test/paper",
                "access": "public",
                "rights_basis": "fixture",
            }
            claim = {
                "claim_id": "claim-1",
                "subject": "example-scientist",
                "facet": "method",
                "claim": "Use a controlled comparison.",
                "status": "observed-pattern",
                "confidence": 0.5,
                "source_ids": ["source-1"],
                "attribution_strength": "weak",
                "coauthor_risk": "unknown",
                "time_window": "2026",
            }

            result = update_profile_claim(
                profile,
                source=source,
                claim=claim,
                reason="add a newly reviewed paper",
                updated_at="2026-09-02T00:00:00+00:00",
            )

            self.assertEqual(result["previous_version"], "1.2.3")
            self.assertEqual(result["profile_version"], "1.2.4")
            snapshot = profile / "history" / result["snapshot_id"]
            self.assertTrue((snapshot / "snapshot.json").is_file())
            old_manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(old_manifest["status"], "peer-reviewed")
            current = json.loads((profile / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(current["status"], "evidence-complete")
            self.assertNotIn("peer_review", current)
            self.assertFalse((profile / "peer-review.md").exists())
            self.assertTrue((snapshot / "peer-review.md").is_file())
            self.assertIn("claim-1", (profile / "evidence" / "claims.jsonl").read_text(encoding="utf-8"))
            lineage = json.loads((profile / "evidence" / "lineage.json").read_text(encoding="utf-8"))
            self.assertIn("source-1", {node["id"] for node in lineage["nodes"]})
            for evaluation in (profile / "evals").glob("*.json"):
                self.assertEqual(json.loads(evaluation.read_text(encoding="utf-8"))["status"], "not-run")
            history = [json.loads(line) for line in (profile / "history.jsonl").read_text().splitlines()]
            self.assertEqual(history[-1]["action"], "update-claim")
            self.assertEqual(validate_profile(profile), [])
            difference = diff_profile(profile, result["snapshot_id"])
            self.assertIn("manifest.json", difference["changed"])
            self.assertIn("evidence/claims.jsonl", difference["changed"])

    def test_rollback_preserves_current_state_before_restoring_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self.make_profile(tmp)
            source = {
                "source_id": "source-1",
                "source_type": "paper",
                "title": "A source",
                "authors": ["Example Scientist"],
                "published_at": "2026",
                "url": "https://example.test/paper",
                "access": "public",
                "rights_basis": "fixture",
            }
            claim = {
                "claim_id": "claim-1",
                "subject": "example-scientist",
                "facet": "method",
                "claim": "Use a controlled comparison.",
                "status": "observed-pattern",
                "confidence": 0.5,
                "source_ids": ["source-1"],
                "attribution_strength": "weak",
                "coauthor_risk": "unknown",
                "time_window": "2026",
            }
            updated = update_profile_claim(
                profile,
                source=source,
                claim=claim,
                reason="update",
                updated_at="2026-09-02T00:00:00+00:00",
            )

            rolled_back = rollback_profile(
                profile,
                updated["snapshot_id"],
                reason="restore reviewed state",
                rolled_back_at="2026-09-02T01:00:00+00:00",
            )

            manifest = json.loads((profile / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["profile_version"], "1.2.3")
            self.assertEqual(manifest["status"], "peer-reviewed")
            self.assertEqual((profile / "evidence" / "claims.jsonl").read_text(encoding="utf-8"), "")
            self.assertTrue((profile / "peer-review.md").is_file())
            self.assertTrue((profile / "history" / rolled_back["safety_snapshot_id"]).is_dir())

    def test_rollback_rejects_tampered_snapshot_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self.make_profile(tmp)
            from everyone_is_skill.versioning import snapshot_profile

            snapshot = snapshot_profile(
                profile, reason="security fixture", created_at="2026-09-02T00:00:00+00:00"
            )
            metadata_path = profile / "history" / snapshot["snapshot_id"] / "snapshot.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["files"]["../../outside.txt"] = "0" * 64
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unapproved snapshot file path"):
                rollback_profile(
                    profile,
                    snapshot["snapshot_id"],
                    reason="must fail",
                    rolled_back_at="2026-09-02T01:00:00+00:00",
                )
            self.assertFalse(Path(tmp, "outside.txt").exists())

    def test_snapshot_rejects_symlinked_history_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self.make_profile(tmp)
            outside = Path(tmp) / "outside"
            outside.mkdir()
            (profile / "history").symlink_to(outside, target_is_directory=True)
            from everyone_is_skill.versioning import snapshot_profile

            with self.assertRaisesRegex(ValueError, "history directory cannot be a symbolic link"):
                snapshot_profile(profile, reason="must fail")


if __name__ == "__main__":
    unittest.main()
