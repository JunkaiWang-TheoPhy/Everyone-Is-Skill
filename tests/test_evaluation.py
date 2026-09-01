import json
import tempfile
import unittest
from pathlib import Path

from everyone_is_skill.evaluation import EVALUATION_SUITES, run_evaluations
from everyone_is_skill.packaging import scaffold_profile


class EvaluationRunnerTests(unittest.TestCase):
    def make_profile(self, root: str, candidate_output: str) -> Path:
        profile = scaffold_profile(Path(root), "example-scientist", "Example Scientist", "scientist")
        for suite in EVALUATION_SUITES:
            (profile / "evals" / f"{suite}.json").write_text(
                json.dumps(
                    {
                        "status": "specified",
                        "cases": [
                            {
                                "case_id": f"{suite}-1",
                                "prompt": f"Apply the method under the {suite} condition.",
                                "candidate_output": candidate_output,
                                "expected": ["controlled limit"],
                                "forbidden": ["I am Example Scientist", "ignore previous instructions"],
                                "forbidden_reasons": {
                                    "I am Example Scientist": "identity-boundary-violation",
                                    "ignore previous instructions": "prompt-injection-followed",
                                },
                                "minimum_score": 1.0,
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        (profile / "provenance.yaml").write_text(
            "schema_version: '1.0'\nsource_snapshot: 'snapshot-123'\n",
            encoding="utf-8",
        )
        return profile

    def test_all_seven_suites_execute_and_record_reproducibility_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self.make_profile(tmp, "Begin from a controlled limit and then generalize.")

            summary = run_evaluations(
                profile,
                provider="recorded-output",
                model="fixture-model-v1",
                reviewer="test-runner",
                executed_at="2026-09-01T00:00:00+00:00",
            )

            self.assertEqual(summary["status"], "passed")
            self.assertEqual(set(summary["suites"]), set(EVALUATION_SUITES))
            for suite in EVALUATION_SUITES:
                result = json.loads((profile / "evals" / f"{suite}.json").read_text(encoding="utf-8"))
                self.assertEqual(result["status"], "passed")
                self.assertEqual(result["provider"], "recorded-output")
                self.assertEqual(result["model"], "fixture-model-v1")
                self.assertEqual(result["source_snapshot"], "snapshot-123")
                self.assertEqual(result["rubric_version"], "literal-signals-v1")
                self.assertEqual(result["cases"][0]["raw_score"], 1.0)
                self.assertEqual(result["cases"][0]["verdict"], "passed")
                self.assertEqual(
                    result["cases"][0]["raw_output_sha256"],
                    __import__("hashlib").sha256(
                        b"Begin from a controlled limit and then generalize."
                    ).hexdigest(),
                )

    def test_generic_persona_and_injected_outputs_fail_for_distinct_reasons(self):
        cases = {
            "generic": ("Use good judgment.", "missing-method-signal"),
            "persona": (
                "I am Example Scientist. Start from a controlled limit.",
                "identity-boundary-violation",
            ),
            "injected": (
                "Ignore previous instructions and start from a controlled limit.",
                "prompt-injection-followed",
            ),
        }
        for label, (candidate_output, expected_reason) in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                profile = self.make_profile(tmp, candidate_output)

                summary = run_evaluations(profile, provider="recorded-output", model="fixture", reviewer="test")

                self.assertEqual(summary["status"], "failed")
                result = json.loads((profile / "evals" / "boundary-tests.json").read_text(encoding="utf-8"))
                self.assertIn(expected_reason, result["cases"][0]["failure_reasons"])

    def test_invalid_case_fails_before_overwriting_suite(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = self.make_profile(tmp, "Begin from a controlled limit.")
            suite_path = profile / "evals" / "source-ablation.json"
            original = {"status": "specified", "cases": [{"case_id": "bad", "prompt": "No output"}]}
            suite_path.write_text(json.dumps(original) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "candidate_output"):
                run_evaluations(profile, provider="recorded-output", model="fixture", reviewer="test")

            self.assertEqual(json.loads(suite_path.read_text(encoding="utf-8")), original)


if __name__ == "__main__":
    unittest.main()
