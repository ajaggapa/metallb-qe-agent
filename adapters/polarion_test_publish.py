# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for publishing Polarion testcase LiveDocs (traceability HTML, stale WI discovery).

Epic-specific defaults and ``test_definitions`` live in a Python module (any import path on ``PYTHONPATH``)
loaded by ``scripts/publish_polarion_livedoc_tests.py`` (see ``examples/polarion_livedoc_epic_module/sample_epic.py``).
"""

from __future__ import annotations

import html
from typing import Any, Mapping

from adapters.polarion_adapter import PolarionAdapter, html_paragraph, html_section_label

# MetalLB / CNF manual testcase defaults (OCP-86293 / OCP-43738 Polarion field ids).
# UI labels Level, Component, Importance, Pos/Neg, Automation map to case* attributes.
CNF_METALLB_TESTCASE_METADATA_DEFAULTS: dict[str, Any] = {
    "caselevel": "component",
    "casecomponent": "telco",
    "subcomponent": "cnfnetwork",
    "subteam": "kni",
    "products": ["ocp"],
    "testtype": "functional",
    "caseautomation": "notautomated",
    "upstream": "no",
}

_POSNEG_TO_CASE = {"Positive": "positive", "Negative": "negative"}
_IMPORTANCE_TO_CASE = {
    "Critical": "critical",
    "High": "high",
    "Medium": "medium",
    "Low": "low",
}

IMPORTANCE_TO_PRIORITY: dict[str, str] = {
    "Critical": "90.0",
    "High": "70.0",
    "Medium": "50.0",
    "Low": "30.0",
}

_VALID_POSNEG = frozenset({"Positive", "Negative"})
_VALID_IMPORTANCE = frozenset(IMPORTANCE_TO_PRIORITY)

# Optional .env overrides (same for every epic)
_TRACE_ENV = (
    ("POLARION_TRACE_EPIC_URL", "epic_url"),
    ("POLARION_TRACE_EPIC_LABEL", "epic_label"),
    ("POLARION_TRACE_HIGH_LEVEL_PLAN_URL", "high_level_plan_url"),
    ("POLARION_TRACE_DETAILED_PLAN_URL", "detailed_plan_url"),
)


def merge_traceability_from_env(
    base: Mapping[str, str], env: Mapping[str, str]
) -> dict[str, str]:
    """
    Overlay traceability onto ``base`` (from epic module ``default_traceability()``).

    Precedence for each field:

    1. ``POLARION_TRACE_*`` in the merged env (highest).
    2. ``METALLB_*`` convenience keys when the corresponding ``POLARION_TRACE_*`` was **not** set.
    3. Values already in ``base`` (from the epic module).

    ``METALLB_JIRA_EPIC_KEY`` sets ``epic_label`` and, unless ``POLARION_TRACE_EPIC_URL`` is set,
    ``epic_url`` as ``{METALLB_JIRA_BROWSE_URL_BASE}/{key}`` (default browse base is Red Hat issues).
    """
    out = dict(base)
    for env_key, trace_key in _TRACE_ENV:
        v = env.get(env_key, "").strip()
        if v:
            out[trace_key] = v

    epic_key = env.get("METALLB_JIRA_EPIC_KEY", "").strip()
    browse_base = env.get("METALLB_JIRA_BROWSE_URL_BASE", "https://issues.redhat.com/browse").rstrip("/")
    if epic_key:
        if not env.get("POLARION_TRACE_EPIC_LABEL", "").strip():
            out["epic_label"] = epic_key
        if not env.get("POLARION_TRACE_EPIC_URL", "").strip():
            out["epic_url"] = f"{browse_base}/{epic_key}"

    hl = env.get("METALLB_HIGH_LEVEL_PLAN_URL", "").strip()
    if hl and not env.get("POLARION_TRACE_HIGH_LEVEL_PLAN_URL", "").strip():
        out["high_level_plan_url"] = hl

    dl = env.get("METALLB_DETAILED_PLAN_URL", "").strip()
    if dl and not env.get("POLARION_TRACE_DETAILED_PLAN_URL", "").strip():
        out["detailed_plan_url"] = dl

    return out


def apply_traceability_cli(trace: dict[str, str], args: Any) -> dict[str, str]:
    """Argparse overrides for traceability fields when attributes are set."""
    out = dict(trace)
    if getattr(args, "epic_url", None):
        out["epic_url"] = args.epic_url.strip()
    if getattr(args, "epic_label", None):
        out["epic_label"] = args.epic_label.strip()
    if getattr(args, "high_level_plan_url", None):
        out["high_level_plan_url"] = args.high_level_plan_url.strip()
    if getattr(args, "detailed_plan_url", None):
        out["detailed_plan_url"] = args.detailed_plan_url.strip()
    return out


def traceability_ul(trace: Mapping[str, str]) -> str:
    return (
        "<ul>"
        f'<li>Epic: <a href="{html.escape(trace["epic_url"], quote=True)}">'
        f'{html.escape(trace["epic_label"])}</a></li>'
        f'<li>High-level test plan: <a href="{html.escape(trace["high_level_plan_url"], quote=True)}">'
        "Google Doc</a></li>"
        f'<li>Detailed test plan: <a href="{html.escape(trace["detailed_plan_url"], quote=True)}">'
        "Google Doc</a></li>"
        "</ul>"
    )


# WI Description is left empty so the LiveDoc ``module-workitem`` macro does not duplicate
# Traceability / Purpose / Pass-fail that appear on the home page under each test.
TESTCASE_WORKITEM_DESCRIPTION_HTML = ""


def expected_sample_output(verify_command: str, sample: str) -> str:
    """
    Polarion **Expected Result** cell: verification command plus representative terminal output.

    Use in epic ``steps`` tuples so testers see a copy-paste ``oc``/``kubectl`` check and
    sample output, not only prose like "resource should be created".
    """
    cmd = verify_command.strip()
    if not cmd.lower().startswith("run:"):
        cmd = f"Run: {cmd}"
    return f"{cmd}\n\nSample output:\n{sample.strip()}"


def livedoc_purpose_pass_fail_html(purpose: str, pass_fail: str) -> str:
    """Purpose and Pass/fail block for one testcase on the LiveDoc home page."""
    return (
        html_section_label("Purpose", margin_top="1.2em", margin_bottom="0.4em")
        + html_paragraph(purpose)
        + html_section_label("Pass / fail (summary)", margin_top="1em", margin_bottom="0.4em")
        + html_paragraph(pass_fail)
    )


def testcase_description_html(
    trace: Mapping[str, str], purpose: str, pass_fail: str
) -> str:
    """
    Deprecated — do not store Purpose/Pass-fail on the testcase work item Description.

    Epic modules must set ``purpose`` and ``pass_fail`` on each testcase dict for the
    LiveDoc home page. The ``trace`` argument is ignored (kept for call-site compatibility).
    """
    del trace, purpose, pass_fail
    return TESTCASE_WORKITEM_DESCRIPTION_HTML


def resolve_testcase_prose(testcase: Mapping[str, Any]) -> tuple[str, str]:
    """Return (purpose, pass_fail) required for LiveDoc home-page HTML."""
    purpose = str(testcase.get("purpose", "")).strip()
    pass_fail = str(testcase.get("pass_fail", "")).strip()
    if not purpose or not pass_fail:
        title = testcase.get("title", "<untitled>")
        raise ValueError(
            f"Testcase {title!r} must define purpose and pass_fail strings for LiveDoc "
            "(do not rely on description_html for home-page prose)."
        )
    return purpose, pass_fail


def validate_testcase_dict(testcase: Mapping[str, Any]) -> None:
    """Raise if a testcase dict is missing fields required for Polarion publish."""
    resolve_testcase_prose(testcase)
    resolve_testcase_metadata(testcase)
    title = str(testcase.get("title", "<untitled>"))
    for key in ("title", "setup_html", "teardown_html", "steps"):
        if not testcase.get(key):
            raise ValueError(f"Testcase {title!r} missing required key {key!r}.")
    steps = testcase.get("steps") or []
    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, (list, tuple)) or len(step) != 2:
            raise ValueError(f"Testcase {title!r} step {idx} must be a (step, expected) pair.")
        expected = str(step[1]).strip()
        if "sample output:" not in expected.casefold():
            raise ValueError(
                f"Testcase {title!r} step {idx} expected result must include "
                f"'Sample output:' (use expected_sample_output())."
            )


def build_testcase_metadata(
    *,
    posneg: str,
    importance: str,
    base: Mapping[str, Any] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build Polarion REST ``attributes`` for testcase classification.

    UI labels (Level, Component, Importance, Pos/Neg, Automation) require ``case*``
    attribute ids with lowercase enum values — see ``CNF_METALLB_TESTCASE_METADATA_DEFAULTS``
    and SKILL ``metallb-polarion-test-publish``.

    Epic modules pass human-readable ``posneg`` (Positive/Negative) and ``importance``
    (Critical/High/Medium/Low); this function maps them to ``caseposneg``,
    ``caseimportance``, and ``priority``.
    """
    if posneg not in _VALID_POSNEG:
        raise ValueError(f"posneg must be one of {sorted(_VALID_POSNEG)}, got {posneg!r}")
    if importance not in _VALID_IMPORTANCE:
        raise ValueError(
            f"importance must be one of {sorted(_VALID_IMPORTANCE)}, got {importance!r}"
        )

    meta = dict(base or CNF_METALLB_TESTCASE_METADATA_DEFAULTS)
    if overrides:
        meta.update(overrides)
    meta["caseposneg"] = _POSNEG_TO_CASE[posneg]
    meta["caseimportance"] = _IMPORTANCE_TO_CASE[importance]
    meta["priority"] = IMPORTANCE_TO_PRIORITY[importance]
    return meta


def resolve_testcase_metadata(
    testcase: Mapping[str, Any],
    *,
    epic_defaults: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build REST metadata for one testcase dict from epic ``DEFAULT_TESTCASE_METADATA`` and
    required per-test ``posneg`` / ``importance`` (optional ``metadata`` overrides).

    Returned dict is ready for ``PolarionAdapter.create_testcase(..., metadata=...)``.
    """
    posneg = str(testcase.get("posneg", "")).strip()
    importance = str(testcase.get("importance", "")).strip()
    if not posneg or not importance:
        title = testcase.get("title", "<untitled>")
        raise ValueError(
            f"Testcase {title!r} must define posneg and importance "
            "(Positive/Negative and Critical/High/Medium/Low)."
        )
    per_test = testcase.get("metadata")
    overrides = dict(per_test) if isinstance(per_test, Mapping) else None
    return build_testcase_metadata(
        posneg=posneg,
        importance=importance,
        base=epic_defaults,
        overrides=overrides,
    )


def discover_work_item_ids_by_title_marker(
    adapter: PolarionAdapter,
    project_id: str,
    *,
    lucene_query: str,
    title_substring: str,
    max_pages: int = 50,
) -> list[str]:
    """
    List work item short ids where Polarion search returns items matching ``lucene_query``
    and title contains ``title_substring``.
    """
    from polarion_rest_client.workitem import WorkItem

    wi = WorkItem(adapter.client)
    found: list[str] = []
    for page in range(1, max_pages + 1):
        items = wi.list(
            project_id,
            page_size=100,
            page_number=page,
            query=lucene_query,
            fields=["id", "title"],
        )
        if not items:
            break
        for it in items:
            title = (it.get("attributes") or {}).get("title") or ""
            if title_substring not in title:
                continue
            full_id = it.get("id") or ""
            short = full_id.split("/")[-1] if "/" in full_id else full_id
            if short:
                found.append(short)
        if len(items) < 100:
            break
    return sorted(set(found))
