import unittest

from everyone_is_skill.contracts import validate_claim, validate_profile_manifest


class ClaimContractTests(unittest.TestCase):
    def setUp(self):
        self.claim = {
            "claim_id": "kitaev-model-001",
            "subject": "alexei-kitaev",
            "facet": "model-construction",
            "claim": "Uses minimal models to expose structurally protected behavior.",
            "status": "person-specific-candidate",
            "confidence": 0.8,
            "source_ids": ["quant-ph/9707021", "cond-mat/0506438"],
            "attribution_strength": "moderate",
            "coauthor_risk": "low",
            "time_window": "1997-2006",
        }

    def test_accepts_grounded_claim(self):
        self.assertEqual(validate_claim(self.claim), [])

    def test_rejects_claim_without_sources(self):
        self.claim["source_ids"] = []
        self.assertIn("source_ids must contain at least one source", validate_claim(self.claim))

    def test_rejects_out_of_range_confidence(self):
        self.claim["confidence"] = 1.4
        self.assertIn("confidence must be between 0 and 1", validate_claim(self.claim))

    def test_rejects_unknown_status(self):
        self.claim["status"] = "definitely-this-person"
        errors = validate_claim(self.claim)
        self.assertTrue(any("status must be one of" in error for error in errors))


class ProfileManifestContractTests(unittest.TestCase):
    def test_requires_bounded_use_and_identity_anchor(self):
        manifest = {
            "schema_version": "1.0",
            "slug": "alexei-kitaev",
            "display_name": "Alexei Kitaev",
            "target_type": "scientist",
            "intended_use": "Research-method reconstruction",
            "identity_anchors": [],
            "boundaries": [],
        }
        errors = validate_profile_manifest(manifest)
        self.assertIn("identity_anchors must contain at least one anchor", errors)
        self.assertIn("boundaries must contain at least one boundary", errors)

    def test_accepts_minimal_valid_manifest(self):
        manifest = {
            "schema_version": "1.0",
            "slug": "alexei-kitaev",
            "display_name": "Alexei Kitaev",
            "target_type": "scientist",
            "intended_use": "Research-method reconstruction",
            "identity_anchors": [{"type": "orcid", "value": "0000-0000-0000-0000"}],
            "boundaries": ["Not an impersonation or source of private mental states."],
        }
        self.assertEqual(validate_profile_manifest(manifest), [])

    def test_rejects_malformed_identity_anchor_and_boundary(self):
        manifest = {
            "schema_version": "1.0",
            "slug": "alexei-kitaev",
            "display_name": "Alexei Kitaev",
            "target_type": "scientist",
            "intended_use": "Research-method reconstruction",
            "identity_anchors": [{"type": "orcid"}],
            "boundaries": [""],
        }
        errors = validate_profile_manifest(manifest)
        self.assertIn("identity_anchors entries must contain non-empty type and value", errors)
        self.assertIn("boundaries entries must be non-empty strings", errors)

    def test_peer_reviewed_status_requires_independent_review_metadata(self):
        manifest = {
            "schema_version": "1.0",
            "slug": "alexei-kitaev",
            "display_name": "Alexei Kitaev",
            "target_type": "scientist",
            "status": "peer-reviewed",
            "intended_use": "Research-method reconstruction",
            "identity_anchors": [{"type": "homepage", "value": "https://example.test"}],
            "boundaries": ["Not an impersonation."],
            "peer_review": {"independent": False, "reviewer": "", "reviewed_at": "", "scope": ""},
        }
        errors = validate_profile_manifest(manifest)
        self.assertIn("peer_review must record an independent reviewer, date, and scope", errors)

    def test_rejects_unknown_profile_status(self):
        manifest = {
            "schema_version": "1.0",
            "slug": "alexei-kitaev",
            "display_name": "Alexei Kitaev",
            "target_type": "scientist",
            "status": "celebrity-simulation",
            "intended_use": "Research-method reconstruction",
            "identity_anchors": [{"type": "homepage", "value": "https://example.test"}],
            "boundaries": ["Not an impersonation."],
        }
        self.assertTrue(any("profile status must be one of" in error for error in validate_profile_manifest(manifest)))


if __name__ == "__main__":
    unittest.main()
