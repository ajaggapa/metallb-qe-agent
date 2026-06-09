"""Unit tests for Polarion testcase metadata defaults and resolution."""

from __future__ import annotations

import unittest

from adapters.polarion_test_publish import (
    build_testcase_metadata,
    expected_sample_output,
    resolve_testcase_metadata,
    validate_testcase_dict,
)


class TestBuildTestcaseMetadata(unittest.TestCase):
    def test_cnf_defaults_and_per_test_fields(self) -> None:
        meta = build_testcase_metadata(posneg="Positive", importance="High")
        self.assertEqual(meta["caselevel"], "component")
        self.assertEqual(meta["casecomponent"], "telco")
        self.assertEqual(meta["subcomponent"], "cnfnetwork")
        self.assertEqual(meta["subteam"], "kni")
        self.assertEqual(meta["products"], ["ocp"])
        self.assertEqual(meta["testtype"], "functional")
        self.assertEqual(meta["caseautomation"], "notautomated")
        self.assertEqual(meta["upstream"], "no")
        self.assertEqual(meta["caseposneg"], "positive")
        self.assertEqual(meta["caseimportance"], "high")
        self.assertEqual(meta["priority"], "70.0")

    def test_resolve_from_testcase_dict(self) -> None:
        tc = {
            "title": "TC-01",
            "posneg": "Negative",
            "importance": "Medium",
        }
        meta = resolve_testcase_metadata(tc)
        self.assertEqual(meta["caseposneg"], "negative")
        self.assertEqual(meta["caseimportance"], "medium")
        self.assertEqual(meta["priority"], "50.0")

    def test_requires_posneg_and_importance(self) -> None:
        with self.assertRaises(ValueError):
            resolve_testcase_metadata({"title": "TC-99"})


class TestValidateTestcaseDict(unittest.TestCase):
    def test_rejects_prose_only_expected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_testcase_dict(
                {
                    "title": "TC-01",
                    "purpose": "p",
                    "pass_fail": "pf",
                    "setup_html": "<p>s</p>",
                    "teardown_html": "<p>t</p>",
                    "steps": [("do thing", "resource should be created")],
                    "posneg": "Positive",
                    "importance": "High",
                }
            )
        self.assertIn("sample output", str(ctx.exception).lower())


class TestExpectedSampleOutput(unittest.TestCase):
    def test_includes_run_prefix_and_sample(self) -> None:
        out = expected_sample_output(
            "oc get pods -n default",
            "NAME   READY   STATUS\npod    1/1     Running",
        )
        self.assertIn("Run: oc get pods -n default", out)
        self.assertIn("Sample output:", out)
        self.assertIn("1/1     Running", out)


if __name__ == "__main__":
    unittest.main()
