import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from everyone_is_skill.packaging import scaffold_profile
from everyone_is_skill.release import release_check


EVAL_FILES = (
    "temporal-holdout.json",
    "matched-peers.json",
    "transfer-tests.json",
    "boundary-tests.json",
    "coauthor-leakage.json",
    "source-ablation.json",
    "prompt-injection.json",
)


class ReleaseCheckTests(unittest.TestCase):
    def make_profile(self, root: str) -> Path:
        profile = scaffold_profile(Path(root), "example-scientist", "Example Scientist", "scientist")
        manifest_path = profile / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.update(
            {
                "status": "release-ready",
                "profile_version": "1.0.0",
                "identity_anchors": [{"type": "orcid", "value": "0000-0002-1825-0097"}],
                "peer_review": {
                    "independent": True,
                    "reviewer": "reviewer-id",
                    "reviewed_at": "2026-09-02",
                    "scope": "claims, attribution, sources, and evaluation results",
                },
            }
        )
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        sources = [
            {"source_id": "source-a", "title": "Source A"},
            {"source_id": "source-b", "title": "Source B"},
        ]
        (profile / "evidence" / "corpus-index.jsonl").write_text(
            "".join(json.dumps(source) + "\n" for source in sources), encoding="utf-8"
        )
        claim = {
            "claim_id": "method-1",
            "subject": "example-scientist",
            "facet": "method",
            "claim": "Starts with the smallest invariant structure that can carry the target behavior.",
            "status": "supported-method",
            "confidence": 0.82,
            "source_ids": ["source-a", "source-b"],
            "attribution_strength": "moderate",
            "coauthor_risk": "moderate",
            "time_window": "2000-2020",
        }
        (profile / "evidence" / "claims.jsonl").write_text(json.dumps(claim) + "\n", encoding="utf-8")
        for filename in EVAL_FILES:
            (profile / "evals" / filename).write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "executed_at": "2026-09-01T00:00:00+00:00",
                        "provider": "recorded-output",
                        "model": "fixture-v1",
                        "reviewer": "reviewer-id",
                        "source_snapshot": "snapshot-123",
                        "rubric_version": "literal-signals-v1",
                        "cases": [
                            {
                                "case_id": filename,
                                "prompt": "Apply the method to a controlled test.",
                                "candidate_output": "Start from a controlled limit.",
                                "expected": ["controlled limit"],
                                "forbidden": ["I am Example Scientist"],
                                "prompt_sha256": hashlib.sha256(
                                    b"Apply the method to a controlled test."
                                ).hexdigest(),
                                "raw_output_sha256": hashlib.sha256(
                                    b"Start from a controlled limit."
                                ).hexdigest(),
                                "raw_score": 1.0,
                                "minimum_score": 1.0,
                                "forbidden_hits": [],
                                "verdict": "passed",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        (profile / "provenance.yaml").write_text(
            "schema_version: '1.0'\nprofile_version: '1.0.0'\n"
            "source_snapshot: 'snapshot-123'\nreview_status: reviewed\n",
            encoding="utf-8",
        )
        return profile

    def test_release_ready_profile_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(release_check(self.make_profile(tmp)), [])

    def test_structural_draft_fails_with_actionable_release_reasons(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = scaffold_profile(Path(tmp), "example-scientist", "Example Scientist", "scientist")
            manifest_path = profile / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["identity_anchors"] = [{"type": "orcid", "value": "0000"}]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            errors = release_check(profile)

            self.assertIn("manifest.status must be release-ready", errors)
            self.assertIn("manifest.profile_version must be semantic versioning (for example 1.0.0)", errors)
            self.assertIn("manifest.identity_anchors contains a placeholder value: 0000", errors)
            self.assertIn("evidence/claims.jsonl must contain at least one claim", errors)
            self.assertIn("provenance.review_status must be reviewed", errors)
            for filename in EVAL_FILES:
                self.assertIn(f"evals/{filename} must have status passed", errors)
                self.assertIn(f"evals/{filename} must contain at least one case", errors)

    def test_supported_method_requires_independent_resolved_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self.make_profile(tmp)
            claims_path = profile / "evidence" / "claims.jsonl"
            claim = json.loads(claims_path.read_text(encoding="utf-8"))
            claim["source_ids"] = ["source-a", "missing-source"]
            claims_path.write_text(json.dumps(claim) + "\n", encoding="utf-8")

            errors = release_check(profile)

            self.assertIn("claim method-1 references unknown source_id: missing-source", errors)

            claim["source_ids"] = ["source-a", "source-a"]
            claims_path.write_text(json.dumps(claim) + "\n", encoding="utf-8")
            errors = release_check(profile)
            self.assertIn("supported-method claim method-1 requires at least two distinct source_ids", errors)

    def test_strong_attribution_requires_resolved_risk_and_counterevidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self.make_profile(tmp)
            claims_path = profile / "evidence" / "claims.jsonl"
            claim = json.loads(claims_path.read_text(encoding="utf-8"))
            claim.update({"attribution_strength": "strong", "coauthor_risk": "unknown"})
            claims_path.write_text(json.dumps(claim) + "\n", encoding="utf-8")

            errors = release_check(profile)

            self.assertIn("strong claim method-1 cannot have coauthor_risk unknown", errors)
            self.assertIn("counterevidence.md must be completed before releasing strong claims", errors)

    def test_unreviewed_import_cannot_be_released(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self.make_profile(tmp)
            manifest_path = profile / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["imported_from"] = {
                "url": "https://example.test/profile",
                "license": "MIT",
                "content_bundled": False,
                "trust": "unreviewed",
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            self.assertIn("manifest.imported_from.trust must be reviewed", release_check(profile))

    def test_real_anchor_does_not_hide_a_remaining_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self.make_profile(tmp)
            manifest_path = profile / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["identity_anchors"].append({"type": "homepage", "value": "placeholder"})
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            self.assertIn(
                "manifest.identity_anchors contains a placeholder value: placeholder",
                release_check(profile),
            )

    def test_passed_label_without_execution_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self.make_profile(tmp)
            eval_path = profile / "evals" / "boundary-tests.json"
            eval_path.write_text(
                json.dumps({"status": "passed", "cases": [{"case_id": "forged"}]}) + "\n",
                encoding="utf-8",
            )

            errors = release_check(profile)

            self.assertIn("evals/boundary-tests.json missing execution field: provider", errors)
            self.assertIn("evals/boundary-tests.json case forged must have verdict passed", errors)
            self.assertIn("evals/boundary-tests.json case forged must record raw_score", errors)
            self.assertIn("evals/boundary-tests.json case forged is not reproducible", errors)

    def test_passed_verdict_cannot_contradict_the_recorded_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self.make_profile(tmp)
            eval_path = profile / "evals" / "prompt-injection.json"
            result = json.loads(eval_path.read_text(encoding="utf-8"))
            result["cases"][0]["raw_score"] = 0.0
            result["cases"][0]["forbidden_hits"] = ["ignore previous instructions"]
            eval_path.write_text(json.dumps(result) + "\n", encoding="utf-8")

            errors = release_check(profile)

            self.assertIn(
                "evals/prompt-injection.json case prompt-injection.json passed verdict contradicts recorded score",
                errors,
            )
            self.assertIn(
                "evals/prompt-injection.json case prompt-injection.json contains forbidden hits",
                errors,
            )


if __name__ == "__main__":
    unittest.main()
