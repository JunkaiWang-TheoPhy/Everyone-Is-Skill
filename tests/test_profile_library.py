import json
import unittest
from pathlib import Path

from everyone_is_skill.evaluation import EVALUATION_SUITES
from everyone_is_skill.release import check_release_readiness, validate_profile


SCIENTIST_SLUGS = {
    "alexei-kitaev",
    "shing-tung-yau",
    "xiao-gang-wen",
    "juan-maldacena",
    "nima-arkani-hamed",
    "chen-ning-yang",
    "nathan-seiberg",
    "nikita-nekrasov",
    "warren-siegel",
}
EVIDENCE_COMPLETE_STATUSES = {"evidence-complete", "behavior-tested", "peer-reviewed", "release-ready"}


class ProfileLibraryTests(unittest.TestCase):
    def setUp(self):
        self.examples = Path("profiles/examples")

    def test_nine_scientist_profiles_are_evidence_complete(self):
        actual = {path.name for path in self.examples.iterdir() if path.is_dir()}
        self.assertEqual(actual, SCIENTIST_SLUGS)
        for slug in sorted(SCIENTIST_SLUGS):
            with self.subTest(slug=slug):
                profile = self.examples / slug
                self.assertEqual(validate_profile(profile), [])
                manifest = json.loads((profile / "manifest.json").read_text(encoding="utf-8"))
                self.assertIn(manifest["status"], EVIDENCE_COMPLETE_STATUSES)
                self.assertTrue(manifest["identity_anchors"])
                claims = [
                    json.loads(line)
                    for line in (profile / "evidence" / "claims.jsonl").read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                supported = [claim for claim in claims if claim["status"] == "supported-method"]
                self.assertGreaterEqual(len(supported), 3)
                corpus = [
                    json.loads(line)
                    for line in (profile / "evidence" / "corpus-index.jsonl").read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                self.assertGreaterEqual(len(corpus), 4)
                source_ids = {source["source_id"] for source in corpus}
                self.assertTrue(all(str(source.get("url", "")).startswith("https://") for source in corpus))
                for source in corpus:
                    self.assertIn(source.get("source_type"), {"paper", "preprint", "talk", "interview", "lecture", "book", "blog", "review", "notes", "other"})
                    self.assertTrue(source.get("title"))
                    self.assertIsInstance(source.get("authors"), list)
                    self.assertTrue(source.get("published_at"))
                    self.assertIn(source.get("access"), {"public", "authorized", "private-reference"})
                    self.assertTrue(source.get("rights_basis"))
                for claim in supported:
                    self.assertGreaterEqual(len(set(claim["source_ids"])), 2)
                    self.assertTrue(set(claim["source_ids"]) <= source_ids)
                    cited = [source for source in corpus if source["source_id"] in claim["source_ids"]]
                    self.assertTrue(any(source["source_type"] in {"paper", "preprint", "talk", "interview", "lecture", "book"} for source in cited))
                counterevidence = (profile / "counterevidence.md").read_text(encoding="utf-8")
                self.assertGreater(len(counterevidence), 180)
                for suite in EVALUATION_SUITES:
                    self.assertTrue((profile / "evals" / f"{suite}.json").is_file())

    def test_three_profiles_include_executed_peer_reviewed_evaluations(self):
        reviewed = []
        for slug in sorted(SCIENTIST_SLUGS):
            profile = self.examples / slug
            manifest = json.loads((profile / "manifest.json").read_text(encoding="utf-8"))
            results = [
                json.loads((profile / "evals" / f"{suite}.json").read_text(encoding="utf-8"))
                for suite in EVALUATION_SUITES
            ]
            if manifest["status"] == "peer-reviewed" and all(result.get("status") == "passed" for result in results):
                reviewed.append(slug)
                peer_review = manifest.get("peer_review", {})
                self.assertTrue(peer_review.get("independent"))
                self.assertTrue(peer_review.get("reviewer"))
                self.assertTrue(peer_review.get("reviewed_at"))
                self.assertTrue(peer_review.get("scope"))
                self.assertTrue(all(result.get("reviewer") and result.get("reviewer") != "library-reviewer" for result in results))
                for result in results:
                    for case in result["cases"]:
                        self.assertTrue(case.get("prompt"))
                        self.assertIsInstance(case.get("candidate_output"), str)
                        self.assertIsInstance(case.get("expected"), list)
                        self.assertIsInstance(case.get("forbidden"), list)
        self.assertGreaterEqual(len(reviewed), 3)
        self.assertIn("alexei-kitaev", reviewed)
        self.assertIn("shing-tung-yau", reviewed)

    def test_release_ready_status_means_the_executable_gate_really_passes(self):
        for slug in sorted(SCIENTIST_SLUGS):
            profile = self.examples / slug
            manifest = json.loads((profile / "manifest.json").read_text(encoding="utf-8"))
            if manifest["status"] == "release-ready":
                self.assertEqual(check_release_readiness(profile), [], slug)

    def test_collective_profile_preserves_phases_roles_and_dissent(self):
        profile = Path("profiles/collectives/modern-theoretical-physics-methods")
        self.assertEqual(validate_profile(profile), [])
        manifest = json.loads((profile / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["target_type"], "team")
        self.assertIn(manifest["status"], EVIDENCE_COMPLETE_STATUSES)
        self.assertGreaterEqual(len(manifest["historical_phases"]), 3)
        self.assertGreaterEqual(len(manifest["roles"]), 3)
        self.assertTrue(manifest["dissent_policy"])
        method = (profile / "method.md").read_text(encoding="utf-8").lower()
        self.assertIn("disagreement", method)
        self.assertIn("minority", method)


if __name__ == "__main__":
    unittest.main()
