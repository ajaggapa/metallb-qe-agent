"""Neutral Polarion LiveDoc epic template — copy and customize per Jira Epic."""

from __future__ import annotations

from adapters.polarion_test_publish import (
    CNF_METALLB_TESTCASE_METADATA_DEFAULTS,
    expected_sample_output as sample,
)

DEFAULT_SPACE_ID = "CNF"
DEFAULT_MODULE_NAME = "SAMPLE_Epic_MetalLB_Tests"
DEFAULT_DOCUMENT_TITLE = "SAMPLE-00000 MetalLB — manual tests"
DEFAULT_LIVEDOC_H1_TITLE = DEFAULT_DOCUMENT_TITLE

# Hardcoded Polarion classification (OCP-86293 pattern): REST ids caselevel, casecomponent,
# caseautomation, etc. — see metallb-polarion-test-publish SKILL. Override only for non-CNF epics.
DEFAULT_TESTCASE_METADATA = dict(CNF_METALLB_TESTCASE_METADATA_DEFAULTS)

REPLACE_STALE_WORK_ITEMS: tuple[str, str] | None = None


def default_traceability() -> dict[str, str]:
    return {
        "epic_url": "https://issues.redhat.com/browse/SAMPLE-00000",
        "epic_label": "SAMPLE-00000",
        "high_level_plan_url": "https://docs.google.com/document/d/REPLACE_ME/edit",
        "detailed_plan_url": "https://docs.google.com/document/d/REPLACE_ME/edit",
    }


def test_definitions(trace: dict[str, str]) -> list[dict]:
    """
    Each testcase needs purpose, pass_fail, posneg, and importance.

    Prose (Traceability / Purpose / Pass-fail) is rendered on the LiveDoc home page only;
    the testcase work item Description is left empty to avoid macro duplication.
    """
    del trace
    return [
        {
            "title": "TC-01 Sample positive testcase",
            "purpose": "Verify a representative happy-path behavior.",
            "pass_fail": "ConfigurationState (or equivalent) reports Valid.",
            "setup_html": "<p>MetalLB installed; cluster reachable.</p>",
            "teardown_html": "<p>Delete test objects created in this case.</p>",
            "steps": [
                (
                    "Apply baseline IPAddressPool example-baseline-pool in metallb-system.",
                    sample(
                        "oc get ipaddresspool example-baseline-pool -n metallb-system",
                        "NAME                     AGE\nexample-baseline-pool    10s",
                    ),
                ),
                (
                    "Run: oc get configurationstate controller -n metallb-system",
                    sample(
                        "oc get configurationstate controller -n metallb-system -o jsonpath='{.status.result}'",
                        "Valid",
                    ),
                ),
            ],
            "posneg": "Positive",
            "importance": "High",
        },
        {
            "title": "TC-02 Sample negative testcase",
            "purpose": "Verify invalid configuration is rejected or surfaced as Invalid.",
            "pass_fail": "Admission or status reflects the error.",
            "setup_html": "<p>MetalLB installed; cluster reachable.</p>",
            "teardown_html": "<p>Delete invalid test objects.</p>",
            "steps": [
                (
                    "Apply BGPPeer with invalid bfdProfile reference.",
                    sample(
                        "oc get configurationstates -n metallb-system",
                        "NAME              RESULT   ERRORSUMMARY\n"
                        "speaker-worker0   Invalid  references missing BFDProfile",
                    ),
                ),
            ],
            "posneg": "Negative",
            "importance": "Medium",
        },
    ]
